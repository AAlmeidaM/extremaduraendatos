"""Punto de entrada de la ingesta.

Recorre INDICADORES (indicadores.py), descarga cada tabla del INE, la filtra
a Extremadura/Badajoz/Cáceres, y hace upsert en PostgreSQL. Tiene dos modos:

- `--modo incremental` (por defecto): pide solo los últimos NULT_POR_DEFECTO
  periodos, y solo de verdad -- desde 2026-08-28 este modo consulta primero
  el calendario oficial de publicaciones del INE (ver calendario.py) y salta
  la llamada real a la API para las tablas que ese calendario dice que no
  tienen publicación pendiente hoy. (Decisión anterior, ahora sustituida:
  llamar siempre a las 23 tablas activas y confiar en que el upsert es
  idempotente -- ver PROJECT.md §17 para el porqué del cambio.) Es el modo
  que usa la tarea programada diaria (scripts\\run_ingesta.ps1); el upsert
  sigue siendo idempotente, así que da igual si algún día no llega a
  ejecutarse -- se pone al día en cuanto vuelva a correr.
- `--modo historico`: pide TODO el histórico disponible de la tabla (sin
  límite `nult`). Se usa para la carga inicial de cada fuente (una vez), para
  poder agregar y comparar series completas a nivel CCAA/provincia desde el
  principio.

Uso:
    python -m extremadura_datos.ingest                              # incremental, todas las fuentes
    python -m extremadura_datos.ingest --solo ine_ipc_ccaa           # incremental, una fuente
    python -m extremadura_datos.ingest --modo historico --solo ine_ipc_ccaa   # histórico completo, una fuente
    python -m extremadura_datos.ingest --modo historico              # histórico completo, todas las fuentes
    python -m extremadura_datos.ingest --modo historico --fuente eurostat     # solo los indicadores de Eurostat

Fuentes (2026-09-15): cada indicador declara su `fuente` en indicadores.py.
'ine' sigue el flujo descrito arriba (calendario del INE incluido);
'eurostat' se delega en eurostat_ingest.py, que en modo incremental usa la
fecha `updated` de Eurostat en vez de un calendario.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone

from . import calendario, db, eurostat_ingest
from .config import Config
from .eurostat_client import EurostatClient
from .indicadores import INDICADORES
from .ine_client import IneApiError, IneClient
from .parse import parsear_tabla

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Nº de periodos recientes a pedir en modo incremental (tarea diaria). Con 8
# sobra para no perder ninguna revisión reciente del INE (que a veces
# recalcula datos ya publicados) sin tener que traer el histórico completo
# cada día. En modo histórico se ignora (se pide todo, nult=None).
NULT_POR_DEFECTO = 8


def _guarda_json_crudo(cfg: Config, tabla_id: str, datos) -> None:
    raw_dir = cfg.datasets_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destino = raw_dir / f"tabla_{tabla_id}_{marca}.json"
    destino.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")


def ingerir_indicador(
    conn, cfg: Config, cliente: IneClient, indicador, nult: int | None
) -> None:
    logger.info(
        "--- %s (tabla INE %s, nult=%s) ---",
        indicador.codigo, indicador.tabla_id_externo, nult if nult is not None else "TODO",
    )
    indicador_id = db.get_or_create_indicador(conn, indicador)

    try:
        datos = cliente.fetch_tabla(indicador.tabla_id_externo, tip="AM", nult=nult)
    except IneApiError as exc:
        logger.error("Fallo al descargar %s: %s", indicador.codigo, exc)
        db.registrar_carga(conn, indicador_id, "error", str(exc))
        return

    _guarda_json_crudo(cfg, indicador.tabla_id_externo, datos)

    filas = parsear_tabla(datos, indicador.filtro_territorio, indicador.periodicidad)
    if not filas:
        mensaje = (
            "0 filas tras filtrar por territorio — esta tabla concreta puede "
            "tener alguna particularidad no vista en las tablas ya verificadas "
            "(ver docs/fuentes-ine.md). Revisa el JSON crudo con "
            "inspect_table.py y ajusta parsear_tabla() en parse.py si hace falta."
        )
        logger.warning(mensaje)
        db.registrar_carga(conn, indicador_id, "error", mensaje, filas_leidas=0)
        return

    n_upsert, total = db.upsert_observaciones(conn, indicador_id, filas)
    logger.info("%s: %d filas cargadas/actualizadas.", indicador.codigo, n_upsert)
    db.registrar_carga(
        conn, indicador_id, "ok", "ok",
        filas_leidas=total, filas_insertadas=n_upsert, filas_actualizadas=n_upsert,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--solo", help="Ingerir solo el indicador con este código (ver indicadores.py)"
    )
    parser.add_argument(
        "--modo",
        choices=["incremental", "historico"],
        default="incremental",
        help=(
            "'incremental' (por defecto, usado por la tarea diaria): pide solo "
            "los últimos %d periodos. 'historico': pide TODO el histórico "
            "disponible de la tabla — usar para la carga inicial de cada fuente."
        ) % NULT_POR_DEFECTO,
    )
    parser.add_argument(
        "--fuente",
        choices=["ine", "eurostat"],
        help="Ingerir solo los indicadores de esta fuente.",
    )
    args = parser.parse_args()
    nult = None if args.modo == "historico" else NULT_POR_DEFECTO

    cfg = Config.load()
    cfg.ensure_dirs()

    indicadores = [i for i in INDICADORES if i.codigo == args.solo] if args.solo else INDICADORES
    if args.fuente:
        indicadores = [i for i in indicadores if i.fuente == args.fuente]
    if not indicadores:
        logger.error("No hay ningún indicador para --solo=%r --fuente=%r.", args.solo, args.fuente)
        return 1

    conn = db.connect(cfg.database_url)
    hubo_error = False
    try:
        db.ensure_schema(conn)
        cliente = IneClient(cfg.ine_api_base, cfg.ine_request_timeout, cfg.ine_request_delay_seconds)
        cliente_eurostat = EurostatClient(
            cfg.eurostat_api_base, cfg.eurostat_request_timeout, cfg.eurostat_request_delay_seconds
        )
        for indicador in indicadores:
            if not indicador.activo:
                continue
            try:
                if indicador.fuente == "eurostat":
                    eurostat_ingest.ingerir_indicador(
                        conn, cfg, cliente_eurostat, indicador, args.modo
                    )
                    continue
                indicador_id = db.get_or_create_indicador(conn, indicador)
                if args.modo == "incremental" and not calendario.debe_ingerir_hoy(
                    conn, cliente, indicador_id, indicador
                ):
                    logger.info(
                        "%s: el calendario del INE no marca publicación pendiente hoy -- se omite.",
                        indicador.codigo,
                    )
                    continue
                ingerir_indicador(conn, cfg, cliente, indicador, nult=nult)
                if args.modo == "incremental":
                    calendario.marcar_procesado(conn, indicador_id)
            except Exception:  # noqa: BLE001 - se registra y se sigue con el resto
                logger.exception("Error inesperado ingiriendo %s", indicador.codigo)
                # Deja la conexión usable para el siguiente indicador (si el
                # fallo ocurrió a mitad de una transacción, sin esto todas
                # las consultas siguientes fallarían con "transaction aborted").
                conn.rollback()
                hubo_error = True
    finally:
        conn.close()

    logger.info("Ingesta terminada.")
    return 1 if hubo_error else 0


if __name__ == "__main__":
    sys.exit(main())
