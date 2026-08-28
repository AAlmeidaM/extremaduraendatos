"""Exporta los datos reales a CSV para un analisis descriptivo (uso puntual).

No modifica nada; solo lee la base de datos y vuelca CSVs a
_ejecucion_claude/ para que Claude los pueda leer desde el entorno cloud.

Uso: .venv\\Scripts\\python.exe scripts\\exportar_analisis.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extremadura_datos.config import Config
from extremadura_datos import db


def volcar(cur, sql, params, ruta: Path) -> int:
    cur.execute(sql, params)
    cols = [d.name for d in cur.description]
    n = 0
    with ruta.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for row in cur.fetchall():
            w.writerow(row)
            n += 1
    return n


def main() -> int:
    cfg = Config.load()
    conn = db.connect(cfg.database_url)
    out_dir = Path(__file__).resolve().parents[1] / "_ejecucion_claude"
    out_dir.mkdir(parents=True, exist_ok=True)

    with conn.cursor() as cur:
        n1 = volcar(
            cur,
            """
            SELECT i.codigo AS indicador, i.categoria, i.nivel_territorial,
                   i.periodicidad, i.tabla_id_externo,
                   t.nivel AS territorio_nivel, t.nombre AS territorio_nombre,
                   s.nombre_origen AS serie_nombre,
                   o.periodo_fecha, o.anyo, o.valor, o.unidad, o.escala
            FROM observacion o
            JOIN serie s ON s.id = o.serie_id
            JOIN indicador i ON i.id = s.indicador_id
            JOIN territorio t ON t.id = s.territorio_id
            WHERE i.activo
            ORDER BY i.codigo, t.nombre, o.periodo_fecha
            """,
            (),
            out_dir / "observaciones.csv",
        )
        print("observaciones.csv:", n1, "filas")

        n2 = volcar(
            cur,
            """
            SELECT codigo, nombre, categoria, nivel_territorial, periodicidad,
                   tabla_id_externo, activo
            FROM indicador
            ORDER BY categoria, codigo
            """,
            (),
            out_dir / "indicadores.csv",
        )
        print("indicadores.csv:", n2, "filas")

    conn.close()
    print("EXPORTACION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
