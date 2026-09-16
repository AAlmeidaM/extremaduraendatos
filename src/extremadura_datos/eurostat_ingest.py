"""Ingesta de un indicador de Eurostat (fase 1 de docs/ampliacion-nuts2-agro.md).

Lo llama ingest.py para los indicadores con `fuente="eurostat"`. Mismo
patrón que la ingesta del INE: descargar → guardar JSON crudo → parsear →
upsert idempotente → registrar en `carga_log`.

Modos:

- `historico`: descarga todo el histórico del dataset (con los filtros de
  dimensión del catálogo).
- `incremental` (tarea diaria): Eurostat no tiene un calendario por tabla
  como el INE, pero cada respuesta trae `updated`. Primero se hace una
  petición mínima para leer ese `updated`; si coincide con el último ya
  cargado (`indicador.origen_actualizado`), no se descarga nada. Si cambió
  (o no se pudo leer — red de seguridad: ante la duda, se descarga), se
  piden solo los últimos AÑOS_INCREMENTAL años (Eurostat revisa datos
  recientes, no el histórico entero).
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone

from . import db
from .config import Config
from .eurostat_client import EurostatApiError, EurostatClient
from .eurostat_parse import parsear_dataset
from .indicadores import Indicador

logger = logging.getLogger(__name__)

AÑOS_INCREMENTAL = 6


def _guarda_json_crudo(cfg: Config, dataset: str, datos) -> None:
    raw_dir = cfg.datasets_dir / "raw" / "eurostat"
    raw_dir.mkdir(parents=True, exist_ok=True)
    marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destino = raw_dir / f"{dataset}_{marca}.json"
    destino.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")


def ingerir_indicador(
    conn, cfg: Config, cliente: EurostatClient, indicador: Indicador, modo: str
) -> None:
    indicador_id = db.get_or_create_indicador(conn, indicador)
    dataset = indicador.tabla_id_externo
    filtros = indicador.eurostat_filtros

    since = None
    actualizado_origen = None
    if modo == "incremental":
        actualizado_origen = cliente.fecha_actualizacion(dataset, filtros)
        ya_cargado = db.origen_actualizado(conn, indicador_id)
        if actualizado_origen is not None and actualizado_origen == ya_cargado:
            logger.info(
                "%s: Eurostat no ha actualizado %s desde la última carga (%s) -- se omite.",
                indicador.codigo, dataset, ya_cargado,
            )
            return
        since = date.today().year - AÑOS_INCREMENTAL

    logger.info(
        "--- %s (Eurostat %s, desde=%s) ---", indicador.codigo, dataset, since or "TODO"
    )
    try:
        datos = cliente.fetch_dataset(dataset, filtros, since_time_period=since)
    except EurostatApiError as exc:
        logger.error("Fallo al descargar %s: %s", indicador.codigo, exc)
        db.registrar_carga(conn, indicador_id, "error", str(exc))
        return

    _guarda_json_crudo(cfg, dataset, datos)

    filas = parsear_dataset(datos, dataset)
    if not filas:
        mensaje = (
            f"0 filas tras parsear {dataset} -- revisa el JSON crudo en "
            f"{cfg.datasets_dir / 'raw' / 'eurostat'} y eurostat_parse.py."
        )
        logger.warning(mensaje)
        db.registrar_carga(conn, indicador_id, "error", mensaje)
        return

    n_upsert, total = db.upsert_observaciones(conn, indicador_id, filas)
    logger.info("%s: %d filas cargadas/actualizadas.", indicador.codigo, n_upsert)
    db.registrar_carga(
        conn, indicador_id, "ok", "ok",
        filas_leidas=total, filas_insertadas=n_upsert, filas_actualizadas=n_upsert,
    )
    # Se guarda el `updated` de la descarga completa (el de la sonda puede no
    # existir en modo histórico).
    db.guardar_origen_actualizado(conn, indicador_id, datos.get("updated") or actualizado_origen)
