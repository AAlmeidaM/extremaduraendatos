"""Acceso a PostgreSQL: aplicar el esquema y volcar observaciones (upsert)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import psycopg2
import psycopg2.extras

from .config import PROJECT_ROOT
from .indicadores import Indicador
from .parse import ObservacionParseada

logger = logging.getLogger(__name__)

SCHEMA_FILE = PROJECT_ROOT / "sql" / "001_schema.sql"

# Traduce la "clave de territorio" que detecta parse.py (nombre normalizado:
# minúsculas, sin acentos) al nombre exacto guardado en la tabla `territorio`
# (sembrada por sql/001_schema.sql). Ampliado el 2026-08-28 con el resto de
# CCAA + las dos filas nacionales ("Nacional" / "Total Nacional", que usa el
# INE indistintamente según la tabla) para poder comparar Extremadura con el
# resto de España — ver indicadores.py (_TODAS_CCAA) y parse.py
# (VARIABLES_TERRITORIALES, que ahora también reconoce las etiquetas
# "Totales Territoriales"/"Total Nacional" como dimensión territorial).
TERRITORIO_CLAVE_A_NOMBRE = {
    "badajoz": "Badajoz",
    "caceres": "Cáceres",
    "extremadura": "Extremadura",
    "andalucia": "Andalucía",
    "aragon": "Aragón",
    "asturias, principado de": "Asturias, Principado de",
    "balears, illes": "Balears, Illes",
    "canarias": "Canarias",
    "cantabria": "Cantabria",
    "castilla - la mancha": "Castilla - La Mancha",
    "castilla y leon": "Castilla y León",
    "cataluna": "Cataluña",
    "ceuta": "Ceuta",
    "comunitat valenciana": "Comunitat Valenciana",
    "galicia": "Galicia",
    "madrid, comunidad de": "Madrid, Comunidad de",
    "melilla": "Melilla",
    "murcia, region de": "Murcia, Región de",
    "navarra, comunidad foral de": "Navarra, Comunidad Foral de",
    "pais vasco": "País Vasco",
    "rioja, la": "Rioja, La",
    "nacional": "España",
    "total nacional": "España",
}


def connect(database_url: str):
    return psycopg2.connect(database_url)


def ensure_schema(conn) -> None:
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    logger.info("Esquema verificado/aplicado (%s).", SCHEMA_FILE.name)


# Nombres en castellano de los 27 Estados miembros (código Eurostat → nombre),
# para dar de alta los países la primera vez que llegan datos de Eurostat
# (2026-09-15). España ya existe como territorio y se enlaza por codigo_nuts.
NOMBRES_PAISES_UE27 = {
    "AT": "Austria", "BE": "Bélgica", "BG": "Bulgaria", "CY": "Chipre",
    "CZ": "Chequia", "DE": "Alemania", "DK": "Dinamarca", "EE": "Estonia",
    "EL": "Grecia", "ES": "España", "FI": "Finlandia", "FR": "Francia",
    "HR": "Croacia", "HU": "Hungría", "IE": "Irlanda", "IT": "Italia",
    "LT": "Lituania", "LU": "Luxemburgo", "LV": "Letonia", "MT": "Malta",
    "NL": "Países Bajos", "PL": "Polonia", "PT": "Portugal", "RO": "Rumanía",
    "SE": "Suecia", "SI": "Eslovenia", "SK": "Eslovaquia",
}


def get_or_create_territorio_nuts(conn, codigo_nuts: str, etiqueta_origen: str | None) -> int:
    """Resuelve (o da de alta) un territorio por su código NUTS/Eurostat.

    - Si ya existe una fila con ese `codigo_nuts` (España, las 19 CCAA,
      Badajoz, Cáceres y la UE-27 vienen sembradas en sql/001_schema.sql), se
      devuelve esa: así los datos de Eurostat y del INE comparten territorio.
    - Si no, se crea: países UE-27 con nivel 'pais' (padre = UE-27) y
      regiones NUTS2 con nivel 'nuts2' (padre = su país, que se crea antes
      si hace falta). El nombre es la etiqueta de Eurostat; como `territorio`
      exige nombre único por nivel, si otra región ya tiene ese nombre se
      añade el código entre paréntesis.
    """
    from .eurostat_parse import clasificar_geo  # import local: evita ciclo

    with conn.cursor() as cur:
        cur.execute("SELECT id FROM territorio WHERE codigo_nuts = %s", (codigo_nuts,))
        row = cur.fetchone()
        if row is not None:
            return row[0]

    nivel = clasificar_geo(codigo_nuts)
    if nivel == "pais":
        padre_id = _territorio_id_por_nuts(conn, "EU27_2020")
        nombre = NOMBRES_PAISES_UE27.get(codigo_nuts, etiqueta_origen or codigo_nuts)
    elif nivel == "nuts2":
        pais = codigo_nuts[:2]
        padre_id = get_or_create_territorio_nuts(conn, pais, NOMBRES_PAISES_UE27.get(pais))
        nombre = etiqueta_origen or codigo_nuts
    else:
        raise ValueError(
            f"Código NUTS {codigo_nuts!r} (nivel {nivel!r}) no se da de alta automáticamente: "
            f"debería venir sembrado en sql/001_schema.sql."
        )

    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM territorio WHERE nivel = %s AND nombre = %s", (nivel, nombre)
        )
        if cur.fetchone() is not None:
            nombre = f"{nombre} ({codigo_nuts})"
        cur.execute(
            """
            INSERT INTO territorio (nivel, codigo_nuts, nombre, padre_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (nivel, codigo_nuts, nombre, padre_id),
        )
        nuevo_id = cur.fetchone()[0]
    return nuevo_id


def _territorio_id_por_nuts(conn, codigo_nuts: str) -> int | None:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM territorio WHERE codigo_nuts = %s", (codigo_nuts,))
        row = cur.fetchone()
    return row[0] if row else None


def get_territorio_id(conn, clave: str, etiqueta_origen: str | None = None) -> int:
    from .eurostat_parse import PREFIJO_CLAVE_NUTS  # import local: evita ciclo

    if clave.startswith(PREFIJO_CLAVE_NUTS):
        return get_or_create_territorio_nuts(conn, clave[len(PREFIJO_CLAVE_NUTS):], etiqueta_origen)
    nombre = TERRITORIO_CLAVE_A_NOMBRE.get(clave)
    if nombre is None:
        raise ValueError(f"Clave de territorio desconocida: {clave!r}")
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM territorio WHERE nombre = %s", (nombre,))
        row = cur.fetchone()
        if row is None:
            raise RuntimeError(
                f"Territorio '{nombre}' no está en la base de datos. "
                f"¿Se aplicó sql/001_schema.sql?"
            )
        return row[0]


def get_or_create_serie(
    conn,
    indicador_id: int,
    territorio_id: int,
    nombre_origen: str,
    codigo_origen: str | None,
    atributos: dict | None = None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO serie (indicador_id, territorio_id, nombre_origen, codigo_origen, atributos)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicador_id, clave_natural) DO UPDATE SET
                nombre_origen = EXCLUDED.nombre_origen,
                codigo_origen = COALESCE(EXCLUDED.codigo_origen, serie.codigo_origen),
                atributos = EXCLUDED.atributos
            RETURNING id
            """,
            (
                indicador_id,
                territorio_id,
                nombre_origen,
                codigo_origen,
                psycopg2.extras.Json(atributos or {}),
            ),
        )
        row = cur.fetchone()
    return row[0]


def get_or_create_indicador(conn, indicador: Indicador) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO indicador
                (fuente_id, tabla_id_externo, codigo, nombre, categoria,
                 nivel_territorial, periodicidad, ine_operacion_id, ine_publicacion_id,
                 naturaleza_dato)
            SELECT id, %(tabla_id_externo)s, %(codigo)s, %(nombre)s, %(categoria)s,
                   %(nivel_territorial)s, %(periodicidad)s, %(ine_operacion_id)s,
                   %(ine_publicacion_id)s, %(naturaleza_dato)s
            FROM fuente WHERE codigo = %(fuente)s
            ON CONFLICT (codigo) DO UPDATE SET
                nombre = EXCLUDED.nombre,
                categoria = EXCLUDED.categoria,
                nivel_territorial = EXCLUDED.nivel_territorial,
                periodicidad = EXCLUDED.periodicidad,
                naturaleza_dato = EXCLUDED.naturaleza_dato,
                -- COALESCE(catálogo, lo que ya hubiera en la BD): así una
                -- corrección en indicadores.py siempre gana, pero un
                -- ine_publicacion_id autodescubierto en tiempo de ejecución
                -- (ver calendario.py, caso CRE) no se pisa a NULL cada día
                -- solo porque el catálogo estático no lo trae.
                ine_operacion_id = COALESCE(EXCLUDED.ine_operacion_id, indicador.ine_operacion_id),
                ine_publicacion_id = COALESCE(EXCLUDED.ine_publicacion_id, indicador.ine_publicacion_id)
            RETURNING id
            """,
            {
                "tabla_id_externo": indicador.tabla_id_externo,
                "codigo": indicador.codigo,
                "nombre": indicador.nombre,
                "categoria": indicador.categoria,
                "nivel_territorial": indicador.nivel_territorial,
                "periodicidad": indicador.periodicidad,
                "ine_operacion_id": indicador.ine_operacion_id,
                "ine_publicacion_id": indicador.ine_publicacion_id,
                "naturaleza_dato": indicador.naturaleza_dato,
                "fuente": indicador.fuente,
            },
        )
        row = cur.fetchone()
    conn.commit()
    if row is None:
        raise RuntimeError(
            f"La fuente {indicador.fuente!r} no existe en la tabla `fuente` "
            f"(¿se aplicó sql/001_schema.sql?)."
        )
    return row[0]


# --- Fecha de actualización en origen (Eurostat, 2026-09-15) ----------------

def origen_actualizado(conn, indicador_id: int) -> str | None:
    """Último valor de `updated` de Eurostat ya ingerido con éxito para este
    indicador (texto tal cual lo da la API), o None si nunca se ha cargado."""
    with conn.cursor() as cur:
        cur.execute("SELECT origen_actualizado FROM indicador WHERE id = %s", (indicador_id,))
        row = cur.fetchone()
    return row[0] if row else None


def guardar_origen_actualizado(conn, indicador_id: int, valor: str | None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE indicador SET origen_actualizado = %s WHERE id = %s", (valor, indicador_id)
        )
    conn.commit()


# --- Calendario oficial de publicaciones del INE (ver calendario.py) --------

def calendario_reciente(conn, indicador_id: int, dias: int) -> bool:
    """True si ya se consultó el calendario del INE para este indicador en
    los últimos `dias` días (evita golpear la API en cada ejecución diaria
    cuando el calendario de una operación apenas cambia)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM indicador
            WHERE id = %s
              AND calendario_actualizado_en IS NOT NULL
              AND calendario_actualizado_en > now() - (%s || ' days')::interval
            """,
            (indicador_id, dias),
        )
        return cur.fetchone() is not None


def marcar_calendario_actualizado(conn, indicador_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE indicador SET calendario_actualizado_en = now() WHERE id = %s",
            (indicador_id,),
        )
    conn.commit()


def guardar_ine_publicacion_id(conn, indicador_id: int, publicacion_id: int) -> None:
    """Persiste el ine_publicacion_id autodescubierto (caso CRE, ver
    indicadores.py) para no tener que volver a resolverlo cada vez."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE indicador SET ine_publicacion_id = %s WHERE id = %s",
            (publicacion_id, indicador_id),
        )
    conn.commit()


def upsert_fechas_calendario(conn, indicador_id: int, fechas: list[tuple]) -> None:
    """`fechas`: lista de (fecha: date, periodo_referencia: str | None)."""
    if not fechas:
        return
    # Una misma fecha puede venir repetida en la respuesta del INE (varias
    # referencias publicadas el mismo día — visto el 2026-09-16 en turismo,
    # vivienda, EPA...). Repetida dentro del mismo INSERT ... ON CONFLICT DO
    # UPDATE, Postgres aborta con CardinalityViolation: se deja una fila por
    # fecha (la última referencia vista).
    por_fecha = {fecha: periodo for fecha, periodo in fechas}
    registros = [(indicador_id, fecha, periodo) for fecha, periodo in por_fecha.items()]
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO calendario_publicacion (indicador_id, fecha_publicacion, periodo_referencia)
            VALUES %s
            ON CONFLICT (indicador_id, fecha_publicacion) DO UPDATE SET
                periodo_referencia = EXCLUDED.periodo_referencia
            """,
            registros,
        )
    conn.commit()


def hay_fechas_calendario(conn, indicador_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM calendario_publicacion WHERE indicador_id = %s LIMIT 1",
            (indicador_id,),
        )
        return cur.fetchone() is not None


def hay_publicacion_pendiente(conn, indicador_id: int) -> bool:
    """True si hay al menos una fecha de publicación ya vencida (<= hoy) que
    todavía no se ha marcado como procesada."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM calendario_publicacion
            WHERE indicador_id = %s AND NOT procesada AND fecha_publicacion <= CURRENT_DATE
            LIMIT 1
            """,
            (indicador_id,),
        )
        return cur.fetchone() is not None


def marcar_publicaciones_procesadas(conn, indicador_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE calendario_publicacion SET procesada = TRUE
            WHERE indicador_id = %s AND NOT procesada AND fecha_publicacion <= CURRENT_DATE
            """,
            (indicador_id,),
        )
    conn.commit()


def upsert_observaciones(
    conn, indicador_id: int, filas: Iterable[ObservacionParseada]
) -> tuple[int, int]:
    """Crea/reutiliza las series que hagan falta y hace upsert de sus observaciones.

    Devuelve (insertadas_o_actualizadas, total).
    """
    filas = list(filas)
    if not filas:
        return (0, 0)

    # Cache local: evita volver a resolver territorio_id/serie_id para cada
    # punto de la misma serie (una serie trae varios periodos en Data).
    cache_territorio: dict[str, int] = {}
    cache_serie: dict[tuple[str, str], int] = {}

    registros = []
    for f in filas:
        if f.territorio_clave not in cache_territorio:
            cache_territorio[f.territorio_clave] = get_territorio_id(
                conn, f.territorio_clave, f.territorio_nombre_origen
            )
        territorio_id = cache_territorio[f.territorio_clave]

        # Misma logica que la columna generada clave_natural en la BD (COD si
        # lo hay, si no el nombre) -- ver sql/001_schema.sql. Si se usara solo
        # el nombre aqui, dos series con Nombre identico pero COD distinto
        # (encontrado de verdad en la tabla 2941, ver esa nota en el esquema)
        # se fusionarian ya en esta cache antes de llegar a la BD.
        clave_serie = (f.territorio_clave, f.serie_codigo_origen or f.serie_nombre_origen)
        if clave_serie not in cache_serie:
            cache_serie[clave_serie] = get_or_create_serie(
                conn,
                indicador_id,
                territorio_id,
                f.serie_nombre_origen,
                f.serie_codigo_origen,
                f.serie_atributos,
            )
        serie_id = cache_serie[clave_serie]

        registros.append(
            (
                serie_id,
                f.periodo_fecha,
                f.anyo,
                f.periodo_codigo,
                f.valor,
                f.unidad,
                f.escala,
                f.tipo_dato,
                f.secreto,
            )
        )

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO observacion
                (serie_id, periodo_fecha, anyo, periodo_codigo,
                 valor, unidad, escala, tipo_dato, secreto)
            VALUES %s
            ON CONFLICT (serie_id, periodo_fecha) DO UPDATE SET
                valor = EXCLUDED.valor,
                unidad = EXCLUDED.unidad,
                escala = EXCLUDED.escala,
                tipo_dato = EXCLUDED.tipo_dato,
                secreto = EXCLUDED.secreto,
                actualizado_en = now()
            """,
            registros,
        )
    conn.commit()
    return (len(registros), len(registros))


def registrar_carga(
    conn,
    indicador_id: int | None,
    estado: str,
    mensaje: str,
    filas_leidas: int = 0,
    filas_insertadas: int = 0,
    filas_actualizadas: int = 0,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO carga_log
                (indicador_id, finalizado_en, filas_leidas, filas_insertadas,
                 filas_actualizadas, estado, mensaje)
            VALUES (%s, now(), %s, %s, %s, %s, %s)
            """,
            (indicador_id, filas_leidas, filas_insertadas, filas_actualizadas, estado, mensaje[:2000]),
        )
    conn.commit()
