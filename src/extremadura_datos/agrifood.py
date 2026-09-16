"""Portal Agri-food de la Comisión Europea (DG AGRI): precios agrarios por
Estado miembro y media de la UE. Fase 3 de docs/ampliacion-nuts2-agro.md.

API verificada contra el servicio real el 2026-09-15/16
(docs/fuentes-europa-agro.md §2):

- Base `https://api.tech.ec.europa.eu/agrifood/api/`, sin autenticación, con
  límite de peticiones (HTTP 429) → pausa entre peticiones y reintentos.
- `beginDate`/`endDate` en `dd/MM/yyyy`; `memberStateCodes` admite lista
  separada por comas. Sin datos para el filtro → HTTP 404 con
  "No results found" (no es un error).
- Precios en texto con símbolo y decimal inconsistente (ver
  precios_util.precio_desde_texto).
- Duplicados reales: en el cambio de campaña (cereales, aceite) la misma
  semana sale dos veces con distinto `weekNumber`/`marketingYear` y el mismo
  precio → db.upsert_observaciones deduplica.
- Códigos de Estado miembro: los de Eurostat (Grecia = EL) más `EU` (media
  UE). `EU+UK` y `UK` se descartan.
- Mercados con código NUTS3 entre paréntesis (aceite: "Badajoz (ES431)") o
  nombre de mercado (cereales: "Badajoz"): si es Badajoz/Cáceres la serie
  va a la provincia; el resto de mercados cuelga del país con el mercado en
  `serie.atributos`.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import requests

from . import db
from .config import Config
from .eurostat_parse import PREFIJO_CLAVE_NUTS, clasificar_geo
from .indicadores import Indicador
from .parse import ObservacionParseada
from .precios_util import (
    MESES_EN,
    fecha_ddmmyyyy,
    guarda_crudo,
    periodo_mensual,
    periodo_semanal,
    precio_desde_texto,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.tech.ec.europa.eu/agrifood/api"
PAUSA_SEGUNDOS = 1.5
AÑO_INICIO_HISTORICO = 2010
SEMANAS_INCREMENTAL = 10

AGREGADOS_UE = {"EU", "EU-UK", "EU27"}
MERCADOS_PROVINCIA = {"badajoz": "ES431", "caceres": "ES432", "cáceres": "ES432"}

UNIDADES = {
    "100 kg": "€/100 kg", "100kg": "€/100 kg", "€/100kg": "€/100 kg",
    "tonnes": "€/t", "€/tonne": "€/t", "p": "€/cabeza",
}


@dataclass(frozen=True)
class _Endpoint:
    dimensiones: tuple[str, ...]  # campos que distinguen la serie (además del territorio)
    mensual: bool = False
    campo_mercado: str | None = None


ENDPOINTS: dict[str, _Endpoint] = {
    "pigmeat/prices": _Endpoint(("pigClass",)),
    "beef/prices": _Endpoint(("category", "productCode")),
    "sheepAndGoat/prices": _Endpoint(("category", "marketName")),
    "cereal/prices": _Endpoint(("productName", "marketName", "stageName"), campo_mercado="marketName"),
    "oliveOil/prices": _Endpoint(("product", "market"), campo_mercado="market"),
    "rawMilk/prices": _Endpoint(("product",), mensual=True),
    "fertiliser/prices": _Endpoint(("product",), mensual=True),
}


class AgrifoodApiError(RuntimeError):
    pass


class AgrifoodClient:
    def __init__(self, base_url: str = BASE_URL, timeout: int = 120, pausa: float = PAUSA_SEGUNDOS):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.pausa = pausa
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "extremadura-en-datos/0.1 (uso personal, Office Lab)"})

    def get(self, endpoint: str, params: list[tuple[str, Any]]) -> list[dict[str, Any]]:
        url = f"{self.base_url}/{endpoint}"
        for intento in range(4):
            time.sleep(self.pausa)
            resp = self._session.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                datos = resp.json()
                return datos if isinstance(datos, list) else []
            if resp.status_code == 404 and "No results" in resp.text:
                return []
            if resp.status_code in (429, 503) and intento < 3:
                espera = 60 * (intento + 1)
                logger.warning("Agri-food %s: HTTP %s, reintento en %ss", endpoint, resp.status_code, espera)
                time.sleep(espera)
                continue
            raise AgrifoodApiError(f"HTTP {resp.status_code} en {endpoint} {params}: {resp.text[:300]}")
        return []


def _territorio(fila: dict[str, Any], ep: _Endpoint) -> str | None:
    """Clave de territorio (prefijo nuts:) o None si la fila se descarta."""
    if ep.campo_mercado:
        mercado = str(fila.get(ep.campo_mercado) or "")
        codigo = re.search(r"\((ES4\d{2})\)", mercado)
        if codigo and codigo.group(1) in MERCADOS_PROVINCIA.values():
            return PREFIJO_CLAVE_NUTS + codigo.group(1)
        nombre = mercado.split("(")[0].strip().lower()
        if nombre in MERCADOS_PROVINCIA:
            return PREFIJO_CLAVE_NUTS + MERCADOS_PROVINCIA[nombre]
    codigo_ms = fila.get("memberStateCode")
    if codigo_ms is None and str(fila.get("memberStateName", "")).lower() in {"european commission", "european union"}:
        codigo_ms = "EU"
    if codigo_ms in AGREGADOS_UE:
        return PREFIJO_CLAVE_NUTS + "EU27_2020"
    if codigo_ms and clasificar_geo(str(codigo_ms)) == "pais":
        return PREFIJO_CLAVE_NUTS + str(codigo_ms)
    return None


def parsear(endpoint: str, filas: list[dict[str, Any]]) -> list[ObservacionParseada]:
    ep = ENDPOINTS[endpoint]
    resultado: list[ObservacionParseada] = []
    for fila in filas:
        valor = precio_desde_texto(fila.get("price"))
        if valor is None:
            continue
        clave = _territorio(fila, ep)
        if clave is None:
            continue
        try:
            if ep.mensual:
                if fila.get("beginDate"):
                    inicio = fecha_ddmmyyyy(fila["beginDate"])
                    fecha, anyo, codigo = periodo_mensual(inicio.year, inicio.month)
                else:
                    mes = MESES_EN[str(fila["month"]).strip().lower()[:3]]
                    fecha, anyo, codigo = periodo_mensual(int(fila["year"]), mes)
            else:
                fecha, anyo, codigo = periodo_semanal(fecha_ddmmyyyy(fila["beginDate"]))
        except (KeyError, ValueError):
            logger.warning("Agri-food %s: fila con periodo ilegible, se omite: %s", endpoint, fila)
            continue

        unidad_origen = str(fila.get("unit") or "")
        atributos = {d: {"nombre": fila.get(d), "codigo": fila.get(d)} for d in ep.dimensiones}
        atributos["unidad_origen"] = {"nombre": unidad_origen, "codigo": unidad_origen}
        partes = ".".join(f"{d}={fila.get(d)}" for d in ep.dimensiones)
        territorio = clave[len(PREFIJO_CLAVE_NUTS):]
        nombre_territorio = fila.get("memberStateName") or territorio
        resultado.append(
            ObservacionParseada(
                territorio_clave=clave,
                territorio_nombre_origen=str(nombre_territorio),
                periodo_fecha=fecha,
                anyo=anyo,
                periodo_codigo=codigo,
                valor=valor,
                unidad=UNIDADES.get(unidad_origen.strip().lower(), unidad_origen or None),
                escala=None,
                tipo_dato=None,
                secreto=False,
                serie_nombre_origen=". ".join(
                    str(x) for x in [nombre_territorio, *(fila.get(d) for d in ep.dimensiones)] if x
                ),
                serie_codigo_origen=f"agrifood|{endpoint}|{partes}|{unidad_origen}|{territorio}",
                serie_atributos=atributos,
            )
        )
    return resultado


def _ventanas(modo: str, hoy: date) -> list[tuple[date, date]]:
    if modo == "incremental":
        return [(hoy - timedelta(weeks=SEMANAS_INCREMENTAL), hoy)]
    return [(date(a, 1, 1), date(a, 12, 31)) for a in range(AÑO_INICIO_HISTORICO, hoy.year + 1)]


def ingerir_indicador(conn, cfg: Config, cliente: AgrifoodClient, indicador: Indicador, modo: str) -> None:
    indicador_id = db.get_or_create_indicador(conn, indicador)
    endpoint = indicador.tabla_id_externo
    filtros = list(indicador.parametros_api)
    hoy = date.today()
    total = 0
    errores: list[str] = []
    logger.info("--- %s (Agri-food %s, modo %s) ---", indicador.codigo, endpoint, modo)

    if endpoint == "fertiliser/prices":
        años = [hoy.year - 1, hoy.year] if modo == "incremental" else range(AÑO_INICIO_HISTORICO, hoy.year + 1)
        peticiones = [[("years", a)] for a in años]
    else:
        peticiones = [
            filtros + [("beginDate", ini.strftime("%d/%m/%Y")), ("endDate", fin.strftime("%d/%m/%Y"))]
            for ini, fin in _ventanas(modo, hoy)
        ]

    for params in peticiones:
        try:
            filas = cliente.get(endpoint, params)
        except (AgrifoodApiError, requests.RequestException) as exc:
            logger.error("%s: %s", indicador.codigo, exc)
            errores.append(str(exc))
            continue
        if not filas:
            continue
        guarda_crudo(cfg.datasets_dir, "agrifood", endpoint.replace("/", "_"), filas)
        obs = parsear(endpoint, filas)
        if obs:
            n, _ = db.upsert_observaciones(conn, indicador_id, obs)
            total += n

    estado = "error" if errores and total == 0 else "ok"
    mensaje = "ok" if not errores else f"{len(errores)} peticiones fallidas: {errores[0][:500]}"
    logger.info("%s: %d filas cargadas/actualizadas.", indicador.codigo, total)
    db.registrar_carga(conn, indicador_id, estado, mensaje, filas_leidas=total, filas_insertadas=total)
