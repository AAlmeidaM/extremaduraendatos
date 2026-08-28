"""Informe legible de la estructura del esquema y los datos reales cargados.

Uso: .venv\\Scripts\\python.exe scripts\\reporte_estructura.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extremadura_datos.config import Config
from extremadura_datos import db


def linea(*args):
    print(*args)


def main() -> int:
    cfg = Config.load()
    conn = db.connect(cfg.database_url)

    with conn.cursor() as cur:
        linea("=" * 90)
        linea("TOTALES GENERALES")
        linea("=" * 90)
        cur.execute("SELECT count(*) FROM fuente")
        linea("fuentes:     ", cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM territorio")
        linea("territorios: ", cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM indicador")
        linea("indicadores: ", cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM indicador WHERE activo")
        linea("  activos:   ", cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM serie")
        linea("series:      ", cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM observacion")
        linea("observaciones:", cur.fetchone()[0])

        linea()
        linea("=" * 90)
        linea("POR TERRITORIO")
        linea("=" * 90)
        cur.execute(
            """
            SELECT t.nivel, t.nombre, count(DISTINCT s.id) AS series, count(o.id) AS observaciones
            FROM territorio t
            LEFT JOIN serie s ON s.territorio_id = t.id
            LEFT JOIN observacion o ON o.serie_id = s.id
            GROUP BY t.nivel, t.nombre
            ORDER BY t.nivel, t.nombre
            """
        )
        linea(f"{'nivel':<12} {'territorio':<15} {'series':>8} {'observaciones':>15}")
        for nivel, nombre, series, obs in cur.fetchall():
            linea(f"{nivel:<12} {nombre:<15} {series:>8} {obs:>15}")

        linea()
        linea("=" * 90)
        linea("POR CATEGORIA")
        linea("=" * 90)
        cur.execute(
            """
            SELECT i.categoria, count(DISTINCT i.id) AS indicadores,
                   count(DISTINCT s.id) AS series, count(o.id) AS observaciones
            FROM indicador i
            LEFT JOIN serie s ON s.indicador_id = i.id
            LEFT JOIN observacion o ON o.serie_id = s.id
            GROUP BY i.categoria
            ORDER BY observaciones DESC
            """
        )
        linea(f"{'categoria':<22} {'indicadores':>12} {'series':>8} {'observaciones':>15}")
        for cat, num_ind, series, obs in cur.fetchall():
            linea(f"{cat:<22} {num_ind:>12} {series:>8} {obs:>15}")

        linea()
        linea("=" * 90)
        linea("POR PERIODICIDAD")
        linea("=" * 90)
        cur.execute(
            """
            SELECT i.periodicidad, count(DISTINCT i.id) AS indicadores, count(o.id) AS observaciones
            FROM indicador i
            LEFT JOIN serie s ON s.indicador_id = i.id
            LEFT JOIN observacion o ON o.serie_id = s.id
            GROUP BY i.periodicidad
            ORDER BY observaciones DESC
            """
        )
        linea(f"{'periodicidad':<15} {'indicadores':>12} {'observaciones':>15}")
        for per, num_ind, obs in cur.fetchall():
            linea(f"{per:<15} {num_ind:>12} {obs:>15}")

        linea()
        linea("=" * 90)
        linea("POR INDICADOR (detalle completo)")
        linea("=" * 90)
        cur.execute(
            """
            SELECT i.codigo, i.categoria, i.nivel_territorial, i.periodicidad, i.activo,
                   i.tabla_id_externo,
                   count(DISTINCT s.id) AS series,
                   count(o.id) AS observaciones,
                   min(o.periodo_fecha) AS desde, max(o.periodo_fecha) AS hasta
            FROM indicador i
            LEFT JOIN serie s ON s.indicador_id = i.id
            LEFT JOIN observacion o ON o.serie_id = s.id
            GROUP BY i.id, i.codigo, i.categoria, i.nivel_territorial, i.periodicidad, i.activo, i.tabla_id_externo
            ORDER BY i.categoria, i.codigo
            """
        )
        linea(
            f"{'indicador':<42} {'tabla':>7} {'categoria':<18} {'nivel':<16} "
            f"{'period.':<11} {'series':>7} {'obs':>7}  {'desde':<11} {'hasta':<11}"
        )
        for codigo, cat, nivel, per, activo, tabla, series, obs, desde, hasta in cur.fetchall():
            marca = "" if activo else " [INACTIVO]"
            linea(
                f"{codigo:<42} {tabla:>7} {cat:<18} {nivel:<16} {per:<11} "
                f"{series:>7} {obs:>7}  {str(desde or ''):<11} {str(hasta or ''):<11}{marca}"
            )

        linea()
        linea("=" * 90)
        linea("ESTRUCTURA DE LAS TABLAS (columnas)")
        linea("=" * 90)
        for tabla in ("fuente", "territorio", "indicador", "serie", "observacion", "carga_log"):
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
                """,
                (tabla,),
            )
            linea(f"\n-- {tabla} --")
            for col, tipo, nullable in cur.fetchall():
                linea(f"  {col:<20} {tipo:<25} {'NULL' if nullable == 'YES' else 'NOT NULL'}")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
