"""Aplica el esquema de base de datos (sql/001_schema.sql) sin ingerir nada.

Uso:
    python -m extremadura_datos.bootstrap_db
"""

from __future__ import annotations

import logging
import sys

from . import db
from .config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    cfg = Config.load()
    cfg.ensure_dirs()
    conn = db.connect(cfg.database_url)
    try:
        db.ensure_schema(conn)
        logger.info("Base de datos lista.")
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main() or 0)
