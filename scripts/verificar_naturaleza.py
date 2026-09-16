"""Resumen de naturaleza_dato_efectiva por indicador en v_analisis.

Sirve para comprobar la corrección del 2026-09-16 (las series de variación
del INE, identificadas por la dimensión "Tipo de dato" de la serie, deben
salir como 'tasa'). Aplica antes el esquema (idempotente).

Uso: .venv\\Scripts\\python.exe scripts\\verificar_naturaleza.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extremadura_datos import db
from extremadura_datos.config import Config


def main() -> int:
    cfg = Config.load()
    conn = db.connect(cfg.database_url)
    db.ensure_schema(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT i.codigo,
                   count(DISTINCT s.id) FILTER (WHERE s.atributos ? 'Tipo de dato') AS series_con_tipo,
                   count(DISTINCT s.id) AS series
            FROM indicador i JOIN serie s ON s.indicador_id = i.id
            WHERE i.fuente_id = (SELECT id FROM fuente WHERE codigo = 'ine')
            GROUP BY i.codigo ORDER BY i.codigo
            """
        )
        print("Series del INE con dimension 'Tipo de dato':")
        for fila in cur.fetchall():
            print(f"  {fila[0]:<45} {fila[1]:>5} / {fila[2]:<5}")
        cur.execute(
            """
            SELECT indicador, naturaleza_dato_tabla, naturaleza_dato_efectiva, count(*)
            FROM v_analisis
            WHERE fuente = 'ine'
            GROUP BY 1, 2, 3 ORDER BY 1, 3
            """
        )
        print("\nnaturaleza tabla -> efectiva (INE):")
        for fila in cur.fetchall():
            print(f"  {fila[0]:<45} {str(fila[1]):<10} -> {str(fila[2]):<10} {fila[3]:>9}")
        cur.execute(
            """
            SELECT DISTINCT s.atributos->'Tipo de dato'->>'nombre'
            FROM serie s JOIN indicador i ON i.id = s.indicador_id
            WHERE i.codigo = 'ine_ipc_ccaa'
            """
        )
        print("\nValores de 'Tipo de dato' en el IPC:", [r[0] for r in cur.fetchall()])
        cur.execute(
            """
            SELECT t.nombre, vp.periodo_fecha, vp.poblacion, vp.prioridad, vp.indicador
            FROM v_poblacion vp JOIN territorio t ON t.id = vp.territorio_id
            WHERE t.nombre IN ('Extremadura', 'Badajoz', 'Cáceres', 'España')
              AND vp.periodo_fecha >= DATE '2024-10-01'
            ORDER BY t.nombre, vp.periodo_fecha DESC, vp.prioridad
            """
        )
        print("\nv_poblacion (desde 2024-10):")
        for fila in cur.fetchall():
            print("  ", fila)
        cur.execute(
            """
            SELECT indicador, count(*) FILTER (WHERE valor_por_1000_habitantes IS NOT NULL), count(*),
                   max(poblacion_fecha_referencia), array_agg(DISTINCT poblacion_fuente)
            FROM v_analisis WHERE naturaleza_dato_efectiva = 'conteo' AND fuente = 'ine'
              AND territorio = 'Extremadura'
            GROUP BY 1 ORDER BY 1
            """
        )
        print("\nconteos INE con valor_por_1000_habitantes:", cur.fetchall())
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
