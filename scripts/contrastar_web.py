"""Contrasta las cifras publicadas en la web (web/datos/panel.json) con las
fuentes originales, consultadas de nuevo y de forma independiente de la base
de datos (paso de verificación de docs/web-extremaduraendatos.md).

- INE: cada serie mostrada se localiza en la base de datos por su nombre (la
  misma selección que hace exportar_web.py), se toma su código de serie del
  INE y se vuelve a pedir a la API Tempus3 (DATOS_SERIE). Se imprime también
  el nombre oficial de la serie para comprobar que es la que se quiere.
- Eurostat, Comisión Europea (Agri-food) y FAO: consultas directas a sus APIs
  con los filtros escritos a mano, sin pasar por el código de ingesta.

No modifica nada. Salida: _ejecucion_claude/contraste_web.txt
Uso: .venv\\Scripts\\python.exe scripts\\contrastar_web.py
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import time
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

import exportar_web as EW  # noqa: E402
from extremadura_datos import db  # noqa: E402
from extremadura_datos.config import Config  # noqa: E402

P = json.loads((RAIZ / "web" / "datos" / "panel.json").read_text(encoding="utf-8"))
S = requests.Session()
S.headers["User-Agent"] = "extremadura-en-datos/contraste (uso personal)"
LINEAS: list[str] = []
FALLOS = 0


def out(t=""):
    print(t)
    LINEAS.append(t)


def comparar(concepto, panel, fuente, tol=0.051, nota=""):
    global FALLOS
    if panel is None or fuente is None:
        estado = "SIN DATO"
        FALLOS += 1
    else:
        estado = "OK" if abs(float(panel) - float(fuente)) <= tol else "DIFERENCIA"
        if estado != "OK":
            FALLOS += 1
    out(f"[{estado:10}] {concepto:55} panel={panel!s:>14}  fuente={fuente!s:>14}  {nota}")


# ------------------------------------------------------------------ INE
def ine_serie(cod, n=6):
    time.sleep(0.4)
    r = S.get(f"https://servicios.ine.es/wstempus/js/ES/DATOS_SERIE/{cod}", params={"nult": n, "tip": "A"}, timeout=60)
    r.raise_for_status()
    j = r.json()
    datos = [(d["Anyo"], d.get("FK_Periodo"), d["Valor"]) for d in j.get("Data", []) if d.get("Valor") is not None]
    return j.get("Nombre"), datos


def codigo(conn, indicador, tokens, nuts):
    A = EW.Almacen(conn)
    cand = A.elegir(indicador, tokens, nuts)
    A.obs([c["id"] for c in cand])
    mejor = max(cand, key=lambda c: len(A._obs[c["id"]]))
    with conn.cursor() as cur:
        cur.execute("SELECT codigo_origen FROM serie WHERE id=%s", (mejor["id"],))
        return cur.fetchone()[0]


def bloque_ine(conn):
    out("=== INE (API Tempus3, serie a serie) ===")
    kp = {k["titulo"]: k for k in P["kpis"]}
    tiles = {t["id"]: t for t in P["pulso"]["tiles"]}
    casos = [
        ("Paro EPA Extremadura (KPI)", "ine_epa_ccaa", ["Tasa de paro de la población", "Ambos sexos", "Total"], "ES43", kp["Tasa de paro (EPA)"]["valor"], 0.006),
        ("Paro EPA España (gráfico)", "ine_epa_ccaa", ["Tasa de paro de la población", "Ambos sexos", "Total"], "ES", P["pulso"]["paro"]["serie"][-1]["esp"], 0.006),
        ("Población Extremadura 1 jul (ECP)", "ine_ecp_poblacion_ccaa", ["Total", "Todas las edades"], "ES43", kp["Población"]["valor"], 0.5),
        ("Pernoctaciones hoteleras", "ine_turismo_viajeros_pernoctaciones_ccaa", ["Pernoctaciones", "Total"], "ES43", tiles["pernoctaciones"]["valor"], 0.5),
        ("Compraventa de viviendas", "ine_compraventa_vivienda_ccaa_provincia", ["General", "Compraventa"], "ES43", tiles["compraventa"]["valor"], 0.5),
        ("Sociedades mercantiles creadas", "ine_soc_mercantiles_constituidas_ccaa", ["Sociedades Constituídas", "Mercantiles", "Número de Sociedades"], "ES43", tiles["sociedades"]["valor"], 0.5),
    ]
    for concepto, ind, tk, nuts, valor_panel, tol in casos:
        try:
            cod = codigo(conn, ind, tk, nuts)
            nombre, datos = ine_serie(cod)
            ult = datos[-1] if datos else (None, None, None)
            comparar(concepto, valor_panel, ult[2], tol, f"{cod} · {ult[0]} P{ult[1]} · «{nombre}»")
        except Exception as exc:  # noqa: BLE001
            comparar(concepto, valor_panel, None, nota=f"error {exc}")
    # hipotecas: suma de provincias frente al total de la comunidad publicado por el INE
    try:
        cb = codigo(conn, "ine_hipotecas_provincia", ["Total", "Número de hipotecas"], "ES431")
        cc = codigo(conn, "ine_hipotecas_provincia", ["Total", "Número de hipotecas"], "ES432")
        nb, db_ = ine_serie(cb)
        nc, dc = ine_serie(cc)
        comparar("Hipotecas (Badajoz + Cáceres)", tiles["hipotecas"]["valor"], db_[-1][2] + dc[-1][2], 0.5, f"«{nb}» + «{nc}»")
    except Exception as exc:  # noqa: BLE001
        comparar("Hipotecas", tiles["hipotecas"]["valor"], None, nota=f"error {exc}")
    # ranking de comunidades: todas
    for fila in P["pulso"]["ranking"]["datos"]:
        try:
            cod = codigo(conn, "ine_epa_ccaa", ["Tasa de paro de la población", "Ambos sexos", "Total"], fila["id"])
            nombre, datos = ine_serie(cod, 2)
            comparar(f"Ranking paro · {fila['nombre']}", fila["valor"], datos[-1][2], 0.006, f"«{nombre}»")
        except Exception as exc:  # noqa: BLE001
            comparar(f"Ranking paro · {fila['nombre']}", fila["valor"], None, nota=f"error {exc}")


# ------------------------------------------------------------------ Eurostat
def eurostat(dataset, **filtros):
    time.sleep(0.5)
    params = [("format", "JSON"), ("lang", "EN")]
    for k, v in filtros.items():
        for x in (v if isinstance(v, (list, tuple)) else [v]):
            params.append((k, x))
    r = S.get(f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}", params=params, timeout=120)
    r.raise_for_status()
    j = r.json()
    ids, tam = j["id"], j["size"]
    idx = {d: j["dimension"][d]["category"]["index"] for d in ids}
    res = {}
    for pos, val in j["value"].items():
        pos = int(pos)
        coord = {}
        for d, n in zip(reversed(ids), reversed(tam)):
            pos, i = divmod(pos, n)
            coord[d] = next(k for k, v in idx[d].items() if v == i)
        res[(coord["geo"], coord["time"])] = val
    return res


def bloque_eurostat():
    out("\n=== Eurostat (API de difusión, filtros escritos a mano) ===")
    cp = P["europa"]["capas"]
    try:
        a = cp["pib"]["anyo"]
        abs_ = eurostat("nama_10r_2gdp", geo=["ES43", "EU27_2020"], unit="PPS_EU27_2020_HAB", time=str(a))
        ind = eurostat("nama_10r_2gdp", geo=["ES43"], unit="PPS_HAB_EU27_2020", time=str(a))
        calc = abs_[("ES43", str(a))] / abs_[("EU27_2020", str(a))] * 100
        comparar(f"PIB pc Extremadura UE=100 ({a}) vs índice oficial", cp["pib"]["ext"], ind.get(("ES43", str(a))), 1.0, f"cálculo con PPS absolutos = {calc:.1f}")
        comparar(f"PIB pc Extremadura PPS/hab ({a})", round(cp["pib"]["ext"] * abs_[("EU27_2020", str(a))] / 100, -2), abs_[("ES43", str(a))], 400, "comprobación inversa (redondeo del índice)")
    except Exception as exc:  # noqa: BLE001
        comparar("PIB pc", cp["pib"]["ext"], None, nota=f"error {exc}")
    for clave, ds, filtros, nombre in [
        ("paro", "lfst_r_lfu3rt", dict(sex="T", age="Y15-74", isced11="TOTAL", unit="PC"), "Tasa de paro 15-74"),
        ("empleo", "lfst_r_lfe2emprt", dict(sex="T", age="Y20-64", unit="PC"), "Tasa de empleo 20-64"),
        ("id", "rd_e_gerdreg", dict(sectperf="TOTAL", unit="PC_GDP"), "I+D % PIB"),
    ]:
        c = cp[clave]
        try:
            d = eurostat(ds, geo=["ES43", "EU27_2020", "DE11", "PL91"], time=str(c["anyo"]), **filtros)
            comparar(f"{nombre} Extremadura ({c['anyo']})", c["ext"], d.get(("ES43", str(c["anyo"]))), 0.051)
            if c["ue"] is not None:
                comparar(f"{nombre} UE-27 ({c['anyo']})", c["ue"], d.get(("EU27_2020", str(c["anyo"]))), 0.051)
            for reg in ("DE11", "PL91"):
                comparar(f"{nombre} {reg} (mapa)", c["valores"].get(reg), d.get((reg, str(c["anyo"]))), 0.051)
        except Exception as exc:  # noqa: BLE001
            comparar(nombre, c["ext"], None, nota=f"error {exc}")
    if "renta" in cp:
        c = cp["renta"]
        try:
            d = eurostat("nama_10r_2hhinc", geo=["ES43", "EU27_2020"], unit="PPS_EU27_2020_HAB", na_item="B6N", direct="BAL", time=str(c["anyo"]))
            v = d[("ES43", str(c["anyo"]))] / d[("EU27_2020", str(c["anyo"]))] * 100
            comparar(f"Renta disponible UE=100 ({c['anyo']})", c["ext"], round(v), 0.51)
        except Exception as exc:  # noqa: BLE001
            comparar("Renta disponible", c["ext"], None, nota=f"error {exc}")
    c = cp["agro"]
    try:
        a_ = eurostat("lfst_r_lfe2en2", geo="ES43", sex="T", age="Y15-74", nace_r2="A", time=str(c["anyo"]))
        t_ = eurostat("lfst_r_lfe2en2", geo="ES43", sex="T", age="Y15-74", nace_r2="TOTAL", time=str(c["anyo"]))
        comparar(f"Empleo agrario % ({c['anyo']})", c["ext"], round(a_[("ES43", str(c["anyo"]))] / t_[("ES43", str(c["anyo"]))] * 100, 1), 0.051)
    except Exception as exc:  # noqa: BLE001
        comparar("Empleo agrario", c["ext"], None, nota=f"error {exc}")


# ------------------------------------------------------------------ Agri-food y FAO
def bloque_precios():
    out("\n=== Comisión Europea, Agri-food (API) ===")
    prods = {p["id"]: p for p in P["campo"]["productos"]}
    base = "https://api.tech.ec.europa.eu/agrifood/api"

    def ddmm(iso):
        a, m, d = iso.split("-")
        return f"{d}/{m}/{a}"

    comprobaciones = [
        ("cerdo", "esp", "pigmeat/prices", dict(memberStateCodes="ES", pigClasses="S"), lambda f: f.get("pigClass") == "S"),
        ("cerdo", "ue", "pigmeat/prices", dict(memberStateCodes="EU", pigClasses="S"), lambda f: f.get("pigClass") == "S"),
        ("cordero", "esp", "sheepAndGoat/prices", dict(memberStateCodes="ES"), lambda f: f.get("category") == "Light Lamb"),
        ("aceite", "esp", "oliveOil/prices", dict(memberStateCodes="ES"), lambda f: f.get("product", "").startswith("Virgin olive oil") and "Average" in f.get("market", "")),
    ]
    for pid, linea, ep, params, filtro in comprobaciones:
        p = prods.get(pid)
        if not p or linea not in p["ultimo"]:
            continue
        u = p["ultimo"][linea]
        try:
            time.sleep(1.5)
            r = S.get(f"{base}/{ep}", params={**params, "beginDate": ddmm(u["fecha"]), "endDate": ddmm(u["fecha"])}, timeout=60)
            filas = [f for f in (r.json() if r.status_code == 200 else []) if filtro(f)]
            v = EW_precio(filas[0]["price"]) if filas else None
            comparar(f"{p['titulo']} · {linea} · semana {u['fecha']}", u["valor"], v, 0.006, f"{len(filas)} fila(s)")
        except Exception as exc:  # noqa: BLE001
            comparar(f"{p['titulo']} · {linea}", u["valor"], None, nota=f"error {exc}")

    out("\n=== FAO (CSV oficial) ===")
    try:
        from extremadura_datos import fao

        pag = S.get(fao.PAGINA, timeout=60)
        txt = S.get(fao.url_csv(pag.text), timeout=60).content.decode("utf-8-sig")
        filas = list(csv.reader(io.StringIO(txt)))
        ult = [f for f in filas if f and re.fullmatch(r"\d{4}-\d{2}", f[0].strip())][-1]
        panel = P["campo"]["fao"]["Índice general"][-1]
        comparar(f"Índice FAO general {ult[0]}", panel[1], float(ult[1]), 0.051, f"panel fecha {panel[0]}")
    except Exception as exc:  # noqa: BLE001
        comparar("Índice FAO", None, None, nota=f"error {exc}")


def EW_precio(txt):
    from extremadura_datos.precios_util import precio_desde_texto

    return precio_desde_texto(txt)


def main() -> int:
    cfg = Config.load()
    conn = db.connect(cfg.database_url)
    out(f"Contraste de panel.json generado {P['generado']}")
    try:
        bloque_ine(conn)
    finally:
        conn.close()
    bloque_eurostat()
    bloque_precios()
    out(f"\nRESULTADO: {FALLOS} comprobaciones con diferencia o sin dato")
    (RAIZ / "_ejecucion_claude" / "contraste_web.txt").write_text("\n".join(LINEAS), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
