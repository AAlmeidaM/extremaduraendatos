"""Gemelo digital: sistemas vitales, relaciones y rejilla temporal.

Lo usa scripts/exportar_web.py para añadir a web/datos/panel.json la sección
`gemelo` que alimenta la página web/gemelo/. Ver docs/gemelo-digital.md.

Criterios (docs/gemelo-digital.md §3):
- Estado de un sistema = percentil de la variación interanual del indicador
  principal frente a las de los cinco años anteriores (fuera del 5-95 % =
  atención). Se calcula también mes a mes para poder recorrer el pasado.
- Frescura = días desde el último dato, con umbral por periodicidad.
- Solo se dibujan relaciones que se pueden medir o que son contables.
"""
from __future__ import annotations

import math
import statistics as st
from datetime import date, timedelta

# Plazo normal desde que TERMINA el periodo hasta que la fuente lo publica.
DIAS_LIMITE = {"semanal": 21, "mensual": 75, "trimestral": 150, "anual": 1100}
MESES_POR_PERIODO = {"semanal": 0.25, "mensual": 1, "trimestral": 3, "anual": 12}
INICIO = date(2010, 1, 1)


def r(x, d=2):
    return None if x is None else round(x, d)


def _mes(f: date) -> str:
    return f"{f.year:04d}-{f.month:02d}"


def _meses(desde: date, hasta: date) -> list[str]:
    out, a, m = [], desde.year, desde.month
    while (a, m) <= (hasta.year, hasta.month):
        out.append(f"{a:04d}-{m:02d}")
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return out


def mensualizar(obs, rejilla):
    """Último valor conocido en cada mes de la rejilla (sin inventar futuro)."""
    if not obs:
        return {}
    res, i, ultimo = {}, 0, None
    for mes in rejilla:
        while i < len(obs) and _mes(obs[i][0]) <= mes:
            ultimo = obs[i][1]
            i += 1
        if ultimo is not None and _mes(obs[0][0]) <= mes:
            res[mes] = ultimo
    return res


def interanual(serie_mes: dict[str, float], en_puntos: bool) -> dict[str, float]:
    out = {}
    for mes, v in serie_mes.items():
        a, m = mes.split("-")
        prev = serie_mes.get(f"{int(a) - 1:04d}-{m}")
        if prev is None:
            continue
        if en_puntos:
            out[mes] = v - prev
        elif prev:
            out[mes] = (v / prev - 1) * 100
    return out


def percentil(valor, muestra):
    if not muestra:
        return None
    return sum(1 for x in muestra if x < valor) / len(muestra)


def estado_desde_percentil(pct):
    if pct is None:
        return "sin_referencia"
    return "atencion" if pct >= 0.95 or pct <= 0.05 else "normal"


def _texto_estado(pct, yoy, en_puntos, nombre_periodo):
    if pct is None or yoy is None:
        return "Sin suficiente historia para comparar."
    cifra = f"{abs(yoy):.1f}".replace(".", ",")
    unidad = "puntos" if en_puntos else "%"
    verbo = "sube" if yoy > 0 else "baja" if yoy < 0 else "se mantiene"
    cambio = f"{verbo} {cifra} {unidad}" if not en_puntos or True else ""
    if estado_desde_percentil(pct) == "atencion":
        comparativa = "mayor" if pct >= 0.95 else "menor"
        return f"{cambio.capitalize()} respecto al mismo {nombre_periodo} del año anterior: un cambio {comparativa} que en el {round(max(pct, 1 - pct) * 100)} % de los periodos de los cinco años previos."
    return f"{cambio.capitalize()} respecto al mismo {nombre_periodo} del año anterior, dentro de lo habitual de los cinco años previos."



# ---------------------------------------------------------------- criterio de normalidad
# Reglas por periodicidad: años de referencia, mínimo de observaciones para
# dar un estado, y tolerancia al emparejar el mismo periodo del año anterior.
REGLA = {
    "semanal":    {"anyos": 5, "minimo": 104, "tol_dias": 4},
    "mensual":    {"anyos": 5, "minimo": 36, "tol_dias": 0},
    "trimestral": {"anyos": 5, "minimo": 12, "tol_dias": 0},
    "anual":      {"anyos": 10, "minimo": 8, "tol_dias": 0},
}
UMBRAL_PCT = 0.05     # colas del 5 % a cada lado
UMBRAL_Z = 2.0        # distancia robusta mínima para hablar de anomalía

# Variaciones que se comparan contra el confinamiento y el año de cierre: se
# excluyen de la REFERENCIA (no de las series) porque son rebotes mecánicos
# que ensanchan artificialmente lo que se considera "habitual".
PANDEMIA = (date(2020, 3, 1), date(2021, 6, 30))


def _base_pandemica(f: date) -> bool:
    """La comparación de este dato tiene como base un periodo de pandemia."""
    try:
        base = f.replace(year=f.year - 1)
    except ValueError:
        base = f - timedelta(days=365)
    return PANDEMIA[0] <= base <= PANDEMIA[1]


def variacion_interanual(obs, tipo, en_puntos):
    """[(fecha, variación frente al mismo periodo del año anterior)] a la
    frecuencia propia de la serie (sin pasar por la rejilla mensual)."""
    tol = REGLA[tipo]["tol_dias"]
    idx = dict(obs)
    salida = []
    for f, v in obs:
        prev = None
        if tipo == "semanal":
            objetivo = f - timedelta(weeks=52)
            for g, w in obs:
                if abs((g - objetivo).days) <= tol:
                    prev = w
                    break
        else:
            try:
                prev = idx.get(f.replace(year=f.year - 1))
            except ValueError:
                prev = None
        if prev is None:
            continue
        if en_puntos:
            salida.append((f, v - prev))
        elif prev:                      # sin base cero (p. ej. turismo en 2020)
            salida.append((f, (v / prev - 1) * 100))
    return salida


def _percentil_medio(valor, muestra):
    """Percentil con rango medio: reparte los empates en vez de ignorarlos."""
    if not muestra:
        return None
    menores = sum(1 for x in muestra if x < valor)
    iguales = sum(1 for x in muestra if x == valor)
    return (menores + 0.5 * iguales) / len(muestra)


def _cuantil(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def evaluar(yoys, i, tipo):
    """Estado del dato i de la lista de variaciones interanuales.

    Referencia: las variaciones de los `anyos` anteriores (sin contar la
    actual). Posición: percentil dentro de esa referencia. Distancia: z
    robusto = (valor - mediana) / (1,4826 x desviación absoluta mediana).
    Estado: fuera de lo habitual si está en las colas del 5 % Y además se
    aleja al menos 2 desviaciones robustas; al borde si solo se cumple una
    de las dos; sin referencia si la muestra es corta.
    """
    regla = REGLA[tipo]
    f, valor = yoys[i]
    try:
        corte = f.replace(year=f.year - regla["anyos"])
    except ValueError:
        corte = f - timedelta(days=365 * regla["anyos"])
    candidatas = [(g, v) for g, v in yoys[:i] if g >= corte]
    muestra = [v for g, v in candidatas if not _base_pandemica(g)]
    excluidas = len(candidatas) - len(muestra)
    n = len(muestra)
    base = {"yoy": r(valor, 2), "n": n, "excluidas_pandemia": excluidas,
            "ventana_anyos": regla["anyos"], "minimo": regla["minimo"]}
    if n < regla["minimo"]:
        return {**base, "estado": "sin_referencia", "percentil": None, "z": None,
                "mediana": r(st.median(muestra), 2) if muestra else None,
                "p05": None, "p95": None}
    pct = _percentil_medio(valor, muestra)
    mediana = st.median(muestra)
    mad = st.median([abs(x - mediana) for x in muestra]) * 1.4826
    z = (valor - mediana) / mad if mad else None
    extremo_pos = pct <= UMBRAL_PCT or pct >= 1 - UMBRAL_PCT
    extremo_dist = z is not None and abs(z) >= UMBRAL_Z
    estado = "atencion" if (extremo_pos and extremo_dist) else ("limite" if (extremo_pos or extremo_dist) else "normal")
    return {**base, "estado": estado, "percentil": r(pct, 3), "z": r(z, 2) if z is not None else None,
            "mediana": r(mediana, 2), "mad": r(mad, 2),
            "p05": r(_cuantil(muestra, 0.05), 2), "p95": r(_cuantil(muestra, 0.95), 2)}


FRASE_PERIODO = {"semanal": "a la misma semana del año anterior", "mensual": "al mismo mes del año anterior",
                 "trimestral": "al mismo trimestre del año anterior", "anual": "al año anterior"}


def _n(x, d=1):
    """Número en castellano: coma decimal y signo menos tipográfico."""
    if x is None:
        return "–"
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def texto_estado(ev, tipo, en_puntos):
    p = FRASE_PERIODO[tipo]
    if ev.get("yoy") is None:
        return "No hay dato del mismo periodo del año anterior para comparar."
    cifra = _n(abs(ev["yoy"]))
    unidad = "puntos" if en_puntos else "%"
    verbo = "sube" if ev["yoy"] > 0 else "baja" if ev["yoy"] < 0 else "no cambia"
    cambio = f"{verbo} {cifra} {unidad}" if ev["yoy"] else "no cambia"
    if ev["estado"] == "sin_referencia":
        return (f"{cambio.capitalize()} frente {p}. No se valora: hacen falta "
                f"al menos {ev['minimo']} comparaciones previas y solo hay {ev['n']}.")
    comun = (f"{cambio.capitalize()} frente {p}. En los últimos {ev['ventana_anyos']} años "
             f"({ev['n']} comparaciones) lo habitual fue entre {_n(ev['p05'])} y {_n(ev['p95'])} {unidad}, "
             f"con una variación típica de {_n(ev['mediana'])} {unidad}.")
    if ev["estado"] == "atencion":
        return comun + f" Este dato queda en el {round(ev['percentil'] * 100)} % de la distribución y a {_n(abs(ev['z']))} desviaciones de lo típico: fuera de lo habitual."
    if ev["estado"] == "limite":
        return comun + f" Este dato queda en el {round(ev['percentil'] * 100)} % de la distribución: en el borde de lo habitual, pero sin llegar a ser una anomalía clara."
    return comun + f" Este dato queda en el {round(ev['percentil'] * 100)} % de la distribución: dentro de lo habitual."


# ------------------------------------------------------------------ series
def fin_periodo(f: date, tipo: str) -> date:
    """Último día del periodo al que se refiere el dato."""
    if tipo == "semanal":
        return f + timedelta(days=6)
    if tipo == "anual":
        return date(f.year, 12, 31)
    meses = 3 if tipo == "trimestral" else 1
    m = f.month - 1 + meses
    return date(f.year + m // 12, m % 12 + 1, 1) - timedelta(days=1)


def serie_obs(A, sel, suma=(), concat=()):
    obs = A.una(*sel)
    for s in concat:  # histórico + serie viva: la más reciente manda
        previo = dict(A.una(*s))
        previo.update(dict(obs))
        obs = sorted(previo.items())
    for s in suma:
        extra = dict(A.una(*s))
        obs = [(f, v + extra[f]) for f, v in obs if f in extra]
    return obs


def bloque_serie(A, cfg, rejilla, hoy):
    """Ficha de una serie: último dato, estado según el criterio de arriba,
    estado mes a mes (para la línea de tiempo) y frescura."""
    obs = serie_obs(A, cfg["sel"], cfg.get("suma", ()), cfg.get("concat", ()))
    if not obs:
        return None
    tipo = cfg["tipo"]
    en_puntos = cfg.get("en_puntos", False)
    f, v = obs[-1]
    yoys = variacion_interanual(obs, tipo, en_puntos)
    ev = evaluar(yoys, len(yoys) - 1, tipo) if yoys else {
        "yoy": None, "n": 0, "ventana_anyos": REGLA[tipo]["anyos"], "minimo": REGLA[tipo]["minimo"],
        "estado": "sin_referencia", "percentil": None, "z": None, "mediana": None, "p05": None, "p95": None}

    # estado del último dato vigente en cada mes (línea de tiempo)
    codigo = {"normal": "n", "limite": "l", "atencion": "a", "sin_referencia": "s"}
    estado_mensual, j = {}, 0
    for mes in rejilla:
        while j < len(yoys) and _mes(yoys[j][0]) <= mes:
            j += 1
        if j:
            e = evaluar(yoys, j - 1, tipo)
            estado_mensual[mes] = [e["percentil"], codigo[e["estado"]]]

    # nivel del dato actual dentro de su propia historia reciente (contexto)
    try:
        corte_nivel = f.replace(year=f.year - 10)
    except ValueError:
        corte_nivel = f - timedelta(days=3652)
    hist = [x for g, x in obs if g >= corte_nivel]
    nivel = _percentil_medio(v, hist) if len(hist) >= 8 else None

    dias = max(0, (hoy - fin_periodo(f, tipo)).days)
    limite = cfg.get("dias_limite", DIAS_LIMITE[tipo])
    mensual = mensualizar(obs, rejilla)
    return {
        "id": cfg["id"], "titulo": cfg["titulo"], "unidad": cfg.get("unidad", ""),
        "decimales": cfg.get("decimales", 0), "tipo": tipo, "fuente": cfg.get("fuente", "INE"),
        "nota": cfg.get("nota"),
        "valor": r(v, 3), "fecha": f.isoformat(), "dias": dias, "fresca": dias <= limite,
        "en_puntos": en_puntos,
        "yoy": ev["yoy"], "estado": ev["estado"], "percentil": ev["percentil"], "z": ev["z"],
        "referencia": {k: ev.get(k) for k in ("n", "excluidas_pandemia", "ventana_anyos", "minimo", "mediana", "mad", "p05", "p95")},
        "nivel": r(nivel, 3) if nivel is not None else None,
        "texto_estado": texto_estado(ev, tipo, en_puntos),
        "serie": [[g.isoformat(), r(x, 3)] for g, x in obs if g >= INICIO],
        "mensual": {m: r(x, 3) for m, x in mensual.items()},
        "estado_mensual": estado_mensual,
        "yoy_mensual": {m: r(x, 2) for m, x in interanual(mensual, en_puntos).items()},
    }


def comparacion(A, cfg, clave, rejilla):
    sel = cfg.get(clave)
    if not sel:
        return None
    obs = A.una(*sel)
    if cfg.get("concat") and obs:
        hist = A.una(sel[0] + "_historico", *sel[1:]) if not sel[0].endswith("_historico") else []
        if hist:
            previo = dict(hist)
            previo.update(dict(obs))
            obs = sorted(previo.items())
    if not obs:
        return None
    return {"serie": [[g.isoformat(), r(x, 3)] for g, x in obs if g >= INICIO],
            "mensual": {m: r(x, 3) for m, x in mensualizar(obs, rejilla).items()}}


# ------------------------------------------------------------------ definición
PPS = "Purchasing power standard (PPS, EU27 from 2020), per inhabitant"
EPA_TOT = ["Tasa de paro de la población", "Ambos sexos", "Total"]


def definicion():
    """8 sistemas vitales. Cada serie: id, título, selección, tipo, unidad."""
    def S(id_, titulo, sel, tipo, unidad="", dec=0, fuente="INE", en_puntos=False, suma=(), esp=None, ue=None, nota=None, concat=()):
        return {"id": id_, "titulo": titulo, "sel": sel, "tipo": tipo, "unidad": unidad,
                "decimales": dec, "fuente": fuente, "en_puntos": en_puntos, "suma": suma,
                "concat": concat, "esp": esp, "ue": ue, "nota": nota}

    return [
        {"id": "empleo", "nombre": "Empleo", "icono": "empleo",
         "descripcion": "Cuánta gente trabaja y cuánta busca empleo sin encontrarlo.",
         "principal": S("paro", "Tasa de paro", ("ine_epa_ccaa", EPA_TOT, "ES43"), "trimestral", "%", 2,
                        en_puntos=True, esp=("ine_epa_ccaa", EPA_TOT, "ES")),
         "secundarios": [
             S("paro_jov", "Paro menores de 25 años", ("ine_epa_ccaa", ["Tasa de paro de la población", "Ambos sexos", "Menores de 25 años"], "ES43"), "trimestral", "%", 1, en_puntos=True),
             S("paro_muj", "Paro de mujeres", ("ine_epa_ccaa", ["Tasa de paro de la población", "Mujeres", "Total"], "ES43"), "trimestral", "%", 1, en_puntos=True),
             S("empleo_tasa", "Tasa de empleo 20-64 años", ("eurostat_empleo_nuts2", ["Total", "From 20 to 64 years"], "ES43"), "anual", "%", 1, fuente="Eurostat", en_puntos=True,
               esp=("eurostat_empleo_nuts2", ["Total", "From 20 to 64 years"], "ES"), ue=("eurostat_empleo_nuts2", ["Total", "From 20 to 64 years"], "EU27_2020")),
             S("ocup_agr", "Ocupados en agricultura", ("eurostat_ocupados_ramas_nuts2", ["Agriculture, forestry and fishing", "From 15 to 74 years", "Total"], "ES43"), "anual", "mil personas", 1, fuente="Eurostat"),
         ]},
        {"id": "poblacion", "nombre": "Población", "icono": "poblacion",
         "descripcion": "Cuántas personas viven en Extremadura y cómo cambia.",
         "principal": S("pob", "Población residente", ("ine_ecp_poblacion_ccaa", ["Total", "Todas las edades"], "ES43"), "trimestral", "habitantes", 0,
                        concat=[("ine_ecp_poblacion_ccaa_historico", ["Total", "Todas las edades"], "ES43")],
                        esp=("ine_ecp_poblacion_ccaa", ["Total", "Todas las edades", "Total Nacional"], "ES")),
         "secundarios": [
             S("pob_bad", "Badajoz", ("ine_ecp_poblacion_provincia", ["Total", "Todas las edades", "Badajoz"], "ES431"), "trimestral", "habitantes", 0,
               concat=[("ine_ecp_poblacion_provincia_historico", ["Total", "Todas las edades", "Badajoz"], "ES431")]),
             S("pob_cac", "Cáceres", ("ine_ecp_poblacion_provincia", ["Total", "Todas las edades", "Cáceres"], "ES432"), "trimestral", "habitantes", 0,
               concat=[("ine_ecp_poblacion_provincia_historico", ["Total", "Todas las edades", "Cáceres"], "ES432")]),
             S("pob_eu", "Población (Eurostat, 1 de enero)", ("eurostat_poblacion_nuts2", ["Number", "Total"], "ES43"), "anual", "habitantes", 0, fuente="Eurostat"),
         ]},
        {"id": "turismo", "nombre": "Turismo", "icono": "turismo",
         "descripcion": "Visitantes que duermen en hoteles y apartamentos de la región.",
         "principal": S("pernoct", "Pernoctaciones", ("ine_turismo_viajeros_pernoctaciones_ccaa", ["Pernoctaciones", "Total"], "ES43"), "mensual", "", 0,
                        esp=("ine_turismo_viajeros_pernoctaciones_ccaa", ["Pernoctaciones", "Total categorías", "Total"], "ES")),
         "secundarios": [
             S("viajeros", "Viajeros", ("ine_turismo_viajeros_pernoctaciones_ccaa", ["Viajeros", "Total"], "ES43"), "mensual", "", 0),
             S("extranjeros", "Viajeros extranjeros", ("ine_turismo_viajeros_pernoctaciones_ccaa", ["Viajeros", "Residentes en el extranjero"], "ES43"), "mensual", "", 0),
             S("estancia", "Estancia media", ("ine_turismo_estancia_media_ccaa", ["Extremadura", "Estancia media"], "ES43"), "mensual", "días", 2),
         ]},
        {"id": "vivienda", "nombre": "Vivienda", "icono": "vivienda",
         "descripcion": "Compras de vivienda, hipotecas y precios.",
         "principal": S("compraventa", "Compraventa de viviendas", ("ine_compraventa_vivienda_ccaa_provincia", ["General", "Compraventa"], "ES43"), "mensual", "", 0,
                        esp=("ine_compraventa_vivienda_ccaa_provincia", ["General", "Compraventa"], "ES")),
         "secundarios": [
             S("hipotecas", "Hipotecas sobre fincas urbanas", ("ine_hipotecas_provincia", ["Total", "Número de hipotecas"], "ES431"), "mensual", "", 0,
               suma=[("ine_hipotecas_provincia", ["Total", "Número de hipotecas"], "ES432")]),
             S("ipv", "Precio de la vivienda (variación anual)", ("ine_ipv_ccaa", ["General", "Variación anual"], "ES43"), "trimestral", "%", 1, en_puntos=True,
               esp=("ine_ipv_ccaa", ["General", "Variación anual"], "ES")),
             S("rusticas", "Fincas rústicas compradas", ("ine_fincas_rusticas_ccaa_provincia", ["Compraventa", "Fincas Rústicas"], "ES431"), "mensual", "", 0,
               suma=[("ine_fincas_rusticas_ccaa_provincia", ["Compraventa", "Fincas Rústicas"], "ES432")]),
         ]},
        {"id": "empresas", "nombre": "Empresas", "icono": "empresas",
         "descripcion": "Sociedades que se crean y confianza de quien dirige negocios.",
         "principal": S("sociedades", "Sociedades creadas", ("ine_soc_mercantiles_constituidas_ccaa", ["Sociedades Constituídas", "Mercantiles", "Número de Sociedades"], "ES43"), "mensual", "", 0,
                        esp=("ine_soc_mercantiles_constituidas_ccaa", ["Sociedades Constituídas", "Mercantiles", "Número de Sociedades"], "ES")),
         "secundarios": [
             S("capital", "Capital de las sociedades creadas", ("ine_soc_mercantiles_constituidas_ccaa", ["Sociedades Constituídas", "Mercantiles", "Capital"], "ES43"), "mensual", "miles €", 0),
             S("disueltas", "Sociedades disueltas", ("ine_soc_mercantiles_disueltas_provincia", ["Total", "Disueltas", "Número de Sociedades"], "ES431"), "mensual", "", 0,
               suma=[("ine_soc_mercantiles_disueltas_provincia", ["Total", "Disueltas", "Número de Sociedades"], "ES432")]),
             S("confianza", "Confianza empresarial", ("ine_confianza_empresarial_ccaa", ["Índice"], "ES43"), "trimestral", "índice", 1,
               esp=("ine_confianza_empresarial_ccaa", ["Índice"], "ES")),
         ]},
        {"id": "campo", "nombre": "Campo", "icono": "campo",
         "descripcion": "Precios que se pagan por los productos del campo y la ganadería.",
         "principal": S("cerdo", "Cerdo de cebo (clase S)", ("agrifood_porcino", ["S"], "ES"), "semanal", "€/100 kg", 2, fuente="Comisión Europea",
                        ue=("agrifood_porcino", ["S"], "EU27_2020"),
                        nota="Precio del mercado español: el portal europeo no publica precio del cerdo por regiones."),
         "secundarios": [
             S("aceite_bad", "Aceite de oliva virgen, Badajoz", ("agrifood_aceite", ["Virgin olive oil (up to 2%)", "Badajoz (ES431)"], "ES431"), "semanal", "€/100 kg", 2, fuente="Comisión Europea",
               esp=("agrifood_aceite", ["Virgin olive oil (up to 2%)", "Average national price"], "ES")),
             S("cordero", "Cordero ligero", ("agrifood_ovino", ["Light Lamb"], "ES"), "semanal", "€/100 kg", 2, fuente="Comisión Europea",
               ue=("agrifood_ovino", ["Light Lamb"], "EU27_2020")),
             S("leche", "Leche cruda de vaca", ("agrifood_leche", ["Raw milk"], "ES"), "mensual", "€/100 kg", 2, fuente="Comisión Europea",
               ue=("agrifood_leche", ["Raw milk"], "EU27_2020")),
             S("fao", "Índice FAO de alimentos", ("fao_indice_precios_alimentos", ["Índice general"], "WORLD"), "mensual", "2014-2016 = 100", 1, fuente="FAO"),
         ]},
        {"id": "economia", "nombre": "Economía", "icono": "economia",
         "descripcion": "Riqueza que produce la región y renta que llega a los hogares.",
         "principal": S("pib", "PIB por habitante (PPA)", ("eurostat_pib_nuts2", [PPS], "ES43"), "anual", "€ PPA", 0, fuente="Eurostat",
                        esp=("eurostat_pib_nuts2", [PPS], "ES"), ue=("eurostat_pib_nuts2", [PPS], "EU27_2020")),
         "secundarios": [
             S("renta", "Renta disponible por habitante (PPA)", ("eurostat_renta_hogares_nuts2", [PPS, "Disposable income, net"], "ES43"), "anual", "€ PPA", 0, fuente="Eurostat",
               esp=("eurostat_renta_hogares_nuts2", [PPS, "Disposable income, net"], "ES"), ue=("eurostat_renta_hogares_nuts2", [PPS, "Disposable income, net"], "EU27_2020")),
             S("vab", "Valor añadido bruto total", ("eurostat_vab_ramas_nuts2", ["Current prices, million euro", "Total - all NACE activities"], "ES43"), "anual", "M€", 0, fuente="Eurostat"),
             S("vab_agr", "VAB de agricultura y ganadería", ("eurostat_vab_ramas_nuts2", ["Current prices, million euro", "Agriculture, forestry and fishing"], "ES43"), "anual", "M€", 0, fuente="Eurostat"),
             S("vab_ind", "VAB de la industria", ("eurostat_vab_ramas_nuts2", ["Current prices, million euro", "Industry (except construction)"], "ES43"), "anual", "M€", 0, fuente="Eurostat"),
         ]},
        {"id": "conocimiento", "nombre": "Conocimiento", "icono": "conocimiento",
         "descripcion": "Dinero dedicado a investigación y desarrollo.",
         "principal": S("id_pib", "Gasto en I+D", ("eurostat_id_nuts2", ["All sectors", "Percentage of gross domestic product (GDP)"], "ES43"), "anual", "% del PIB", 2, fuente="Eurostat", en_puntos=True,
                        esp=("eurostat_id_nuts2", ["All sectors", "Percentage of gross domestic product (GDP)"], "ES")),
         "secundarios": [
             S("id_hab", "Gasto en I+D por habitante", ("eurostat_id_nuts2", ["All sectors", "Euro per inhabitant"], "ES43"), "anual", "€", 0, fuente="Eurostat",
               esp=("eurostat_id_nuts2", ["All sectors", "Euro per inhabitant"], "ES")),
             S("id_emp", "I+D de las empresas", ("eurostat_id_nuts2", ["Business enterprise sector", "Euro per inhabitant"], "ES43"), "anual", "€/hab.", 0, fuente="Eurostat"),
             S("id_uni", "I+D de las universidades", ("eurostat_id_nuts2", ["Higher education sector", "Euro per inhabitant"], "ES43"), "anual", "€/hab.", 0, fuente="Eurostat"),
         ]},
    ]


# ------------------------------------------------------------------ relaciones
def _corr(xs, ys):
    if len(xs) < 8:
        return None
    mx, my = st.mean(xs), st.mean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return None if sx == 0 or sy == 0 else sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def _desplazar(mes: str, n: int) -> str:
    a, m = int(mes[:4]), int(mes[5:])
    total = a * 12 + (m - 1) + n
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def mejor_desfase(yoy_a: dict, yoy_b: dict, max_meses: int, paso: int = 1):
    """Correlación entre variaciones interanuales de A y de B desplazada."""
    mejor = None
    for lag in range(0, max_meses + 1, paso):
        pares = [(v, yoy_b[_desplazar(m, lag)]) for m, v in yoy_a.items() if _desplazar(m, lag) in yoy_b]
        c = _corr([x for x, _ in pares], [y for _, y in pares])
        if c is None:
            continue
        if mejor is None or abs(c) > abs(mejor["corr"]):
            mejor = {"desfase_meses": lag, "corr": r(c, 3), "n": len(pares),
                     "banda": r(1.96 / math.sqrt(len(pares)), 3)}
    return mejor


def relaciones(sistemas_fichas, campo_extra):
    """Aristas del grafo. Cada una: tipo medida | contable | contexto."""
    def yoy(sid, serie_id):
        s = sistemas_fichas.get(sid)
        if not s:
            return {}
        if s["principal"]["id"] == serie_id:
            return s["principal"]["yoy_mensual"]
        for sec in s["secundarios"]:
            if sec["id"] == serie_id:
                return sec["yoy_mensual"]
        return {}

    aristas = []

    def medida(de, a, etiqueta, ya, yb, max_meses, detalle, grafico=None):
        m = mejor_desfase(ya, yb, max_meses)
        if not m or abs(m["corr"]) < (m["banda"] or 0):
            return
        aristas.append({"de": de, "a": a, "tipo": "medida", "etiqueta": etiqueta,
                        "corr": m["corr"], "desfase_meses": m["desfase_meses"], "n": m["n"],
                        "banda": m["banda"], "detalle": detalle, "grafico": grafico})

    # mercados europeos -> campo
    if campo_extra.get("transmision"):
        t = campo_extra["transmision"]
        mejor = max(t["desfases"], key=lambda d: d["corr"] or 0)
        aristas.append({"de": "ue", "a": "campo", "tipo": "medida", "etiqueta": "Precio europeo del cerdo",
                        "corr": mejor["corr"], "desfase_meses": round(mejor["semanas"] / 4.3, 1),
                        "desfase_semanas": mejor["semanas"], "n": mejor["n"], "banda": mejor["banda"],
                        "detalle": "El precio español del cerdo sigue al europeo casi sin retraso.",
                        "grafico": "transmision"})
    medida("mundo", "campo", "Índice FAO de alimentos", yoy("campo", "fao"), yoy("campo", "cerdo"), 6,
           "Los precios mundiales de los alimentos y el del cerdo en España se mueven a la vez.")
    medida("campo", "economia", "Precios agrarios y VAB agrario", yoy("campo", "cerdo"), yoy("economia", "vab_agr"), 12,
           "Cuando suben los precios del campo, el valor añadido agrario de la región sube después.")
    medida("turismo", "empleo", "Turismo y empleo", yoy("turismo", "pernoct"), yoy("empleo", "paro"), 6,
           "Más pernoctaciones suelen venir acompañadas de menos paro.")
    medida("empleo", "vivienda", "Empleo y compra de vivienda", yoy("empleo", "paro"), yoy("vivienda", "compraventa"), 9,
           "El paro y la compraventa de viviendas se mueven en sentidos opuestos.")
    medida("empresas", "empleo", "Creación de empresas y paro", yoy("empresas", "sociedades"), yoy("empleo", "paro"), 9,
           "La creación de sociedades anticipa parte del movimiento del paro.")
    medida("poblacion", "vivienda", "Población y vivienda", yoy("poblacion", "pob"), yoy("vivienda", "compraventa"), 12,
           "Los cambios de población acompañan a la compra de vivienda.")

    # contables
    aristas += [
        {"de": "economia", "a": "poblacion", "tipo": "contable", "etiqueta": "PIB por habitante",
         "detalle": "El PIB por habitante se obtiene dividiendo la riqueza producida entre la población."},
        {"de": "campo", "a": "economia", "tipo": "contable", "etiqueta": "Peso del campo en la economía",
         "detalle": "El valor añadido del campo forma parte del PIB regional."},
        {"de": "conocimiento", "a": "economia", "tipo": "contable", "etiqueta": "I+D sobre PIB",
         "detalle": "El gasto en I+D se mide como porcentaje del PIB regional."},
        {"de": "empleo", "a": "economia", "tipo": "contable", "etiqueta": "Trabajo y producción",
         "detalle": "El empleo es uno de los factores con los que se produce el PIB."},
    ]
    return aristas


NODOS = [
    {"id": "ue", "nombre": "Mercados de la UE", "tipo": "entorno", "x": 0.12, "y": 0.18},
    {"id": "mundo", "nombre": "Precios mundiales", "tipo": "entorno", "x": 0.12, "y": 0.72},
    {"id": "campo", "nombre": "Campo", "tipo": "sistema", "x": 0.36, "y": 0.45},
    {"id": "economia", "nombre": "Economía", "tipo": "sistema", "x": 0.62, "y": 0.45},
    {"id": "empleo", "nombre": "Empleo", "tipo": "sistema", "x": 0.62, "y": 0.12},
    {"id": "empresas", "nombre": "Empresas", "tipo": "sistema", "x": 0.38, "y": 0.10},
    {"id": "turismo", "nombre": "Turismo", "tipo": "sistema", "x": 0.86, "y": 0.14},
    {"id": "poblacion", "nombre": "Población", "tipo": "sistema", "x": 0.86, "y": 0.50},
    {"id": "vivienda", "nombre": "Vivienda", "tipo": "sistema", "x": 0.62, "y": 0.82},
    {"id": "conocimiento", "nombre": "Conocimiento", "tipo": "sistema", "x": 0.36, "y": 0.80},
]


# ------------------------------------------------------------------ montaje
def construir(A, campo_extra, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    rejilla = _meses(INICIO, hoy)
    sistemas = []
    for cfg in definicion():
        principal = bloque_serie(A, cfg["principal"], rejilla, hoy)
        if not principal:
            continue
        principal["esp"] = comparacion(A, cfg["principal"], "esp", rejilla)
        principal["ue"] = comparacion(A, cfg["principal"], "ue", rejilla)
        secundarios = []
        for scfg in cfg["secundarios"]:
            s = bloque_serie(A, scfg, rejilla, hoy)
            if not s:
                continue
            s["esp"] = comparacion(A, scfg, "esp", rejilla)
            s["ue"] = comparacion(A, scfg, "ue", rejilla)
            secundarios.append(s)
        sistemas.append({"id": cfg["id"], "nombre": cfg["nombre"], "descripcion": cfg["descripcion"],
                         "principal": principal, "secundarios": secundarios})

    fichas = {s["id"]: s for s in sistemas}
    rels = relaciones(fichas, campo_extra)

    # el JSON solo lleva lo que la web usa: serie original, estado mensual del
    # indicador principal y la última lectura de cada serie secundaria.
    for s in sistemas:
        for ficha in [s["principal"], *s["secundarios"]]:
            ficha.pop("mensual", None)
            ficha.pop("yoy_mensual", None)
            if ficha is not s["principal"]:
                ficha.pop("estado_mensual", None)

    return {
        "rejilla": rejilla,
        "sistemas": sistemas,
        "nodos": NODOS,
        "relaciones": rels,
        "metodo": {
            "estado": ("Se compara el último dato con el mismo periodo del año anterior y esa variación se sitúa entre las "
                       "de los años anteriores del propio indicador, a su frecuencia real (semanal, mensual, trimestral o anual). "
                       "Se marca «fuera de lo habitual» cuando queda en el 5 % más alto o más bajo Y además se aleja al menos dos "
                       "desviaciones robustas de la variación típica; «en el borde» cuando solo se cumple una de las dos condiciones; "
                       "«sin referencia» cuando no hay suficientes comparaciones previas (104 semanales, 36 mensuales, 12 trimestrales "
                       "u 8 anuales). La referencia son 5 años, o 10 en las series anuales, y deja fuera las comparaciones "
                       "contra los meses de pandemia (de marzo de 2020 a junio de 2021), que eran rebotes mecánicos."),
            "frescura": "Días transcurridos desde que terminó el periodo del último dato; se marca la serie cuando supera el plazo normal de su fuente (21 días las semanales, 75 las mensuales, 150 las trimestrales y 1.100 las anuales).",
            "relaciones": "Correlación entre variaciones interanuales con desfase de 0 a 12 meses; se muestra la de mayor valor absoluto y solo si supera el umbral 1,96/√n. Las relaciones contables no se estiman: son definiciones.",
            "limites": ("El estado dice si el cambio es raro para esa serie, no si es bueno o malo. No corrige el efecto de "
                        "cambios metodológicos ni de revisiones posteriores de las fuentes, y los años de la pandemia siguen "
                        "dentro de las series, aunque sus comparaciones se excluyen de la referencia."),
        },
    }
