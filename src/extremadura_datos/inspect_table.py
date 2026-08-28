"""Utilidad de diagnóstico: descarga una tabla del INE tal cual y la vuelca a
disco, sin intentar interpretarla. Pensada para la PRIMERA ejecución en el PC
(que sí tiene salida a internet, a diferencia del entorno donde se escribió
este proyecto) — para confirmar cómo es de verdad el JSON antes de fiarse del
parseo de parse.py.

Uso:
    python -m extremadura_datos.inspect_table 75803
    python -m extremadura_datos.inspect_table 75803 --nult 2
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone

from .config import Config
from .ine_client import IneClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tabla_id", help="Id de tabla del INE, p.ej. 75803")
    parser.add_argument("--nult", type=int, default=3, help="Nº de periodos más recientes (por defecto 3)")
    args = parser.parse_args()

    cfg = Config.load()
    cfg.ensure_dirs()

    cliente = IneClient(cfg.ine_api_base, cfg.ine_request_timeout, cfg.ine_request_delay_seconds)
    logger.info("Pidiendo tabla %s (nult=%s)...", args.tabla_id, args.nult)
    datos = cliente.fetch_tabla(args.tabla_id, tip="AM", nult=args.nult)

    raw_dir = cfg.datasets_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destino = raw_dir / f"tabla_{args.tabla_id}_{marca}.json"
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("Guardado en %s", destino)
    n_series = len(datos) if isinstance(datos, list) else "?"
    logger.info("Nº de series recibidas: %s", n_series)

    if isinstance(datos, list) and datos:
        primera = datos[0]
        print("\n--- Primera serie (para ver los nombres de campo reales) ---")
        print(json.dumps(primera, ensure_ascii=False, indent=2)[:4000])
        print(
            "\nCampos esperados (confirmados 2026-08-28 contra tablas 50913 y 3996): "
            "COD, Nombre, T3_Unidad, T3_Escala, MetaData (lista de dimensiones con "
            "T3_Variable/Nombre/Codigo), Data (con Fecha ISO8601, T3_TipoDato, "
            "T3_Periodo, Anyo, Valor, Secreto). Si esta tabla no los trae así, "
            "revisa parsear_tabla() en parse.py."
        )
    else:
        print("\nLa respuesta no fue una lista de series; revisa el JSON completo en:")
        print(destino)


if __name__ == "__main__":
    sys.exit(main() or 0)
