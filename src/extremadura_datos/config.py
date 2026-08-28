"""Carga de configuración desde variables de entorno (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Busca el .env en la raíz del proyecto (dos niveles por encima de este archivo:
# src/extremadura_datos/config.py -> raíz del proyecto).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Falta la variable de entorno {name}. "
            f"Copia .env.example a .env y rellénala (ver README.md)."
        )
    return value


@dataclass(frozen=True)
class Config:
    database_url: str
    log_dir: Path
    datasets_dir: Path
    ine_api_base: str
    ine_request_timeout: int
    ine_request_delay_seconds: float
    log_level: str

    @classmethod
    def load(cls) -> "Config":
        return cls(
            database_url=_require("DATABASE_URL"),
            log_dir=Path(os.environ.get("LOG_DIR", str(_PROJECT_ROOT / "logs"))),
            datasets_dir=Path(
                os.environ.get("DATASETS_DIR", str(_PROJECT_ROOT / "datasets"))
            ),
            ine_api_base=os.environ.get(
                "INE_API_BASE", "https://servicios.ine.es/wstempus/js/ES"
            ),
            ine_request_timeout=int(os.environ.get("INE_REQUEST_TIMEOUT", "30")),
            ine_request_delay_seconds=float(
                os.environ.get("INE_REQUEST_DELAY_SECONDS", "1")
            ),
            log_level=os.environ.get("LOG_LEVEL", "info"),
        )

    def ensure_dirs(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.datasets_dir.mkdir(parents=True, exist_ok=True)


PROJECT_ROOT = _PROJECT_ROOT
