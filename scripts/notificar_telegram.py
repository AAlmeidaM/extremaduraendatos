"""Avisos por Telegram de los datos nuevos (bot @datosextremadura_bot).

Tras cada ingesta diaria comprueba, para una lista de series clave, si hay un
periodo más reciente que el último avisado. Si lo hay, envía un mensaje con:
  - el dato de Extremadura (o Badajoz) y su cambio frente al periodo anterior
    y frente al mismo periodo del año anterior;
  - el mismo dato de España y/o de la media de la UE, cuando existe;
  - las próximas publicaciones previstas del INE (tabla calendario_publicacion).

Los lunes envía además un resumen del calendario de la semana aunque no haya
datos nuevos.

Configuración (en .env, nunca en Git):
  TELEGRAM_BOT_TOKEN=...   token de @BotFather
  TELEGRAM_CHAT_ID=...     lo rellena scripts/telegram_configurar.py
Sin estas variables el script no hace nada (sale con código 0).

Estado: tabla telegram_aviso (clave, ultimo_periodo) en la base de datos; la
primera ejecución envía un resumen con el último dato de cada serie.

Uso: .venv\\Scripts\\python.exe scripts\\notificar_telegram.py [--prueba] [--forzar-resumen]
  --prueba          imprime el mensaje sin enviarlo ni guardar estado
  --forzar-resumen  envía el resumen completo aunque no haya novedades
"""
from __future__ import annotations

import argparse
import html
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

import exportar_web as EW  # noqa: E402
from extremadura_datos import db  # noqa: E402
from extremadura_datos.config import Config  # noqa: E402

WEB = "https://extremaduraendatos.com"
MESES = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()

# (etiqueta, indicador, tokens, nuts)
Sel = tuple


@dataclass
class Serie:
    clave: str
    titulo: str
    bloque: str          # empleo, poblacion, turismo, vivienda, empresas, precios, europa
    tipo: str            # trimestral, mensual, semanal, anual
    unidad: str
    decimales: int
    principal: Sel       # Extremadura (o Badajoz)
    principal_nombre: str = "Extremadura"
    espana: Sel | None = None
    ue: Sel | None = None
    suma: list[Sel] = field(default_factory=list)   # series que se suman a la principal
    en_puntos: bool = False                           # tasas: cambios en puntos, no en %
    fuente: str = "INE"


PPS = "Purchasing power standard (PPS, EU27 from 2020), per inhabitant"
EPA = ["Tasa de paro de la población", "Ambos sexos", "Total"]

SERIES = [
    Serie("paro_epa", "Tasa de paro (EPA)", "Empleo", "trimestral", "%", 2,
          ("ine_epa_ccaa", EPA, "ES43"), espana=("ine_epa_ccaa", EPA, "ES"), en_puntos=True),
    Serie("poblacion", "Población residente", "Población", "trimestral", "habitantes", 0,
          ("ine_ecp_poblacion_ccaa", ["Total", "Todas las edades"], "ES43"),
          espana=("ine_ecp_poblacion_ccaa", ["Total", "Todas las edades", "Total Nacional"], "ES")),
    Serie("pernoctaciones", "Pernoctaciones en hoteles", "Turismo", "mensual", "", 0,
          ("ine_turismo_viajeros_pernoctaciones_ccaa", ["Pernoctaciones", "Total"], "ES43"),
          espana=("ine_turismo_viajeros_pernoctaciones_ccaa", ["Pernoctaciones", "Total categorías", "Total"], "ES")),
    Serie("viajeros", "Viajeros en hoteles", "Turismo", "mensual", "", 0,
          ("ine_turismo_viajeros_pernoctaciones_ccaa", ["Viajeros", "Total"], "ES43"),
          espana=("ine_turismo_viajeros_pernoctaciones_ccaa", ["Viajeros", "Total categorías", "Total"], "ES")),
    Serie("compraventa", "Compraventa de viviendas", "Vivienda", "mensual", "", 0,
          ("ine_compraventa_vivienda_ccaa_provincia", ["General", "Compraventa"], "ES43"),
          espana=("ine_compraventa_vivienda_ccaa_provincia", ["General", "Compraventa"], "ES")),
    Serie("hipotecas", "Hipotecas sobre fincas urbanas", "Vivienda", "mensual", "", 0,
          ("ine_hipotecas_provincia", ["Total", "Número de hipotecas"], "ES431"),
          suma=[("ine_hipotecas_provincia", ["Total", "Número de hipotecas"], "ES432")]),
    Serie("ipv", "Precio de la vivienda (variación anual)", "Vivienda", "trimestral", "%", 1,
          ("ine_ipv_ccaa", ["General", "Variación anual"], "ES43"),
          espana=("ine_ipv_ccaa", ["General", "Variación anual"], "ES"), en_puntos=True),
    Serie("ipc", "Inflación (IPC, variación anual)", "Precios de consumo", "mensual", "%", 1,
          ("ine_ipc_ccaa", ["Índice general", "Variación anual"], "ES43"),
          espana=("ine_ipc_ccaa", ["Índice general", "Variación anual"], "ES"), en_puntos=True),
    Serie("sociedades", "Sociedades mercantiles creadas", "Empresas", "mensual", "", 0,
          ("ine_soc_mercantiles_constituidas_ccaa", ["Sociedades Constituídas", "Mercantiles", "Número de Sociedades"], "ES43"),
          espana=("ine_soc_mercantiles_constituidas_ccaa", ["Sociedades Constituídas", "Mercantiles", "Número de Sociedades"], "ES")),
    Serie("confianza", "Confianza empresarial (índice)", "Empresas", "trimestral", "", 1,
          ("ine_confianza_empresarial_ccaa", ["Índice"], "ES43"),
          espana=("ine_confianza_empresarial_ccaa", ["Índice"], "ES")),
    # Europa (anual, Eurostat)
    Serie("eu_pib", "PIB por habitante (PPA)", "Europa", "anual", "€ PPA", 0,
          ("eurostat_pib_nuts2", [PPS], "ES43"), espana=("eurostat_pib_nuts2", [PPS], "ES"),
          ue=("eurostat_pib_nuts2", [PPS], "EU27_2020"), fuente="Eurostat"),
    Serie("eu_paro", "Tasa de paro 15-74 años", "Europa", "anual", "%", 1,
          ("eurostat_paro_nuts2", ["All ISCED 2011 levels", "Total", "From 15 to 74 years"], "ES43"),
          espana=("eurostat_paro_nuts2", ["All ISCED 2011 levels", "Total", "From 15 to 74 years"], "ES"),
          ue=("eurostat_paro_nuts2", ["All ISCED 2011 levels", "Total", "From 15 to 74 years"], "EU27_2020"),
          en_puntos=True, fuente="Eurostat"),
    Serie("eu_empleo", "Tasa de empleo 20-64 años", "Europa", "anual", "%", 1,
          ("eurostat_empleo_nuts2", ["Total", "From 20 to 64 years"], "ES43"),
          espana=("eurostat_empleo_nuts2", ["Total", "From 20 to 64 years"], "ES"),
          ue=("eurostat_empleo_nuts2", ["Total", "From 20 to 64 years"], "EU27_2020"),
          en_puntos=True, fuente="Eurostat"),
    Serie("eu_renta", "Renta disponible de los hogares por habitante (PPA)", "Europa", "anual", "€ PPA", 0,
          ("eurostat_renta_hogares_nuts2", [PPS, "Disposable income, net"], "ES43"),
          espana=("eurostat_renta_hogares_nuts2", [PPS, "Disposable income, net"], "ES"),
          ue=("eurostat_renta_hogares_nuts2", [PPS, "Disposable income, net"], "EU27_2020"), fuente="Eurostat"),
    # Precios agrarios (semanales / mensuales)
    Serie("pr_cerdo", "Cerdo de cebo, clase S (€/100 kg)", "Precios agrarios", "semanal", "€", 2,
          ("agrifood_porcino", ["S"], "ES"), principal_nombre="España",
          ue=("agrifood_porcino", ["S"], "EU27_2020"), fuente="Comisión Europea"),
    Serie("pr_cordero", "Cordero ligero (€/100 kg)", "Precios agrarios", "semanal", "€", 2,
          ("agrifood_ovino", ["Light Lamb"], "ES"), principal_nombre="España",
          ue=("agrifood_ovino", ["Light Lamb"], "EU27_2020"), fuente="Comisión Europea"),
    Serie("pr_vacuno", "Añojo R3 (€/100 kg)", "Precios agrarios", "semanal", "€", 2,
          ("agrifood_vacuno", ["Young bulls", "AR3"], "ES"), principal_nombre="España",
          ue=("agrifood_vacuno", ["Young bulls", "AR3"], "EU27_2020"), fuente="Comisión Europea"),
    Serie("pr_aceite_bad", "Aceite de oliva virgen (€/100 kg)", "Precios agrarios", "semanal", "€", 2,
          ("agrifood_aceite", ["Virgin olive oil (up to 2%)", "Badajoz (ES431)"], "ES431"), principal_nombre="Badajoz",
          espana=("agrifood_aceite", ["Virgin olive oil (up to 2%)", "Average national price"], "ES"), fuente="Comisión Europea"),
    Serie("pr_leche", "Leche cruda de vaca (€/100 kg)", "Precios agrarios", "mensual", "€", 2,
          ("agrifood_leche", ["Raw milk"], "ES"), principal_nombre="España",
          ue=("agrifood_leche", ["Raw milk"], "EU27_2020"), fuente="Comisión Europea"),
    Serie("pr_fao", "Índice FAO de precios de los alimentos", "Precios agrarios", "mensual", "", 1,
          ("fao_indice_precios_alimentos", ["Índice general"], "WORLD"), principal_nombre="Mundo", fuente="FAO"),
]


# ------------------------------------------------------------------ formato
def num(v, d=0):
    if v is None:
        return "–"
    s = f"{v:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def periodo(f: date, tipo: str) -> str:
    if tipo == "trimestral":
        return f"{(f.month - 1) // 3 + 1}.º trimestre de {f.year}"
    if tipo == "mensual":
        return f"{MESES[f.month - 1]} de {f.year}"
    if tipo == "semanal":
        return f"semana del {f.strftime('%d/%m/%Y')}"
    return str(f.year)


def cambio(actual, anterior, en_puntos, d):
    if actual is None or anterior is None:
        return None
    if en_puntos:
        dif = actual - anterior
        signo = "▲" if dif > 0.005 else "▼" if dif < -0.005 else "="
        return f"{signo} {num(abs(dif), max(d, 1))} puntos"
    if anterior == 0:
        return None
    pct = (actual / anterior - 1) * 100
    signo = "▲" if pct > 0.05 else "▼" if pct < -0.05 else "="
    return f"{signo} {num(abs(pct), 1)} %"


def buscar_mismo_periodo(obs, f, tipo):
    d = dict(obs)
    if tipo == "semanal":
        for g, v in reversed(obs):
            if abs((g - (f - timedelta(weeks=52))).days) <= 3:
                return v
        return None
    try:
        return d.get(f.replace(year=f.year - 1))
    except ValueError:
        return None


# ------------------------------------------------------------------ datos
def serie_obs(A, sel, suma=()):
    obs = A.una(*sel)
    for s in suma:
        extra = dict(A.una(*s))
        obs = [(f, v + extra[f]) for f, v in obs if f in extra]
    return obs


def bloque_texto(A, s: Serie) -> tuple[date, str] | None:
    obs = serie_obs(A, s.principal, s.suma)
    if not obs:
        return None
    f, v = obs[-1]
    ant = obs[-2][1] if len(obs) > 1 else None
    hace = buscar_mismo_periodo(obs, f, s.tipo)
    uni = f" {s.unidad}" if s.unidad and s.unidad != "%" else ("%" if s.unidad == "%" else "")
    lineas = [f"<b>{html.escape(s.titulo)}</b> · {periodo(f, s.tipo)}"]
    limite = {"semanal": 30, "mensual": 100, "trimestral": 200, "anual": 900}[s.tipo]
    if (date.today() - f).days > limite:
        lineas[0] += " ⚠️ <i>serie sin actualizar, revisar la carga</i>"
    partes = []
    c1 = cambio(v, ant, s.en_puntos, s.decimales)
    c2 = cambio(v, hace, s.en_puntos, s.decimales) if s.tipo != "anual" else None
    anterior_txt = {"semanal": "semana anterior", "mensual": "mes anterior", "trimestral": "trimestre anterior", "anual": "año anterior"}[s.tipo]
    if c1:
        partes.append(f"{c1} vs. {anterior_txt}")
    if c2:
        partes.append(f"{c2} vs. hace un año")
    lineas.append(f"  {s.principal_nombre}: <b>{num(v, s.decimales)}{uni}</b>" + (f" ({'; '.join(partes)})" if partes else ""))
    for nombre, sel in (("España", s.espana), ("Media UE", s.ue)):
        if not sel:
            continue
        o = A.una(*sel)
        previos = [(g, x) for g, x in o if g <= f]
        if not previos or (f - previos[-1][0]).days > 400:
            continue
        fo, vo = previos[-1]
        extra = [] if fo == f else [f"dato de {periodo(fo, s.tipo)}"]
        if s.tipo != "anual":
            ch = cambio(vo, buscar_mismo_periodo(o, fo, s.tipo), s.en_puntos, s.decimales)
            if ch:
                extra.append(f"{ch} vs. hace un año")
        if s.en_puntos or s.unidad == "%":
            dif = v - vo
            if abs(dif) < 0.05:
                extra.append(f"igual que {s.principal_nombre}")
            else:
                extra.append(f"{s.principal_nombre} está {num(abs(dif), 1)} puntos {'por encima' if dif > 0 else 'por debajo'}")
        elif s.clave.startswith("eu_") or s.bloque == "Precios agrarios":
            extra.append(f"{s.principal_nombre} = {num(v / vo * 100, 0)} % de este valor")
        lineas.append(f"  {nombre}: {num(vo, s.decimales)}{uni}" + (f" ({'; '.join(extra)})" if extra else ""))
    lineas.append(f"  <i>Fuente: {s.fuente}</i>")
    return f, "\n".join(lineas)


def calendario(conn, dias=7) -> str:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT c.fecha_publicacion, i.nombre, c.periodo_referencia
               FROM calendario_publicacion c JOIN indicador i ON i.id = c.indicador_id
               WHERE i.activo AND c.fecha_publicacion BETWEEN current_date AND current_date + %s
               ORDER BY c.fecha_publicacion, i.nombre""",
            (dias,),
        )
        filas = cur.fetchall()
    if not filas:
        return ""
    dias_sem = "lun mar mié jue vie sáb dom".split()
    txt = ["<b>📅 Próximas publicaciones del INE</b>"]
    vistos = set()
    for f, nombre, per in filas:
        k = (f, nombre)
        if k in vistos:
            continue
        vistos.add(k)
        txt.append(f"  {dias_sem[f.weekday()]} {f.strftime('%d/%m')}: {html.escape(nombre)}" + (f" ({html.escape(per)})" if per else ""))
    return "\n".join(txt[:25])


# ------------------------------------------------------------------ estado y envío
def asegurar_tabla(conn):
    with conn.cursor() as cur:
        cur.execute(
            """CREATE TABLE IF NOT EXISTS telegram_aviso (
                   clave TEXT PRIMARY KEY,
                   ultimo_periodo DATE NOT NULL,
                   enviado_en TIMESTAMPTZ NOT NULL DEFAULT now())"""
        )
        cur.execute("CREATE TABLE IF NOT EXISTS telegram_resumen (dia DATE PRIMARY KEY)")
    conn.commit()


def estado(conn) -> dict[str, date]:
    with conn.cursor() as cur:
        cur.execute("SELECT clave, ultimo_periodo FROM telegram_aviso")
        return dict(cur.fetchall())


def guardar(conn, clave, f):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO telegram_aviso (clave, ultimo_periodo) VALUES (%s, %s)
               ON CONFLICT (clave) DO UPDATE SET ultimo_periodo = EXCLUDED.ultimo_periodo, enviado_en = now()""",
            (clave, f),
        )


def enviar(token, chat_id, texto):
    trozos, actual = [], ""
    for bloque in texto.split("\n\n"):
        if len(actual) + len(bloque) + 2 > 3900:
            trozos.append(actual)
            actual = ""
        actual += ("\n\n" if actual else "") + bloque
    if actual:
        trozos.append(actual)
    for t in trozos:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": t, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Telegram respondió {r.status_code}: {r.text[:300]}")
        time.sleep(1)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--prueba", action="store_true")
    ap.add_argument("--forzar-resumen", action="store_true")
    args = ap.parse_args()

    cfg = Config.load()  # carga también .env
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not args.prueba and (not token or not chat_id):
        print("Telegram: faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en .env; no se envía nada.")
        return 0

    conn = db.connect(cfg.database_url)
    try:
        asegurar_tabla(conn)
        A = EW.Almacen(conn)
        previo = estado(conn)
        primera = not previo
        nuevos: dict[str, list[str]] = {}
        pendientes = []
        for s in SERIES:
            try:
                res = bloque_texto(A, s)
            except Exception as exc:  # noqa: BLE001 — una serie rota no para el resto
                print(f"AVISO {s.clave}: {exc}")
                continue
            if not res:
                continue
            f, texto = res
            if primera or args.forzar_resumen or previo.get(s.clave) is None or f > previo[s.clave]:
                nuevos.setdefault(s.bloque, []).append(texto)
            pendientes.append((s.clave, f))

        hoy = date.today()
        cal = calendario(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM telegram_resumen WHERE dia=%s", (hoy,))
            ya_lunes = cur.fetchone() is not None
        lunes = hoy.weekday() == 0 and not ya_lunes

        if not nuevos and not lunes:
            print("Telegram: sin datos nuevos.")
            return 0

        if nuevos:
            cabecera = ("<b>📊 Extremadura en Datos · resumen inicial</b>\nÚltimo dato disponible de cada serie."
                        if primera or args.forzar_resumen else
                        f"<b>📊 Extremadura en Datos · datos nuevos</b>\n{hoy.strftime('%d/%m/%Y')}")
            partes = [cabecera]
            for bloque, textos in nuevos.items():
                partes.append(f"<b>— {html.escape(bloque).upper()} —</b>")
                partes.extend(textos)
        else:
            partes = [f"<b>📅 Extremadura en Datos · semana del {hoy.strftime('%d/%m/%Y')}</b>\nNo hay datos nuevos hoy."]
        if cal:
            partes.append(cal)
        partes.append(f'<a href="{WEB}">{WEB.replace("https://", "")}</a>')
        mensaje = "\n\n".join(partes)

        if args.prueba:
            print(mensaje)
            return 0
        enviar(token, chat_id, mensaje)
        for clave, f in pendientes:
            guardar(conn, clave, f)
        if lunes:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO telegram_resumen (dia) VALUES (%s) ON CONFLICT DO NOTHING", (hoy,))
        conn.commit()
        print(f"Telegram: mensaje enviado ({sum(len(v) for v in nuevos.values())} series).")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
