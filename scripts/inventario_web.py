"""Inventario de series disponibles para la web (solo lectura).
Uso: .venv\\Scripts\\python.exe scripts\\inventario_web.py
Salida: _ejecucion_claude/inventario_web.txt
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from extremadura_datos.config import Config
from extremadura_datos import db

SQL = """
SELECT i.codigo, t.nivel, t.nombre, COALESCE(t.codigo_nuts,''), s.nombre_origen,
       s.atributos::text, count(o.id), min(o.periodo_fecha), max(o.periodo_fecha),
       (array_agg(o.valor ORDER BY o.periodo_fecha DESC))[1], max(o.unidad)
FROM serie s
JOIN indicador i ON i.id = s.indicador_id
JOIN territorio t ON t.id = s.territorio_id
JOIN observacion o ON o.serie_id = s.id
WHERE i.activo AND (t.nombre ILIKE 'extremadura%%' OR t.codigo_nuts IN ('ES43','ES431','ES432','ES','EU27_2020','WORLD'))
GROUP BY 1,2,3,4,5,6
ORDER BY 1,3,5
"""

def main() -> int:
    cfg = Config.load()
    conn = db.connect(cfg.database_url)
    out = Path(__file__).resolve().parents[1] / "_ejecucion_claude" / "inventario_web.tsv"
    with conn.cursor() as cur, out.open("w", encoding="utf-8") as f:
        cur.execute(SQL)
        f.write("indicador\tnivel\tterritorio\tnuts\tserie\tatributos\tn\tdesde\thasta\tultimo\tunidad\n")
        n = 0
        for r in cur.fetchall():
            f.write("\t".join("" if x is None else str(x).replace("\t", " ") for x in r) + "\n")
            n += 1
        cur.execute("SELECT i.codigo, count(DISTINCT s.territorio_id), min(o.periodo_fecha), max(o.periodo_fecha) FROM indicador i JOIN serie s ON s.indicador_id=i.id JOIN observacion o ON o.serie_id=s.id WHERE i.codigo LIKE 'eurostat%%' GROUP BY 1")
        f2 = out.with_name("inventario_eurostat.tsv").open("w", encoding="utf-8")
        for r in cur.fetchall():
            f2.write("\t".join(map(str, r)) + "\n")
        f2.close()
    print("filas", n)
    conn.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
