"""Comprueba, tras una ingesta, cuántas filas hay por indicador en la base
de datos real. Pensado para ejecutarse justo después de
`python -m extremadura_datos.ingest --modo historico`.

Uso: .venv\\Scripts\\python.exe scripts\\verificar_carga.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extremadura_datos.config import Config
from extremadura_datos import db


def main() -> int:
    cfg = Config.load()
    conn = db.connect(cfg.database_url)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT i.codigo, i.activo, count(o.id) AS filas,
                   min(o.periodo_fecha) AS desde, max(o.periodo_fecha) AS hasta
            FROM indicador i
            LEFT JOIN serie s ON s.indicador_id = i.id
            LEFT JOIN observacion o ON o.serie_id = s.id
            GROUP BY i.codigo, i.activo
            ORDER BY i.codigo
            """
        )
        filas = cur.fetchall()

    print(f"{'indicador':<45} {'activo':<7} {'filas':>7}  {'desde':<12} {'hasta':<12}")
    print("-" * 90)
    total = 0
    sin_datos = []
    for codigo, activo, num_filas, desde, hasta in filas:
        total += num_filas or 0
        print(f"{codigo:<45} {str(activo):<7} {num_filas:>7}  {str(desde or ''):<12} {str(hasta or ''):<12}")
        if activo and not num_filas:
            sin_datos.append(codigo)

    print("-" * 90)
    print(f"TOTAL observaciones: {total}")
    print(f"Indicadores activos SIN ninguna fila: {sin_datos if sin_datos else 'ninguno'}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
