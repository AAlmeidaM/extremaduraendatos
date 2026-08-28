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

# Traduce la "clave de territorio" que detecta parse.py (subcadena en minúsculas
# sin acentos) al nombre exacto guardado en la tabla `territorio` (sembrada por
# sql/001_schema.sql).
TERRITORIO_CLAVE_A_NOMBRE = {
    "badajoz": "Badajoz",
    "caceres": "Cáceres",
    "extremadura": "Extremadura",
}


def connect(database_url: str):
    return psycopg2.connect(database_url)


def ensure_schema(conn) -> None:
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    logger.info("Esquema verificado/aplicado (%s).", SCHEMA_FILE.name)


def get_territorio_id(conn, clave: str) -> int:
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
                 nivel_territorial, periodicidad)
            SELECT id, %(tabla_id_externo)s, %(codigo)s, %(nombre)s, %(categoria)s,
                   %(nivel_territorial)s, %(periodicidad)s
            FROM fuente WHERE codigo = 'ine'
            ON CONFLICT (codigo) DO UPDATE SET
                nombre = EXCLUDED.nombre,
                categoria = EXCLUDED.categoria,
                nivel_territorial = EXCLUDED.nivel_territorial,
                periodicidad = EXCLUDED.periodicidad
            RETURNING id
            """,
            {
                "tabla_id_externo": indicador.tabla_id_externo,
                "codigo": indicador.codigo,
                "nombre": indicador.nombre,
                "categoria": indicador.categoria,
                "nivel_territorial": indicador.nivel_territorial,
                "periodicidad": indicador.periodicidad,
            },
        )
        row = cur.fetchone()
    conn.commit()
    return row[0]


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
            cache_territorio[f.territorio_clave] = get_territorio_id(conn, f.territorio_clave)
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
