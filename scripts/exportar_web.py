"""Exporta los datos de la base de datos a JSON para la web pública
extremaduraendatos.com (paso 3 de docs/web-extremaduraendatos.md).

Solo lectura. Genera:
  web/datos/panel.json    — cifras, series y análisis de los tres bloques
  web/datos/nuts2.geojson — contornos NUTS 2 de GISCO (se descarga una vez)

Reglas:
- Solo fuentes con licencia de reutilización clara (INE, Eurostat, Comisión
  Europea, FAO). Las series del Observatorio de la Junta NO se exportan hasta
  tener autorización (docs/web-extremaduraendatos.md §3).
- Una serie de precios se muestra solo si su último dato tiene menos de
  DIAS_FRESCURA días; así no aparecen líneas paradas.
- Los análisis (previsión, gemelas, transmisión) son estadística sencilla y
  reproducible, con su error medido; ver la sección "método" de cada bloque en
  el JSON.

Uso: .venv\\Scripts\\python.exe scripts\\exportar_web.py
"""
from __future__ import annotations

import json
import math
import re
import statistics as st
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from extremadura_datos import db  # noqa: E402
from extremadura_datos.config import Config  # noqa: E402

SALIDA = RAIZ / "web" / "datos"
GEO_URL = "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_20M_2021_4326_LEVL_2.geojson"
UE27 = set("AT BE BG CY CZ DE DK EE EL ES FI FR HR HU IE IT LT LU LV MT NL PL PT RO SE SI SK".split())
EXCLUIR_NUTS = re.compile(r"^(FRY|ES70|PT20|PT30)")
DIAS_FRESCURA = 150
HOY = date.today()


# ---------------------------------------------------------------- utilidades
def partes(nombre: str) -> set[str]:
    return {p.strip().rstrip(".").strip().lower() for p in nombre.split(". ") if p.strip()}


class Almacen:
    """Carga perezosa de series por indicador y de sus observaciones."""

    def __init__(self, conn):
        self.conn = conn
        self._series: dict[str, list[dict]] = {}
        self._obs: dict[int, list[tuple[date, float]]] = {}

    def series(self, indicador: str) -> list[dict]:
        if indicador not in self._series:
            with self.conn.cursor() as cur:
                cur.execute(
                    """SELECT s.id, s.nombre_origen, COALESCE(t.codigo_nuts,''), t.nivel, t.nombre
                       FROM serie s JOIN indicador i ON i.id=s.indicador_id
                       JOIN territorio t ON t.id=s.territorio_id WHERE i.codigo=%s""",
                    (indicador,),
                )
                self._series[indicador] = [
                    {"id": r[0], "nombre": r[1], "nuts": r[2], "nivel": r[3], "territorio": r[4], "partes": partes(r[1])}
                    for r in cur.fetchall()
                ]
        return self._series[indicador]

    def elegir(self, indicador, tokens=(), nuts=None, excluir=()) -> list[dict]:
        tk = {t.lower() for t in tokens}
        ex = {t.lower() for t in excluir}
        res = []
        for s in self.series(indicador):
            if nuts is not None and s["nuts"] != nuts:
                continue
            if tk <= s["partes"] and not (ex & s["partes"]):
                res.append(s)
        return res

    def obs(self, ids: list[int]) -> None:
        falta = [i for i in ids if i not in self._obs]
        if not falta:
            return
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT serie_id, periodo_fecha, valor FROM observacion WHERE serie_id = ANY(%s) AND valor IS NOT NULL AND NOT secreto ORDER BY periodo_fecha",
                (falta,),
            )
            tmp = defaultdict(list)
            for sid, f, v in cur.fetchall():
                tmp[sid].append((f, float(v)))
        for i in falta:
            self._obs[i] = tmp.get(i, [])

    def una(self, indicador, tokens=(), nuts=None, excluir=()) -> list[tuple[date, float]]:
        """Serie con más observaciones entre las que cumplen el filtro."""
        cand = self.elegir(indicador, tokens, nuts, excluir)
        if not cand:
            return []
        self.obs([c["id"] for c in cand])
        return max((self._obs[c["id"]] for c in cand), key=len)

    def por_territorio(self, indicador, tokens=(), excluir=(), filtro_nuts=None) -> dict[str, dict]:
        cand = [c for c in self.elegir(indicador, tokens, None, excluir) if filtro_nuts is None or filtro_nuts(c["nuts"])]
        self.obs([c["id"] for c in cand])
        res: dict[str, dict] = {}
        for c in cand:
            o = self._obs[c["id"]]
            clave = c["nuts"] or c["territorio"]
            if o and (clave not in res or len(o) > len(res[clave]["obs"])):
                res[clave] = {"nombre": c["territorio"], "obs": o, "nivel": c["nivel"]}
        return res


def ultimo(obs):
    return obs[-1] if obs else (None, None)


def valor_en(obs, fecha):
    for f, v in obs:
        if f == fecha:
            return v
    return None


def hace_un_anyo(obs):
    """Valor del mismo periodo un año antes (mensual, trimestral o anual)."""
    if not obs:
        return None
    f, _ = obs[-1]
    try:
        objetivo = f.replace(year=f.year - 1)
    except ValueError:
        objetivo = f - timedelta(days=365)
    exacto = valor_en(obs, objetivo)
    if exacto is not None:
        return exacto
    # semanal: la semana más cercana a 52 semanas antes (±3 días)
    for g, v in reversed(obs):
        if abs((g - (f - timedelta(weeks=52))).days) <= 3:
            return v
    return None


def var_pct(a, b):
    return None if a is None or b in (None, 0) else round((a / b - 1) * 100, 2)


def iso(f: date) -> str:
    return f.isoformat()


def periodo_txt(f: date, tipo: str) -> str:
    meses = "ene feb mar abr may jun jul ago sep oct nov dic".split()
    if tipo == "trimestral":
        return f"{(f.month - 1) // 3 + 1}T {f.year}"
    if tipo == "mensual":
        return f"{meses[f.month - 1]} {f.year}"
    if tipo == "semanal":
        return f"sem. {f.isocalendar()[1]} · {f.strftime('%d/%m/%Y')}"
    return str(f.year)


def fresca(obs, dias=DIAS_FRESCURA) -> bool:
    return bool(obs) and (HOY - obs[-1][0]).days <= dias


def cuantil(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def r(x, d=2):
    return None if x is None else round(x, d)


# ---------------------------------------------------------------- bloque 1
def bloque_pulso(A: Almacen) -> dict:
    paro = A.una("ine_epa_ccaa", ["Tasa de paro de la población", "Ambos sexos", "Total"], "ES43")
    paro_es = A.una("ine_epa_ccaa", ["Tasa de paro de la población", "Ambos sexos", "Total"], "ES")

    def tile(id_, titulo, obs, unidad, tipo, modo="pct", decimales=0, escala=1.0, fuente="INE"):
        if not obs:
            return None
        f, v = obs[-1]
        prev = hace_un_anyo(obs)
        if modo == "pp":
            cambio = None if prev is None else round(v - prev, 2)
        else:
            cambio = var_pct(v, prev)
        spark = [r(x * escala, 3) for _, x in obs[-36:]]
        return {
            "id": id_, "titulo": titulo, "valor": r(v * escala, 3), "unidad": unidad, "decimales": decimales,
            "cambio": cambio, "cambio_tipo": modo, "periodo": periodo_txt(f, tipo), "fecha": iso(f),
            "tipo": tipo, "spark": spark, "fuente": fuente,
        }

    pern = A.una("ine_turismo_viajeros_pernoctaciones_ccaa", ["Pernoctaciones", "Total"], "ES43")
    viaj_ext = A.una("ine_turismo_viajeros_pernoctaciones_ccaa", ["Viajeros", "Residentes en el extranjero"], "ES43")
    compra = A.una("ine_compraventa_vivienda_ccaa_provincia", ["General", "Compraventa"], "ES43")
    socs = A.una("ine_soc_mercantiles_constituidas_ccaa", ["Sociedades Constituídas", "Mercantiles", "Número de Sociedades"], "ES43")
    hip_b = A.una("ine_hipotecas_provincia", ["Total", "Número de hipotecas"], "ES431")
    hip_c = A.una("ine_hipotecas_provincia", ["Total", "Número de hipotecas"], "ES432")
    dc = dict(hip_c)
    hip = [(f, v + dc[f]) for f, v in hip_b if f in dc]
    confianza = A.una("ine_confianza_empresarial_ccaa", ["Índice"], "ES43")

    tiles = [t for t in [
        tile("pernoctaciones", "Pernoctaciones hoteleras", pern, "", "mensual"),
        tile("compraventa", "Compraventa de viviendas", compra, "", "mensual"),
        tile("hipotecas", "Hipotecas sobre viviendas y otras fincas urbanas", hip, "", "mensual"),
        tile("sociedades", "Sociedades mercantiles creadas", socs, "", "mensual"),
    ] if t]

    # --- previsión de la tasa de paro (estacional ingenua + tendencia) ---
    prevision = None
    if len(paro) >= 30:
        ys = [v for _, v in paro]
        fechas = [f for f, _ in paro]

        def pred(hist, h):
            # último valor del mismo trimestre + tendencia media interanual de los últimos 4 trimestres
            tend = st.mean(hist[-k] - hist[-k - 4] for k in range(1, 5))
            base = hist[len(hist) - 4 + ((h - 1) % 4)]
            return base + tend * (1 + (h - 1) // 4)

        errores = defaultdict(list)
        for origen in range(len(ys) - 44, len(ys) - 1):
            if origen < 9:
                continue
            hist = ys[: origen + 1]
            for h in range(1, 5):
                if origen + h < len(ys):
                    errores[h].append(ys[origen + h] - pred(hist, h))
        fut = []
        f = fechas[-1]
        for h in range(1, 5):
            mes = f.month + 3 * h
            fh = date(f.year + (mes - 1) // 12, (mes - 1) % 12 + 1, 1)
            c = pred(ys, h)
            e = errores[h]
            fut.append({
                "fecha": iso(fh), "periodo": periodo_txt(fh, "trimestral"), "central": r(c),
                "lo": r(c + cuantil(e, 0.10)), "hi": r(c + cuantil(e, 0.90)),
            })
        prevision = {
            "puntos": fut,
            "error_medio_1t": r(st.mean(abs(x) for x in errores[1]), 2),
            "n_pruebas": len(errores[1]),
            "metodo": "Valor del mismo trimestre del año anterior más la variación interanual media de los últimos cuatro trimestres. Intervalo del 80 % a partir de los errores de ese mismo método en los últimos 11 años.",
        }

    # --- ranking CCAA ---
    epa = A.por_territorio("ine_epa_ccaa", ["Tasa de paro de la población", "Ambos sexos", "Total"])
    ranking = []
    fecha_rank = paro[-1][0] if paro else None
    for clave, d in epa.items():
        v = valor_en(d["obs"], fecha_rank)
        if v is None:
            continue
        nombre = "España" if clave == "ES" else d["nombre"]
        ranking.append({"id": clave, "nombre": nombre, "valor": r(v)})
    ranking.sort(key=lambda x: -x["valor"])

    # --- movimientos a vigilar: variación interanual del último dato frente a los 5 años anteriores ---
    candidatos = [
        ("Pernoctaciones hoteleras", pern), ("Viajeros extranjeros en hoteles", viaj_ext),
        ("Compraventa de viviendas", compra), ("Hipotecas sobre fincas urbanas", hip),
        ("Sociedades mercantiles creadas", socs), ("Tasa de paro", paro),
    ]
    alertas = []
    for titulo, obs in candidatos:
        if len(obs) < 30:
            continue
        idx = {f: v for f, v in obs}
        yoy = []
        for f, v in obs:
            try:
                p = idx.get(f.replace(year=f.year - 1))
            except ValueError:
                p = None
            if p:
                yoy.append((f, (v / p - 1) * 100 if titulo != "Tasa de paro" else v - p))
        if len(yoy) < 20:
            continue
        ult_f, ult = yoy[-1]
        ventana = [x for f, x in yoy[:-1] if f >= ult_f.replace(year=ult_f.year - 5)]
        if len(ventana) < 12:
            continue
        pct = sum(1 for x in ventana if x < ult) / len(ventana)
        estado = "atencion" if pct >= 0.95 or pct <= 0.05 else "normal"
        es_paro = titulo == "Tasa de paro"
        cifra = f"{abs(ult):.1f}".replace(".", ",")
        if es_paro:
            cambio_txt = f"{'sube' if ult > 0 else 'baja'} {cifra} puntos"
        else:
            cambio_txt = f"{'sube' if ult > 0 else 'cae'} un {cifra} %"
        sentido = "subida" if ult > 0 else "caída"
        if estado == "atencion":
            texto = f"{cambio_txt.capitalize()} respecto al año anterior: un cambio {'mayor' if pct >= 0.95 else 'menor'} que en el {round(max(pct, 1 - pct) * 100)} % de los periodos de los últimos cinco años."
        else:
            texto = f"{cambio_txt.capitalize()} respecto al año anterior, un cambio normal comparado con los últimos cinco años."
        alertas.append({"titulo": titulo, "estado": estado, "texto": texto, "periodo": periodo_txt(ult_f, "trimestral" if titulo == "Tasa de paro" else "mensual"), "extremo": abs(pct - 0.5), "sentido": sentido})
    alertas.sort(key=lambda a: -a["extremo"])

    serie_paro = [{"fecha": iso(f), "periodo": periodo_txt(f, "trimestral"), "ext": r(v), "esp": r(valor_en(paro_es, f))} for f, v in paro if f.year >= 2008]

    return {
        "tiles": tiles,
        "paro": {"serie": serie_paro, "prevision": prevision},
        "ranking": {"periodo": periodo_txt(fecha_rank, "trimestral") if fecha_rank else None, "datos": ranking},
        "alertas": alertas[:4],
        "confianza": tile("confianza", "Confianza empresarial", confianza, "índice", "trimestral", decimales=1),
        "_paro_obs": paro, "_pern": pern, "_compra": compra,
    }


# ---------------------------------------------------------------- bloque 2
def es_nuts2(c: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{2}[0-9A-Z]{2}", c or "")) and c[:2] in UE27 and not EXCLUIR_NUTS.match(c)


def ultimo_anyo_comun(datos: dict[str, dict], minimo=180):
    cuenta = defaultdict(int)
    for d in datos.values():
        for f, _ in d["obs"]:
            cuenta[f.year] += 1
    buenos = [a for a, n in cuenta.items() if n >= minimo]
    return max(buenos) if buenos else None


def en_anyo(obs, anyo):
    for f, v in obs:
        if f.year == anyo:
            return v
    return None


def bloque_europa(A: Almacen) -> dict:
    PPS = "Purchasing power standard (PPS, EU27 from 2020), per inhabitant"
    pib = A.por_territorio("eurostat_pib_nuts2", [PPS], filtro_nuts=es_nuts2)
    pib_ue = A.una("eurostat_pib_nuts2", [PPS], "EU27_2020")
    paro = A.por_territorio("eurostat_paro_nuts2", ["All ISCED 2011 levels", "Total", "From 15 to 74 years"], filtro_nuts=es_nuts2)
    paro_ue = A.una("eurostat_paro_nuts2", ["All ISCED 2011 levels", "Total", "From 15 to 74 years"], "EU27_2020")
    empleo = A.por_territorio("eurostat_empleo_nuts2", ["Total", "From 20 to 64 years"], filtro_nuts=es_nuts2)
    empleo_ue = A.una("eurostat_empleo_nuts2", ["Total", "From 20 to 64 years"], "EU27_2020")
    renta = A.por_territorio("eurostat_renta_hogares_nuts2", [PPS, "Disposable income, net"], filtro_nuts=es_nuts2)
    renta_ue = A.una("eurostat_renta_hogares_nuts2", [PPS, "Disposable income, net"], "EU27_2020")
    agr = A.por_territorio("eurostat_ocupados_ramas_nuts2", ["Agriculture, forestry and fishing", "From 15 to 74 years", "Total"], filtro_nuts=es_nuts2)
    tot = A.por_territorio("eurostat_ocupados_ramas_nuts2", ["Total - all NACE activities", "From 15 to 74 years", "Total"], filtro_nuts=es_nuts2)
    idd = A.por_territorio("eurostat_id_nuts2", ["All sectors", "Percentage of gross domestic product (GDP)"], filtro_nuts=es_nuts2)
    pob = A.por_territorio("eurostat_poblacion_nuts2", ["Number", "Total"], filtro_nuts=es_nuts2)

    nombres = {}
    for fuente in (pib, paro, empleo, pob):
        for k, d in fuente.items():
            nombres.setdefault(k, d["nombre"])

    def capa(datos, titulo, unidad, decimales, anyo=None, transform=None, ref_ue=None, descripcion=""):
        anyo = anyo or ultimo_anyo_comun(datos)
        valores = {}
        for k, d in datos.items():
            v = en_anyo(d["obs"], anyo)
            if v is not None:
                valores[k] = r(transform(k, v) if transform else v, decimales)
        return {"titulo": titulo, "unidad": unidad, "decimales": decimales, "anyo": anyo, "valores": valores,
                "ue": r(ref_ue, decimales) if ref_ue is not None else None, "descripcion": descripcion}

    anyo_pib = ultimo_anyo_comun(pib)
    ue_pib = en_anyo(pib_ue, anyo_pib)
    capas = {
        "pib": capa(pib, "PIB por habitante", "UE = 100", 0, anyo_pib, lambda k, v: v / ue_pib * 100, 100,
                    "Producto interior bruto por habitante en paridad de poder de compra, en relación con la media de la UE."),
        "paro": capa(paro, "Tasa de paro", "%", 1, ref_ue=en_anyo(paro_ue, ultimo_anyo_comun(paro)),
                     descripcion="Personas paradas sobre la población activa de 15 a 74 años."),
        "empleo": capa(empleo, "Tasa de empleo", "%", 1, ref_ue=en_anyo(empleo_ue, ultimo_anyo_comun(empleo)),
                       descripcion="Personas ocupadas sobre la población de 20 a 64 años."),
    }
    anyo_renta = ultimo_anyo_comun(renta)
    ue_renta = en_anyo(renta_ue, anyo_renta)
    if ue_renta:
        capas["renta"] = capa(renta, "Renta disponible de los hogares", "UE = 100", 0, anyo_renta, lambda k, v: v / ue_renta * 100, 100,
                              "Renta neta disponible por habitante en paridad de poder de compra, en relación con la media de la UE.")
    anyo_agr = ultimo_anyo_comun(agr)
    agro_vals = {}
    for k, d in agr.items():
        a, t = en_anyo(d["obs"], anyo_agr), en_anyo(tot.get(k, {}).get("obs", []), anyo_agr)
        if a is not None and t:
            agro_vals[k] = r(a / t * 100, 1)
    capas["agro"] = {"titulo": "Empleo en agricultura", "unidad": "% del empleo", "decimales": 1, "anyo": anyo_agr, "valores": agro_vals, "ue": None,
                     "descripcion": "Personas ocupadas en agricultura, ganadería, silvicultura y pesca sobre el total de ocupados."}
    capas["id"] = capa(idd, "Gasto en I+D", "% del PIB", 2, ultimo_anyo_comun(idd, 150),
                       descripcion="Gasto interno en investigación y desarrollo de todos los sectores sobre el PIB.")

    for c in capas.values():
        vals = sorted(c["valores"].items(), key=lambda kv: -kv[1])
        c["puesto_ext"] = next((i + 1 for i, (k, _) in enumerate(vals) if k == "ES43"), None)
        c["n"] = len(vals)
        c["ext"] = c["valores"].get("ES43")

    # --- regiones gemelas: distancia euclídea sobre variables tipificadas ---
    anyo_pob = ultimo_anyo_comun(pob)
    crec_pob = {}
    for k, d in pob.items():
        a, b = en_anyo(d["obs"], anyo_pob), en_anyo(d["obs"], anyo_pob - 10)
        if a and b:
            crec_pob[k] = (a / b - 1) * 100
    variables = {
        "PIB por habitante (UE = 100)": capas["pib"]["valores"],
        "Tasa de paro": capas["paro"]["valores"],
        "Tasa de empleo": capas["empleo"]["valores"],
        "Empleo en agricultura": capas["agro"]["valores"],
        "Gasto en I+D": capas["id"]["valores"],
        "Crecimiento de la población en 10 años": crec_pob,
    }
    if "renta" in capas:
        variables["Renta disponible (UE = 100)"] = capas["renta"]["valores"]
    medias = {n: (st.mean(v.values()), st.pstdev(v.values()) or 1) for n, v in variables.items()}
    regiones = set().union(*[set(v) for v in variables.values()])
    z = {}
    for k in regiones:
        falt = [n for n in variables if k not in variables[n]]
        if len(falt) > 1:
            continue
        z[k] = {n: ((variables[n][k] - medias[n][0]) / medias[n][1]) if k in variables[n] else 0.0 for n in variables}
    gemelas = []
    if "ES43" in z:
        base = z["ES43"]
        dist = sorted(((math.sqrt(sum((z[k][n] - base[n]) ** 2 for n in variables)), k) for k in z if k != "ES43"))
        mediana = st.median(d for d, _ in dist)
        for d, k in dist[:6]:
            # 100 = perfil idéntico; 0 = tan distinta como la región mediana de la UE
            gemelas.append({"id": k, "nombre": nombres.get(k, k), "pais": k[:2], "distancia": r(d, 2),
                            "similitud": max(0, round((1 - d / mediana) * 100))})
        perfil = {n: {"ext": r(variables[n].get("ES43"), 1)} for n in variables}
    else:
        perfil = {}

    # --- convergencia: índice PIB pc (UE=100) año base frente a variación media anual del índice ---
    anyo0 = 2012
    ue0 = en_anyo(pib_ue, anyo0)
    puntos = []
    if ue0 and ue_pib:
        for k, d in pib.items():
            v0, v1 = en_anyo(d["obs"], anyo0), en_anyo(d["obs"], anyo_pib)
            if v0 and v1:
                i0, i1 = v0 / ue0 * 100, v1 / ue_pib * 100
                puntos.append([k, nombres.get(k, k), r(i0, 1), r((i1 - i0) / (anyo_pib - anyo0), 2)])

    serie_pib_ext = []
    ext_obs = pib.get("ES43", {}).get("obs", [])
    es_obs = A.una("eurostat_pib_nuts2", [PPS], "ES")
    for f, v in ext_obs:
        u = en_anyo(pib_ue, f.year)
        e = en_anyo(es_obs, f.year)
        if u:
            serie_pib_ext.append({"anyo": f.year, "ext": r(v / u * 100, 1), "esp": r(e / u * 100, 1) if e else None})

    return {"capas": capas, "nombres": nombres, "gemelas": gemelas, "variables_gemelas": list(variables), "perfil": perfil,
            "convergencia": {"anyo0": anyo0, "anyo1": anyo_pib, "puntos": puntos},
            "pib_historico": serie_pib_ext}


# ---------------------------------------------------------------- bloque 3
PRODUCTOS = [
    {"id": "cerdo", "titulo": "Cerdo de cebo (clase S)", "unidad": "€/100 kg canal", "ind": "agrifood_porcino",
     "lineas": [("esp", ["S"], "ES"), ("ue", ["S"], "EU27_2020")]},
    {"id": "lechon", "titulo": "Lechón", "unidad": "€/cabeza", "ind": "agrifood_porcino",
     "lineas": [("esp", ["Piglet"], "ES"), ("ue", ["Piglet"], "EU27_2020")]},
    {"id": "cordero", "titulo": "Cordero ligero", "unidad": "€/100 kg canal", "ind": "agrifood_ovino",
     "lineas": [("esp", ["Light Lamb"], "ES"), ("ue", ["Light Lamb"], "EU27_2020")]},
    {"id": "aceite", "titulo": "Aceite de oliva virgen", "unidad": "€/100 kg", "ind": "agrifood_aceite",
     "lineas": [("bad", ["Virgin olive oil (up to 2%)", "Badajoz (ES431)"], "ES431"), ("esp", ["Virgin olive oil (up to 2%)", "Average national price"], "ES")]},
    {"id": "aove", "titulo": "Aceite de oliva virgen extra", "unidad": "€/100 kg", "ind": "agrifood_aceite",
     "lineas": [("esp", ["Extra virgin olive oil (up to 0.8%)", "Average national price"], "ES")]},
    {"id": "leche", "titulo": "Leche cruda de vaca", "unidad": "€/100 kg", "ind": "agrifood_leche",
     "lineas": [("esp", ["Raw milk"], "ES"), ("ue", ["Raw milk"], "EU27_2020")]},
    {"id": "vacuno", "titulo": "Añojo (macho joven R3)", "unidad": "€/100 kg canal", "ind": "agrifood_vacuno",
     "lineas": [("esp", ["Young bulls", "AR3"], "ES"), ("ue", ["Young bulls", "AR3"], "EU27_2020")]},
]


def semanal_log_cambios(obs):
    d = dict(obs)
    out = {}
    for f, v in obs:
        p = d.get(f - timedelta(weeks=1))
        if p and v > 0 and p > 0:
            out[f] = math.log(v / p)
    return out


def corr(xs, ys):
    if len(xs) < 10:
        return None
    mx, my = st.mean(xs), st.mean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return None if sx == 0 or sy == 0 else sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def bloque_campo(A: Almacen) -> dict:
    desde = date(2015, 1, 1)
    productos = []
    for p in PRODUCTOS:
        lineas = {}
        for clave, tokens, nuts in p["lineas"]:
            o = A.una(p["ind"], tokens, nuts)
            if fresca(o):
                lineas[clave] = [[iso(f), r(v)] for f, v in o if f >= desde]
        if lineas:
            ult = {k: {"fecha": v[-1][0], "valor": v[-1][1]} for k, v in lineas.items()}
            productos.append({"id": p["id"], "titulo": p["titulo"], "unidad": p["unidad"], "lineas": lineas, "ultimo": ult})

    # --- transmisión UE -> España en el porcino (clase S), últimos 5 años ---
    es = A.una("agrifood_porcino", ["S"], "ES")
    ue = A.una("agrifood_porcino", ["S"], "EU27_2020")
    corte = HOY - timedelta(days=365 * 5)
    ces, cue = semanal_log_cambios([x for x in es if x[0] >= corte]), semanal_log_cambios([x for x in ue if x[0] >= corte])
    lags = []
    for lag in range(0, 9):
        pares = [(cue[f], ces[f + timedelta(weeks=lag)]) for f in cue if f + timedelta(weeks=lag) in ces]
        c = corr([a for a, _ in pares], [b for _, b in pares])
        lags.append({"semanas": lag, "corr": r(c, 3), "n": len(pares), "banda": r(1.96 / math.sqrt(len(pares)), 3) if pares else None})

    # --- asimetría: cambio a 4 semanas en España frente al de la UE, según el signo ---
    d_es, d_ue = dict(es), dict(ue)
    sube, baja = [], []
    for f, v in ue:
        if f < corte:
            continue
        f4 = f - timedelta(weeks=4)
        if f4 in d_ue and f in d_es and f4 in d_es and d_ue[f4] and d_es[f4]:
            x = math.log(v / d_ue[f4])
            y = math.log(d_es[f] / d_es[f4])
            (sube if x > 0 else baja).append((x, y))

    def beta(pares):
        sxx = sum(x * x for x, _ in pares)
        return None if sxx == 0 else sum(x * y for x, y in pares) / sxx

    asimetria = {"sube": r(beta(sube), 2) if len(sube) > 20 else None, "baja": r(beta(baja), 2) if len(baja) > 20 else None,
                 "n_sube": len(sube), "n_baja": len(baja)}

    # --- cadena de costes: variación interanual del último dato ---
    def eslabon(titulo, obs, unidad, decimales=0):
        if obs and isinstance(obs[0], list):  # varias candidatas: la primera fresca con dato de hace un año
            buenas = [o for o in obs if fresca(o, 200) and hace_un_anyo(o) is not None]
            obs = buenas[0] if buenas else next((o for o in obs if o), [])
        if not fresca(obs, 200):
            return None
        f, v = obs[-1]
        return {"titulo": titulo, "valor": r(v, decimales), "unidad": unidad, "cambio": var_pct(v, hace_un_anyo(obs)), "fecha": iso(f)}

    cadena = [e for e in [
        eslabon("Fertilizante nitrogenado (UE)", A.una("agrifood_fertilizantes", ["N (Nitrogen)"], "EU27_2020"), "€/t"),
        eslabon("Cebada pienso (UE)", [A.una("agrifood_cereales", ["Feed barley", "National Average", "National Average - Not Specified"], "EU27_2020"), A.una("agrifood_cereales", ["Feed barley", "National Average", "Deliver to first customer - silo or processing plant - on truck or other transport means"], "EU27_2020")], "€/t"),
        eslabon("Maíz pienso (UE)", [A.una("agrifood_cereales", ["Feed maize", "National Average", "National Average - Not Specified"], "EU27_2020"), A.una("agrifood_cereales", ["Feed maize", "National Average", "Deliver to first customer - silo or processing plant - on truck or other transport means"], "EU27_2020")], "€/t"),
        eslabon("Índice FAO de alimentos", A.una("fao_indice_precios_alimentos", ["Índice general"], "WORLD"), "2014-2016 = 100", 1),
        eslabon("Cerdo de cebo (España)", es, "€/100 kg", 2),
    ] if e]

    fao = {}
    for g in ["Índice general", "Carne", "Lácteos", "Cereales", "Aceites vegetales", "Azúcar"]:
        o = A.una("fao_indice_precios_alimentos", [g], "WORLD")
        fao[g] = [[iso(f), r(v, 1)] for f, v in o if f >= date(2015, 1, 1)]

    return {"productos": productos, "transmision": {"producto": "Cerdo de cebo (clase S)", "desfases": lags},
            "asimetria": asimetria, "cadena": cadena, "fao": fao, "_es": es, "_ue": ue}


# ---------------------------------------------------------------- cinta y portada
def construir(conn) -> dict:
    A = Almacen(conn)
    pulso = bloque_pulso(A)
    europa = bloque_europa(A)
    campo = bloque_campo(A)

    pob = A.una("ine_ecp_poblacion_ccaa", ["Total", "Todas las edades"], "ES43")
    pob_h = A.una("ine_ecp_poblacion_ccaa_historico", ["Total", "Todas las edades"], "ES43")
    pobm = dict(pob_h)
    pobm.update(dict(pob))
    pob_all = sorted(pobm.items())

    paro = pulso.pop("_paro_obs")
    pern = pulso.pop("_pern")
    compra = pulso.pop("_compra")
    es, ue = campo.pop("_es"), campo.pop("_ue")

    cinta = []

    def item(bloque, etiqueta, obs, unidad, dec, modo="pct", tipo="mensual"):
        if not obs:
            return
        f, v = obs[-1]
        p = obs[-2][1] if modo == "semanal" and len(obs) > 1 else hace_un_anyo(obs)
        cambio = (None if p is None else round(v - p, 2)) if modo == "pp" else var_pct(v, p)
        cinta.append({"bloque": bloque, "etiqueta": etiqueta, "valor": r(v, dec), "unidad": unidad, "decimales": dec,
                      "cambio": cambio, "cambio_tipo": "pp" if modo == "pp" else "pct",
                      "referencia": "semana anterior" if modo == "semanal" else "interanual",
                      "periodo": periodo_txt(f, tipo)})

    item("pulso", "Paro EPA", paro, "%", 1, "pp", "trimestral")
    item("pulso", "Población", pob_all, "hab.", 0, tipo="trimestral")
    item("pulso", "Pernoctaciones", pern, "", 0)
    item("pulso", "Compraventa viviendas", compra, "", 0)
    for p in campo["productos"]:
        if p["id"] in ("cerdo", "cordero", "aceite", "leche"):
            clave = "bad" if "bad" in p["lineas"] else "esp"
            o = [(date.fromisoformat(f), v) for f, v in p["lineas"][clave]]
            lugar = "Badajoz" if clave == "bad" else "España"
            item("campo", f"{p['titulo']} · {lugar}", o, p["unidad"], 2, "semanal" if p["id"] != "leche" else "pct",
                 "semanal" if p["id"] != "leche" else "mensual")
    item("campo", "Índice FAO de alimentos", [(date.fromisoformat(f), v) for f, v in campo["fao"]["Índice general"]], "", 1)
    cp = europa["capas"]
    for k, et in [("pib", "PIB por habitante"), ("paro", "Paro en Europa")]:
        c = cp[k]
        if c.get("ext") is not None:
            cinta.append({"bloque": "europa", "etiqueta": f"{et} · Extremadura", "valor": c["ext"], "unidad": c["unidad"], "decimales": c["decimales"],
                          "cambio": None, "cambio_tipo": None, "referencia": f"UE {c['ue']}" if c["ue"] is not None else "", "periodo": str(c["anyo"])})

    kpis = []
    if paro:
        f, v = paro[-1]
        p = hace_un_anyo(paro)
        kpis.append({"bloque": "pulso", "titulo": "Tasa de paro (EPA)", "valor": r(v, 2), "decimales": 1, "unidad": "%",
                     "cambio": r(v - p, 2) if p else None, "cambio_tipo": "pp", "referencia": "interanual", "periodo": periodo_txt(f, "trimestral")})
    if pob_all:
        f, v = pob_all[-1]
        kpis.append({"bloque": "pulso", "titulo": "Población", "valor": v, "decimales": 0, "unidad": "hab.",
                     "cambio": var_pct(v, hace_un_anyo(pob_all)), "cambio_tipo": "pct", "referencia": "interanual", "periodo": f"1 {periodo_txt(f, 'mensual')}"})
    if cp["pib"].get("ext") is not None:
        hist = europa["pib_historico"]
        cambio = None
        if len(hist) > 5:
            cambio = r(hist[-1]["ext"] - hist[-6]["ext"], 1)
        kpis.append({"bloque": "europa", "titulo": "PIB por habitante (UE = 100)", "valor": cp["pib"]["ext"], "decimales": 0, "unidad": "",
                     "cambio": cambio, "cambio_tipo": "puntos", "referencia": "en 5 años", "periodo": str(cp["pib"]["anyo"])})
    if es:
        f, v = es[-1]
        kpis.append({"bloque": "campo", "titulo": "Cerdo de cebo, España (€/100 kg)", "valor": r(v, 2), "decimales": 2, "unidad": "",
                     "cambio": var_pct(v, es[-2][1]) if len(es) > 1 else None, "cambio_tipo": "pct", "referencia": "semanal", "periodo": periodo_txt(f, "semanal")})

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM observacion")
        n_obs = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM indicador WHERE activo AND codigo NOT LIKE 'junta%%'")
        n_ind = cur.fetchone()[0]
        cur.execute("""SELECT f.codigo, max(cl.finalizado_en) FROM carga_log cl JOIN indicador i ON i.id=cl.indicador_id
                       JOIN fuente f ON f.id=i.fuente_id WHERE cl.estado='ok' GROUP BY f.codigo""")
        cargas = {c: (m.isoformat() if m else None) for c, m in cur.fetchall()}

    return {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "resumen": {"indicadores": n_ind, "observaciones": n_obs, "cargas": cargas},
        "cinta": cinta, "kpis": kpis, "pulso": pulso, "europa": europa, "campo": campo,
    }


def descargar_geojson() -> None:
    destino = SALIDA / "nuts2.geojson"
    if destino.exists() and destino.stat().st_size > 100_000:
        return
    import requests

    resp = requests.get(GEO_URL, timeout=120)
    resp.raise_for_status()
    geo = resp.json()
    feats = []
    for f in geo["features"]:
        p = f["properties"]
        if p["CNTR_CODE"] in UE27 and not EXCLUIR_NUTS.match(p["NUTS_ID"]):
            f["properties"] = {"id": p["NUTS_ID"], "nombre": p.get("NAME_LATN"), "pais": p["CNTR_CODE"]}

            def red(coords):
                if isinstance(coords[0], (int, float)):
                    return [round(coords[0], 3), round(coords[1], 3)]
                return [red(c) for c in coords]

            f["geometry"]["coordinates"] = red(f["geometry"]["coordinates"])
            f.pop("id", None)
            feats.append(f)
    destino.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")), encoding="utf-8")
    print("nuts2.geojson:", len(feats), "regiones")


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    cfg = Config.load()
    conn = db.connect(cfg.database_url)
    try:
        panel = construir(conn)
    finally:
        conn.close()
    texto = json.dumps(panel, ensure_ascii=False, separators=(",", ":"), default=str)
    (SALIDA / "panel.json").write_text(texto, encoding="utf-8")
    print(f"panel.json: {len(texto) / 1024:.0f} KB")
    try:
        descargar_geojson()
    except Exception as exc:  # el panel sigue sirviendo con los contornos anteriores
        print("AVISO geojson:", exc)
    print("EXPORTACION_WEB_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
