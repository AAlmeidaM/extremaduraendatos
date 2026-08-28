"""Descarga JSON crudo del INE para unas pocas tablas 'insignia', para poder
comparar Extremadura contra el resto de CCAA. Uso puntual (no toca la base
de datos ni el pipeline de produccion); solo lee de la API publica del INE
y escribe JSON crudo a _ejecucion_claude/ine_raw/ para que Claude lo analice.

Uso: .venv\\Scripts\\python.exe scripts\\fetch_comparativa_nacional.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extremadura_datos.config import Config
from extremadura_datos.ine_client import IneClient

# Tablas insignia elegidas para comparar Extremadura vs resto de Espana:
# cubren precios, empleo, industria, turismo y vivienda con una sola serie
# "cabecera" facil de identificar por tabla.
TABLAS = {
    "50913": "IPC (indice general, CCAA)",
    "75803": "Tasa de paro EPA (CCAA)",
    "26061": "Indice de Produccion Industrial (CCAA)",
    "2074": "Viajeros y pernoctaciones totales (CCAA)",
    "25171": "Indice de Precios de Vivienda (CCAA)",
    "13912": "Resumen sociedades mercantiles (CCAA)",
    "8027": "Confianza empresarial (CCAA)",
}


def main() -> int:
    cfg = Config.load()
    client = IneClient(cfg.ine_api_base, timeout=cfg.ine_request_timeout, delay_seconds=cfg.ine_request_delay_seconds)
    out_dir = Path(__file__).resolve().parents[1] / "_ejecucion_claude" / "ine_raw"
    out_dir.mkdir(parents=True, exist_ok=True)

    for tabla_id, etiqueta in TABLAS.items():
        print(f"Descargando {tabla_id} ({etiqueta})...")
        try:
            datos = client.fetch_tabla(tabla_id, tip="AM", nult=6)
        except Exception as exc:
            print(f"  ERROR en {tabla_id}: {exc}")
            continue
        ruta = out_dir / f"{tabla_id}.json"
        ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        n = len(datos) if isinstance(datos, list) else 0
        print(f"  OK: {n} series -> {ruta.name}")

    print("DESCARGA_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
