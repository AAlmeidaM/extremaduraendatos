"""Interpreta el JSON crudo de DATOS_TABLA del INE y lo normaliza a filas listas
para cargar en la base de datos (una fila por serie + periodo).

Campos y estructura confirmados contra respuestas REALES del INE (no contra
documentación): tablas 50913 (IPC, CCAA) y 3996 (EPA paro por provincia),
verificadas en el navegador el 2026-08-28 — ver docs/fuentes-ine.md. Cada
elemento de la lista que devuelve DATOS_TABLA es una serie con esta forma:

    {
        "COD": "IPC256217",
        "Nombre": "Extremadura. Índice general. Índice. ",
        "T3_Unidad": "Índice",
        "T3_Escala": " ",
        "MetaData": [
            {"Id": 1, "T3_Variable": "Tipo de dato", "Nombre": "Índice", "Codigo": "..."},
            {"Id": 9007, "T3_Variable": "Comunidades y Ciudades Autónomas",
             "Nombre": "Extremadura", "Codigo": "11"},
            ...
        ],
        "Data": [
            {"Fecha": "2025-12-01T00:00:00.000+01:00", "T3_TipoDato": "Definitivo",
             "T3_Periodo": "M12", "Anyo": 2025, "Valor": 120.159, "Secreto": false},
            ...
        ],
    }

Puntos importantes que NO coincidían con lo que se había asumido antes de
verificarlo (ver CHANGELOG 2026-08-28):

- `Fecha` es un string ISO 8601 con offset de zona (no epoch en milisegundos).
- La unidad/escala/tipo de dato van en `T3_Unidad`, `T3_Escala`, `T3_TipoDato`
  (strings simples, no `{"Nombre": ...}`).
- `MetaData` trae, para cada dimensión de la serie (territorio, tipo de dato,
  sexo, rubro...), su `T3_Variable` (la etiqueta de la dimensión) y su
  `Nombre`/`Codigo` concretos. Es mucho más fiable que buscar el territorio
  como subcadena de `Nombre` (que sigue existiendo, y se usa como respaldo si
  una tabla no trae MetaData reconocible).
- `nombre_origen` NO es una clave fiable por sí sola (ver sql/001_schema.sql):
  el INE puede repetir el mismo `Nombre` y el mismo `MetaData` para dos
  series con `COD` y valores distintos (encontrado en la tabla 2941). La
  clave real es `COD` cuando existe.

⚠️ Existe una SEGUNDA variante de formato, encontrada el 2026-08-28 en las
tablas de Contabilidad Regional de España (77196, y probablemente 72946/su
sustituta — ver docs/fuentes-ine.md): sin `COD`, sin `T3_Unidad`/`T3_Escala`/
`T3_TipoDato`, y cada punto de `Data` trae `NombrePeriodo` (p.ej. `"2024(A)"`)
en vez de `Fecha`/`Anyo`/`T3_Periodo`:

    {
        "Nombre": "Extremadura, A. Agricultura, ganadería, silvicultura y pesca, Valor",
        "MetaData": [
            {"T3_Variable": "Comunidades y Ciudades Autónomas", "Nombre": "Extremadura", "Codigo": "11"},
            {"T3_Variable": "ramas de actividad", "Nombre": "A. Agricultura...", "Codigo": "..."},
            {"T3_Variable": "magnitud", "Nombre": "Valor", "Codigo": "valor"},
        ],
        "Data": [{"NombrePeriodo": "2024(A)", "Valor": 2175719.0}],
    }

`parsear_tabla()` reconoce ambos formatos por punto de `Data` (usa `Fecha` si
está, si no intenta `NombrePeriodo` — ver `_fecha_desde_nombre_periodo`).
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Patrones de NombrePeriodo vistos hasta ahora en tablas anuales tipo CRE:
# "2024(A)" (tabla 77196, CCAA) y "2023(P)" (tabla 76926, provincia) — la
# letra entre paréntesis parece indicar el estado del dato (avance/
# provisional/...), no la periodicidad, y varía de una tabla a otra; se
# guarda tal cual en `tipo_dato` sin intentar traducir su significado exacto.
# Trimestral/mensual son una extrapolación razonable del mismo formato
# Tempus3 legacy, pero NO se han visto todavía en datos reales — si aparecen
# y no encajan, este es el único sitio que hay que ajustar.
_RE_PERIODO_ANUAL = re.compile(r"^(\d{4})\(([A-Za-z]+)\)$")
_RE_PERIODO_TRIMESTRAL = re.compile(r"^(\d{4})T(\d)$")
_RE_PERIODO_MENSUAL = re.compile(r"^(\d{4})M(\d{1,2})$")


def _fecha_desde_nombre_periodo(nombre_periodo: str) -> tuple[date, int, str, str | None] | None:
    """Respaldo para el formato legacy sin `Fecha` (ver aviso arriba).
    Devuelve (fecha, anyo, periodo_codigo, tipo_dato) o None si no se
    reconoce el patrón.
    """
    m = _RE_PERIODO_ANUAL.match(nombre_periodo)
    if m:
        anyo = int(m.group(1))
        return date(anyo, 1, 1), anyo, "A", m.group(2)
    m = _RE_PERIODO_TRIMESTRAL.match(nombre_periodo)
    if m:
        anyo, trimestre = int(m.group(1)), int(m.group(2))
        return date(anyo, (trimestre - 1) * 3 + 1, 1), anyo, f"T{trimestre}", None
    m = _RE_PERIODO_MENSUAL.match(nombre_periodo)
    if m:
        anyo, mes = int(m.group(1)), int(m.group(2))
        return date(anyo, mes, 1), anyo, f"M{mes:02d}", None
    return None

# T3_Variable (normalizados) que identifican una dimensión territorial dentro
# de MetaData. Confirmado contra datos reales: las tablas de ámbito CCAA usan
# "Comunidades y Ciudades Autónomas", las de ámbito provincia usan
# "Provincias". Si aparece una tabla con otra etiqueta territorial, añadirla
# aquí (único sitio que hace falta tocar).
VARIABLES_TERRITORIALES = {
    "comunidades y ciudades autonomas",
    "provincias",
}


def _normaliza(texto: str) -> str:
    """minúsculas y sin acentos, para comparar 'Cáceres' con 'caceres'."""
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sin_acentos.lower().strip()


def _texto_o_none(valor: Any) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


@dataclass
class ObservacionParseada:
    territorio_clave: str  # p.ej. "badajoz" — el elemento de filtro que hizo match
    periodo_fecha: date
    anyo: int
    periodo_codigo: str
    valor: float | None
    unidad: str | None
    escala: str | None
    tipo_dato: str | None
    secreto: bool
    serie_nombre_origen: str
    serie_codigo_origen: str | None = None
    # Resto de dimensiones de la serie (todo lo que MetaData trae aparte del
    # territorio), tal cual: {T3_Variable: {"nombre": ..., "codigo": ...}}.
    # Se guarda en serie.atributos (JSONB) — ver sql/001_schema.sql.
    serie_atributos: dict[str, Any] = field(default_factory=dict)


def _periodo_codigo(periodicidad: str, fecha: date, periodo_ine: str | None) -> str:
    """Prefiere el código de periodo que da el propio INE (`T3_Periodo`, p.ej.
    "M12", "T4") y solo lo deriva de la fecha si no viene."""
    if periodo_ine:
        return str(periodo_ine)
    if periodicidad == "anual":
        return "A"
    if periodicidad == "trimestral":
        return f"T{(fecha.month - 1) // 3 + 1}"
    if periodicidad == "mensual":
        return f"M{fecha.month:02d}"
    return fecha.isoformat()


def _extrae_territorio_y_atributos(
    serie: dict[str, Any], filtro_territorio: tuple[str, ...], nombre_serie: str
) -> tuple[str | None, dict[str, Any]]:
    """Decide a qué territorio pertenece esta serie y recoge el resto de sus
    dimensiones (para guardarlas como atributos de la serie).

    Estrategia principal: recorrer `MetaData`. La dimensión cuyo `T3_Variable`
    es territorial (ver VARIABLES_TERRITORIALES) da el territorio, comparando
    su `Nombre` normalizado con `filtro_territorio`; el resto de dimensiones
    se guardan tal cual en un dict.

    Respaldo: si la tabla no trae MetaData (o no trae una dimensión
    territorial reconocible), se busca cada elemento de `filtro_territorio`
    como subcadena del nombre completo de la serie — el método usado antes de
    poder verificar MetaData contra datos reales.
    """
    metadata = serie.get("MetaData")
    territorio_clave: str | None = None
    atributos: dict[str, Any] = {}

    if isinstance(metadata, list):
        for dim in metadata:
            if not isinstance(dim, dict):
                continue
            variable = dim.get("T3_Variable")
            valor_nombre = dim.get("Nombre")
            valor_codigo = dim.get("Codigo")
            if not variable or valor_nombre is None:
                continue

            if _normaliza(str(variable)) in VARIABLES_TERRITORIALES:
                candidato = next(
                    (t for t in filtro_territorio if t == _normaliza(str(valor_nombre))),
                    None,
                )
                if candidato is not None:
                    territorio_clave = candidato
                continue  # el territorio no se repite como atributo aparte

            atributos[str(variable)] = {"nombre": valor_nombre, "codigo": valor_codigo}

    if territorio_clave is None:
        nombre_normalizado = _normaliza(nombre_serie)
        territorio_clave = next(
            (t for t in filtro_territorio if t in nombre_normalizado), None
        )

    return territorio_clave, atributos


def parsear_tabla(
    datos_crudos: list[dict[str, Any]],
    filtro_territorio: tuple[str, ...],
    periodicidad: str,
) -> list[ObservacionParseada]:
    """`datos_crudos` es la lista de series que devuelve IneClient.fetch_tabla.

    Nos quedamos solo con las series cuyo territorio (resuelto vía MetaData, o
    por subcadena en el nombre si no hay MetaData reconocible) está en
    `filtro_territorio`.
    """
    resultado: list[ObservacionParseada] = []

    if not isinstance(datos_crudos, list):
        logger.error(
            "Se esperaba una lista de series y se recibió %s — revisa el JSON "
            "crudo con inspect_table.py.",
            type(datos_crudos),
        )
        return resultado

    for serie in datos_crudos:
        if not isinstance(serie, dict):
            continue

        nombre_serie = serie.get("Nombre") or ""
        codigo_serie = serie.get("COD")
        codigo_serie = str(codigo_serie) if codigo_serie is not None else None
        unidad = _texto_o_none(serie.get("T3_Unidad"))
        escala = _texto_o_none(serie.get("T3_Escala"))

        territorio_clave, atributos = _extrae_territorio_y_atributos(
            serie, filtro_territorio, nombre_serie
        )
        if territorio_clave is None:
            continue  # no es de Extremadura/Badajoz/Cáceres: se descarta

        puntos = serie.get("Data")
        if not isinstance(puntos, list):
            logger.warning("Serie '%s' sin lista Data reconocible, se omite.", nombre_serie)
            continue

        for punto in puntos:
            if not isinstance(punto, dict):
                continue

            fecha_raw = punto.get("Fecha")
            periodo_codigo_ine: str | None = None
            tipo_dato_punto: str | None = None
            if fecha_raw is not None:
                try:
                    fecha = datetime.fromisoformat(str(fecha_raw)).date()
                except ValueError:
                    logger.warning("Fecha ilegible (%s) en serie '%s'.", fecha_raw, nombre_serie)
                    continue
                anyo_declarado = punto.get("Anyo")
                anyo = int(anyo_declarado) if anyo_declarado is not None else fecha.year
                if anyo_declarado is not None and int(anyo_declarado) != fecha.year:
                    logger.debug(
                        "Anyo declarado (%s) distinto del año de Fecha (%s) en '%s'; se usa el de Fecha.",
                        anyo_declarado, fecha.year, nombre_serie,
                    )
                periodo_codigo_ine = punto.get("T3_Periodo")
                tipo_dato_punto = _texto_o_none(punto.get("T3_TipoDato"))
            else:
                # Formato legacy sin Fecha (tablas tipo CRE) — ver aviso al
                # principio del módulo.
                nombre_periodo = punto.get("NombrePeriodo")
                if nombre_periodo is None:
                    logger.warning(
                        "Punto sin Fecha ni NombrePeriodo en serie '%s': %s", nombre_serie, punto
                    )
                    continue
                resuelto = _fecha_desde_nombre_periodo(str(nombre_periodo))
                if resuelto is None:
                    logger.warning(
                        "NombrePeriodo '%s' no reconocido en serie '%s' — revisar "
                        "_fecha_desde_nombre_periodo().", nombre_periodo, nombre_serie,
                    )
                    continue
                fecha, anyo, periodo_codigo_ine, tipo_dato_punto = resuelto

            valor_bruto = punto.get("Valor")
            valor = None if valor_bruto is None else float(valor_bruto)
            secreto = bool(punto.get("Secreto") or False)

            resultado.append(
                ObservacionParseada(
                    territorio_clave=territorio_clave,
                    periodo_fecha=fecha,
                    anyo=anyo,
                    periodo_codigo=_periodo_codigo(periodicidad, fecha, periodo_codigo_ine),
                    valor=valor,
                    unidad=unidad,
                    escala=escala,
                    tipo_dato=tipo_dato_punto,
                    secreto=secreto,
                    serie_nombre_origen=nombre_serie,
                    serie_codigo_origen=codigo_serie,
                    serie_atributos=atributos,
                )
            )

    return resultado
