"""Resumen de la carga de precios agrarios (fase 3, 2026-09-16).

Uso: .venv\\Scripts\\python.exe scripts\\verificar_precios.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extremadura_datos import db
from extremadura_datos.config import Config

CONSULTAS = {
    "Por indicador (filas, series, territorios, desde, hasta)": """
        SELECT i.codigo, count(o.id), count(DISTINCT s.id), count(DISTINCT s.territorio_id),
               min(o.periodo_fecha), max(o.periodo_fecha)
        FROM indicador i JOIN serie s ON s.indicador_id = i.id JOIN observacion o ON o.serie_id = s.id
        WHERE i.categoria = 'precios_agrarios' GROUP BY 1 ORDER BY 1""",
    "Territorios de precios (nivel, nombre, filas)": """
        SELECT t.nivel, t.nombre, count(*)
        FROM observacion o JOIN serie s ON s.id = o.serie_id JOIN indicador i ON i.id = s.indicador_id
        JOIN territorio t ON t.id = s.territorio_id
        WHERE i.categoria = 'precios_agrarios' AND t.nivel IN ('provincia', 'agregado')
        GROUP BY 1, 2 ORDER BY 1, 2""",
    "Porcino clase S: España vs media UE (últimas 4 semanas)": """
        SELECT o.periodo_fecha, t.nombre, o.valor, o.unidad
        FROM observacion o JOIN serie s ON s.id = o.serie_id JOIN indicador i ON i.id = s.indicador_id
        JOIN territorio t ON t.id = s.territorio_id
        WHERE i.codigo = 'agrifood_porcino' AND s.atributos->'pigClass'->>'codigo' = 'S'
          AND t.codigo_nuts IN ('ES', 'EU27_2020')
          AND o.periodo_fecha >= (SELECT max(periodo_fecha) - 21 FROM observacion o2 WHERE o2.serie_id = s.id)
        ORDER BY 1 DESC, 2""",
    "Mercados de Badajoz en el portal Agri-food (serie, filas, última fecha, último valor)": """
        SELECT i.codigo, s.nombre_origen, count(*), max(o.periodo_fecha),
               (array_agg(o.valor ORDER BY o.periodo_fecha DESC))[1]
        FROM observacion o JOIN serie s ON s.id = o.serie_id JOIN indicador i ON i.id = s.indicador_id
        JOIN territorio t ON t.id = s.territorio_id
        WHERE i.fuente_id = (SELECT id FROM fuente WHERE codigo = 'agrifood') AND t.nombre = 'Badajoz'
        GROUP BY 1, 2 ORDER BY 1, 2""",
    "Observatorio Junta: producto, provincia, años con dato, filas, último valor": """
        SELECT s.atributos->'producto'->>'nombre', t.nombre,
               string_agg(DISTINCT o.anyo::text, ',' ORDER BY o.anyo::text), count(*),
               (array_agg(o.valor::text || ' ' || o.unidad || ' (' || o.periodo_fecha || ')' ORDER BY o.periodo_fecha DESC))[1]
        FROM observacion o JOIN serie s ON s.id = o.serie_id JOIN indicador i ON i.id = s.indicador_id
        JOIN territorio t ON t.id = s.territorio_id
        WHERE i.codigo = 'junta_precios_agricolas'
        GROUP BY 1, 2 ORDER BY 1, 2""",
    "Índice FAO (últimos 3 meses)": """
        SELECT o.periodo_fecha, s.atributos->'grupo'->>'nombre', o.valor
        FROM observacion o JOIN serie s ON s.id = o.serie_id JOIN indicador i ON i.id = s.indicador_id
        WHERE i.codigo = 'fao_indice_precios_alimentos'
          AND o.periodo_fecha >= (SELECT max(o2.periodo_fecha) - 60 FROM observacion o2 JOIN serie s2 ON s2.id = o2.serie_id WHERE s2.indicador_id = i.id)
        ORDER BY 1 DESC, 2""",
    "Últimas cargas registradas": """
        SELECT i.codigo, c.estado, c.filas_leidas, left(c.mensaje, 150), c.iniciado_en
        FROM carga_log c JOIN indicador i ON i.id = c.indicador_id
        WHERE i.categoria = 'precios_agrarios' ORDER BY c.id DESC LIMIT 12""",
}


def main() -> int:
    cfg = Config.load()
    conn = db.connect(cfg.database_url)
    with conn.cursor() as cur:
        for titulo, sql in CONSULTAS.items():
            cur.execute(sql)
            print(f"\n== {titulo} ==")
            for fila in cur.fetchall():
                print("  ", " | ".join(str(x) for x in fila))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
