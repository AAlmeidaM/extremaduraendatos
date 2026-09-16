"""Índice de Precios de los Alimentos de la FAO (mensual, mundial, 2014-2016=100).
Fase 3 de docs/ampliacion-nuts2-agro.md.

Verificado el 2026-09-15 (docs/fuentes-europa-agro.md §3):

- El CSV se enlaza desde https://www.fao.org/worldfoodsituation/foodpricesindex/en/
  y su URL lleva un parámetro de versión (`?sfvrsn=...`) que cambia en cada
  publicación → se lee la página y se toma el enlace a
  `food_price_indices_data*.csv`.
- Formato: dos líneas de título ("FAO Food Price Index", "2014-2016=100"),
  cabecera `Date,Food Price Index,Meat,Dairy,Cereals,Oils,Sugar`, una línea
  vacía de comas y después `AAAA-MM,valor,...` (columnas de sobra vacías).
- Territorio: `Mundo` (codigo_nuts `WORLD`, sembrado en sql/001_schema.sql).
"""

from __future__ import annotations

import csv
import io
import logging
import re
from urllib.parse import urljoin

import requests

from . import db
from .config import Config
from .eurostat_parse import PREFIJO_CLAVE_NUTS
from .indicadores import Indicador
from .parse import ObservacionParseada
from .precios_util import guarda_crudo, periodo_mensual

logger = logging.getLogger(__name__)

PAGINA = "https://www.fao.org/worldfoodsituation/foodpricesindex/en/"
NOMBRES_ES = {
    "Food Price Index": "Índice general",
    "Meat": "Carne",
    "Dairy": "Lácteos",
    "Cereals": "Cereales",
    "Oils": "Aceites vegetales",
    "Sugar": "Azúcar",
}


class FaoError(RuntimeError):
    pass


def url_csv(html: str, base: str = PAGINA) -> str:
    enlaces = re.findall(r'href="([^"]*food_price_indices_data[^"]*\.csv[^"]*)"', html, flags=re.I)
    if not enlaces:
        raise FaoError("No se encontró el enlace al CSV del índice de la FAO en la página.")
    return urljoin(base, enlaces[0].replace("&amp;", "&"))


def parsear_csv(texto: str) -> list[ObservacionParseada]:
    filas = list(csv.reader(io.StringIO(texto)))
    try:
        i_cab = next(i for i, f in enumerate(filas) if f and f[0].strip().lower() == "date")
    except StopIteration as exc:
        raise FaoError("CSV de la FAO sin cabecera 'Date'.") from exc
    cabecera = [c.strip() for c in filas[i_cab]]
    columnas = [(j, c) for j, c in enumerate(cabecera) if j > 0 and c]
    resultado: list[ObservacionParseada] = []
    for fila in filas[i_cab + 1:]:
        if not fila or not re.fullmatch(r"\d{4}-\d{2}", fila[0].strip()):
            continue
        anyo, mes = (int(x) for x in fila[0].strip().split("-"))
        fecha, anyo, codigo = periodo_mensual(anyo, mes)
        for j, nombre in columnas:
            if j >= len(fila) or not fila[j].strip():
                continue
            try:
                valor = float(fila[j])
            except ValueError:
                continue
            etiqueta = NOMBRES_ES.get(nombre, nombre)
            resultado.append(
                ObservacionParseada(
                    territorio_clave=PREFIJO_CLAVE_NUTS + "WORLD",
                    territorio_nombre_origen="Mundo",
                    periodo_fecha=fecha,
                    anyo=anyo,
                    periodo_codigo=codigo,
                    valor=valor,
                    unidad="Índice 2014-2016=100",
                    escala=None,
                    tipo_dato=None,
                    secreto=False,
                    serie_nombre_origen=f"Mundo. Índice FAO de precios de los alimentos. {etiqueta}",
                    serie_codigo_origen=f"fao|ffpi|{nombre}",
                    serie_atributos={"grupo": {"nombre": etiqueta, "codigo": nombre}},
                )
            )
    return resultado


def ingerir_indicador(conn, cfg: Config, indicador: Indicador, modo: str) -> None:
    """Descarga el CSV completo (pocas KB) en ambos modos; el upsert es idempotente."""
    indicador_id = db.get_or_create_indicador(conn, indicador)
    logger.info("--- %s (FAO, modo %s) ---", indicador.codigo, modo)
    sesion = requests.Session()
    sesion.headers.update({"User-Agent": "Mozilla/5.0 (extremadura-en-datos; uso personal)"})
    try:
        pagina = sesion.get(PAGINA, timeout=60)
        pagina.raise_for_status()
        enlace = url_csv(pagina.text)
        resp = sesion.get(enlace, timeout=60)
        resp.raise_for_status()
        texto = resp.content.decode("utf-8-sig", errors="replace")
        filas = parsear_csv(texto)
    except (requests.RequestException, FaoError) as exc:
        logger.error("%s: %s", indicador.codigo, exc)
        db.registrar_carga(conn, indicador_id, "error", str(exc))
        return
    guarda_crudo(cfg.datasets_dir, "fao", "food_price_indices", texto, extension="csv")
    n, _ = db.upsert_observaciones(conn, indicador_id, filas)
    logger.info("%s: %d filas cargadas/actualizadas.", indicador.codigo, n)
    db.registrar_carga(conn, indicador_id, "ok", "ok", filas_leidas=n, filas_insertadas=n)
