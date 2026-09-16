"""Interpreta la respuesta JSON-stat 2.0 de la API de Eurostat y la normaliza a
las mismas filas (`ObservacionParseada`) que usa la ingesta del INE, para
reutilizar `db.upsert_observaciones` sin cambios de modelo.

Estructura verificada contra respuestas REALES de Eurostat el 2026-09-15
(desde el navegador del PC de producción, ver docs/fuentes-europa-agro.md §1):

    {
        "label": "Gross domestic product (GDP) at current market prices by NUTS 2 region",
        "updated": "2026-02-10T11:00:00+0100",
        "id":   ["freq", "unit", "geo", "time"],
        "size": [1, 2, 9, 3],
        "dimension": {
            "unit": {"label": "Unit of measure",
                     "category": {"index": {"MIO_EUR": 0, "PPS_EU27_2020_HAB": 1},
                                  "label": {"MIO_EUR": "Million euro", ...}}},
            "geo":  {... "index": {"EU27_2020": 0, "EL30": 1, "ES": 2, "ES4": 3, "ES43": 4, ...}},
            "time": {... "index": {"2022": 0, "2023": 1, "2024": 2}},
        },
        "value":  {"0": 16169785.3, "14": 26583.5, ...},   # DISPERSO: índice lineal -> valor
        "status": {"4": "p", "159": "|C", ...},            # flags por índice lineal
        "extension": {"status": {"label": {"p": "provisional", "|C": "|confidential"}}},
    }

Puntos importantes:

- `value` y `status` son diccionarios **dispersos** indexados por la posición
  lineal (orden fila de `id`/`size`, la última dimensión varía más rápido).
  Las posiciones sin dato simplemente no aparecen.
- Dato confidencial: aparece en `status` con una `C` (visto como `"|C"`) y
  **sin** entrada en `value` → se guarda como `secreto=True`, `valor=None`
  (mismo tratamiento que el secreto estadístico del INE; `v_analisis` lo
  excluye por defecto).
- `geo` mezcla agregados (`EU27_2020`, `EU`, `EA20`), países (`ES`), NUTS1
  (`ES4`), NUTS2 (`ES43`), a veces NUTS3 (`ES431`), "Extra-Regio" (`ESZZ`) y
  regiones de países no UE (`NO08`, `TR10`...). `clasificar_geo()` decide qué
  se guarda (ver su docstring).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from .parse import ObservacionParseada

logger = logging.getLogger(__name__)

# Estados miembros de la UE-27 tal y como los codifica Eurostat (Grecia = EL).
PAISES_UE27 = frozenset(
    "AT BE BG CY CZ DE DK EE EL ES FI FR HR HU IE IT LT LU LV MT NL PL PT RO SE SI SK".split()
)

AGREGADO_UE27 = "EU27_2020"

# NUTS3 que sí se guardan: solo las dos provincias extremeñas, que ya existen
# como territorio (el resto de NUTS3 europeos quedan fuera de esta fase).
NUTS3_GUARDADOS = frozenset({"ES431", "ES432"})

# Prefijo de la clave de territorio que entiende db.get_territorio_id para
# resolver por código NUTS (en vez de por nombre, como con el INE).
PREFIJO_CLAVE_NUTS = "nuts:"

_DIMENSIONES_NO_SERIE = {"geo", "time"}


def clasificar_geo(codigo: str) -> str | None:
    """Devuelve el nivel territorial con el que se guarda un código `geo`, o
    None si se descarta.

    - `EU27_2020` → 'agregado' (media/total de la UE-27, referencia de comparación).
    - País UE-27 (2 letras) → 'pais'.
    - NUTS2 de un país UE-27 (4 caracteres) → 'nuts2' (las de España ya
      existen como 'ccaa' y se resuelven por su código NUTS).
    - Badajoz/Cáceres (`ES431`/`ES432`) → 'provincia'.
    - Todo lo demás (NUTS1, resto de NUTS3, Extra-Regio `xxZZ`, otros
      agregados, países/regiones fuera de la UE-27) → None.
    """
    if codigo == AGREGADO_UE27:
        return "agregado"
    if codigo in NUTS3_GUARDADOS:
        return "provincia"
    pais = codigo[:2]
    if pais not in PAISES_UE27:
        return None
    if len(codigo) == 2:
        return "pais"
    if len(codigo) == 4 and not codigo.endswith("Z"):
        return "nuts2"
    return None


_RE_ANUAL = re.compile(r"^(\d{4})$")
_RE_TRIMESTRE = re.compile(r"^(\d{4})-?Q([1-4])$")
_RE_MES = re.compile(r"^(\d{4})-?M?(\d{2})$")
_RE_SEMESTRE = re.compile(r"^(\d{4})-?S([12])$")


def periodo_desde_time(codigo_time: str) -> tuple[date, int, str] | None:
    """`"2024"` → (2024-01-01, 2024, "A"); `"2024-Q3"`/`"2024Q3"` → T3;
    `"2024-05"`/`"2024M05"` → M05; `"2024-S2"` → S2. None si no se reconoce."""
    texto = codigo_time.strip()
    if m := _RE_ANUAL.match(texto):
        anyo = int(m.group(1))
        return date(anyo, 1, 1), anyo, "A"
    if m := _RE_TRIMESTRE.match(texto):
        anyo, trimestre = int(m.group(1)), int(m.group(2))
        return date(anyo, 3 * (trimestre - 1) + 1, 1), anyo, f"T{trimestre}"
    if m := _RE_SEMESTRE.match(texto):
        anyo, semestre = int(m.group(1)), int(m.group(2))
        return date(anyo, 1 if semestre == 1 else 7, 1), anyo, f"S{semestre}"
    if m := _RE_MES.match(texto):
        anyo, mes = int(m.group(1)), int(m.group(2))
        if 1 <= mes <= 12:
            return date(anyo, mes, 1), anyo, f"M{mes:02d}"
    return None


@dataclass(frozen=True)
class _Dimension:
    id: str
    codigos: list[str]  # ordenados por su posición en el índice
    etiquetas: dict[str, str]


def _dimensiones(datos: dict[str, Any]) -> list[_Dimension]:
    dims = []
    for dim_id in datos["id"]:
        categoria = datos["dimension"][dim_id]["category"]
        indice: dict[str, int] = categoria["index"]
        codigos = [c for c, _ in sorted(indice.items(), key=lambda kv: kv[1])]
        dims.append(_Dimension(dim_id, codigos, categoria.get("label", {})))
    return dims


def _coordenadas(posicion: int, tamanos: list[int]) -> list[int]:
    """Posición lineal → índice en cada dimensión (última dimensión = la que
    varía más rápido, como define JSON-stat)."""
    coords = [0] * len(tamanos)
    for i in range(len(tamanos) - 1, -1, -1):
        posicion, coords[i] = divmod(posicion, tamanos[i])
    return coords


def parsear_dataset(datos: dict[str, Any], dataset: str) -> list[ObservacionParseada]:
    """Convierte una respuesta JSON-stat de Eurostat en filas listas para
    `db.upsert_observaciones`. Solo se quedan los territorios que acepta
    `clasificar_geo()`.

    Cada combinación de dimensiones distintas de `geo`/`time` (unidad, rama,
    sexo, edad...) + territorio es una `serie`; su `codigo_origen` es estable
    (`dataset|dim=COD.dim=COD|GEO`) y sus dimensiones van a `serie.atributos`.
    """
    if not isinstance(datos, dict) or "id" not in datos or "dimension" not in datos:
        logger.error("Respuesta de Eurostat sin estructura JSON-stat reconocible (%s).", dataset)
        return []

    dims = _dimensiones(datos)
    tamanos = [int(t) for t in datos["size"]]
    ids = [d.id for d in dims]
    if "geo" not in ids or "time" not in ids:
        logger.error("El dataset %s no tiene dimensiones geo/time.", dataset)
        return []
    i_geo, i_time = ids.index("geo"), ids.index("time")
    i_unit = ids.index("unit") if "unit" in ids else None

    valores: dict[str, Any] = datos.get("value") or {}
    estados: dict[str, str] = datos.get("status") or {}
    etiquetas_estado: dict[str, str] = (
        (datos.get("extension") or {}).get("status", {}).get("label", {})
    )

    # Posiciones a recorrer: todas las que tienen valor, más las marcadas como
    # confidenciales sin valor (se guardan como secreto).
    posiciones = set(valores.keys())
    posiciones.update(p for p, st in estados.items() if "C" in str(st) and p not in valores)

    resultado: list[ObservacionParseada] = []
    periodos_no_reconocidos: set[str] = set()

    for pos_texto in posiciones:
        coords = _coordenadas(int(pos_texto), tamanos)
        codigo_geo = dims[i_geo].codigos[coords[i_geo]]
        if clasificar_geo(codigo_geo) is None:
            continue

        codigo_time = dims[i_time].codigos[coords[i_time]]
        periodo = periodo_desde_time(codigo_time)
        if periodo is None:
            periodos_no_reconocidos.add(codigo_time)
            continue
        fecha, anyo, periodo_codigo = periodo

        partes_codigo = []
        partes_nombre = []
        atributos: dict[str, Any] = {}
        for i, dim in enumerate(dims):
            if dim.id in _DIMENSIONES_NO_SERIE:
                continue
            codigo = dim.codigos[coords[i]]
            etiqueta = dim.etiquetas.get(codigo, codigo)
            partes_codigo.append(f"{dim.id}={codigo}")
            if dim.id != "freq":
                partes_nombre.append(etiqueta)
            atributos[dim.id] = {"nombre": etiqueta, "codigo": codigo}

        etiqueta_geo = dims[i_geo].etiquetas.get(codigo_geo, codigo_geo)
        estado = estados.get(pos_texto)
        secreto = estado is not None and "C" in str(estado)
        valor_bruto = valores.get(pos_texto)

        resultado.append(
            ObservacionParseada(
                territorio_clave=f"{PREFIJO_CLAVE_NUTS}{codigo_geo}",
                territorio_nombre_origen=etiqueta_geo,
                periodo_fecha=fecha,
                anyo=anyo,
                periodo_codigo=periodo_codigo,
                valor=None if valor_bruto is None or secreto else float(valor_bruto),
                unidad=(
                    dims[i_unit].etiquetas.get(dims[i_unit].codigos[coords[i_unit]])
                    if i_unit is not None
                    else None
                ),
                escala=None,
                tipo_dato=(etiquetas_estado.get(estado, estado) if estado else None),
                secreto=secreto,
                serie_nombre_origen=". ".join([etiqueta_geo, *partes_nombre]),
                serie_codigo_origen=f"{dataset}|{'.'.join(partes_codigo)}|{codigo_geo}",
                serie_atributos=atributos,
            )
        )

    if periodos_no_reconocidos:
        logger.warning(
            "%s: periodos no reconocidos (se omiten): %s",
            dataset, sorted(periodos_no_reconocidos)[:10],
        )
    return resultado
