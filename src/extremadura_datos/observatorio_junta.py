"""Observatorio de Precios y Mercados de la Junta de Extremadura: precios
agrícolas semanales por provincia (Badajoz/Cáceres). Fase 3 de
docs/ampliacion-nuts2-agro.md.

Web Liferay + JSF/PrimeFaces sin API. Mecanismo verificado desde el
navegador del PC el 2026-09-16:

1. `GET /precios` → enlaces de cada producto (`entidad_precio_seleccionada_id=N`).
   Solo sector agricultura: la pestaña de ganadería no tiene registros.
2. `GET` de la ficha del producto (≈500 KB, 20-60 s de respuesta) → formulario
   `..._:frmDatos` con su `action` (lleva `p_auth`) y campos ocultos
   (`javax.faces.ViewState`...).
3. Cambiar la campaña (`MOSTRAR_input` = `ACTU` | `2026` | `2025`...) exige
   un POST AJAX de PrimeFaces (`valueChange`): la campaña queda guardada en
   la SESIÓN del servidor; mandar `MOSTRAR_input` solo en la exportación no
   basta (devuelve la campaña anterior de la sesión).
4. POST del formulario con el botón "Exportar a CSV" → `text/csv; Cp1252`:
   `CODIGO ZONA;SEMANA;POSICION COMERCIAL;VALOR;UNIDAD MEDIDA;`
   `Badajoz;Semana 38: (15/09/25 - 21/09/25);En origen;5.62;€/kg de pepita;`

Por el estado en sesión, los productos se piden de uno en uno y en orden
(nunca en paralelo). Como la ficha tarda tanto, en modo incremental solo se
descarga si han pasado DIAS_ENTRE_DESCARGAS desde la última descarga
correcta (se guarda en indicador.origen_actualizado).
"""

from __future__ import annotations

import csv
import io
import logging
import re
import time
from datetime import date, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin

import requests

from . import db
from .config import Config
from .eurostat_parse import PREFIJO_CLAVE_NUTS
from .indicadores import Indicador
from .parse import ObservacionParseada
from .precios_util import guarda_crudo, periodo_semanal

logger = logging.getLogger(__name__)

BASE = "https://observatoriopreciosymercados.juntaex.es"
LISTADO = BASE + "/precios"
AÑO_INICIO_HISTORICO = 2023
DIAS_ENTRE_DESCARGAS = 6
ZONAS = {"badajoz": "ES431", "caceres": "ES432", "cáceres": "ES432"}
_RE_SEMANA = re.compile(r"\((\d{1,2})/(\d{1,2})/(\d{2,4})\s*-")


class ObservatorioError(RuntimeError):
    pass


class _Formulario(HTMLParser):
    """Recoge action y campos del formulario cuyo id termina en ':frmDatos'."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.dentro = False
        self.action: str | None = None
        self.form_id: str | None = None
        self.campos: list[tuple[str, str]] = []
        self.boton_csv: str | None = None
        self._select: str | None = None
        self._select_valor: str | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form" and str(a.get("id", "")).endswith(":frmDatos"):
            self.dentro, self.action, self.form_id = True, a.get("action"), a.get("id")
            return
        if not self.dentro:
            return
        if tag == "input" and a.get("name"):
            tipo = (a.get("type") or "text").lower()
            if tipo in ("submit", "button"):
                if "csv" in str(a.get("value", "")).lower():
                    self.boton_csv = a["name"]
            elif tipo not in ("checkbox", "radio") or "checked" in a:
                self.campos.append((a["name"], a.get("value") or ""))
        elif tag == "select" and a.get("name"):
            self._select, self._select_valor = a["name"], None
        elif tag == "option" and self._select:
            if self._select_valor is None or "selected" in a:
                self._select_valor = a.get("value") or ""

    def handle_endtag(self, tag):
        if tag == "select" and self._select:
            self.campos.append((self._select, self._select_valor or ""))
            self._select = None
        elif tag == "form" and self.dentro:
            self.dentro = False


def productos(html_listado: str) -> dict[str, str]:
    """{id: nombre} de los productos del listado."""
    encontrados: dict[str, str] = {}
    for href, texto in re.findall(r'<a[^>]+href="([^"]*entidad_precio_seleccionada_id=\d+[^"]*)"[^>]*>(.*?)</a>', html_listado, flags=re.S):
        nombre = re.sub(r"<[^>]+>", "", texto).strip()
        ident = re.search(r"entidad_precio_seleccionada_id=(\d+)", href).group(1)
        if nombre and "saltar" not in nombre.lower():
            encontrados[ident] = re.sub(r"\s+", " ", nombre)
    return encontrados


def parsear_csv(texto: str, producto_id: str, producto: str) -> list[ObservacionParseada]:
    resultado: list[ObservacionParseada] = []
    lector = csv.reader(io.StringIO(texto), delimiter=";")
    cabecera = next(lector, None)
    if not cabecera or "SEMANA" not in [c.strip().upper() for c in cabecera]:
        raise ObservatorioError(f"CSV inesperado para {producto}: {texto[:200]!r}")
    for fila in lector:
        if len(fila) < 5 or not fila[0].strip():
            continue
        zona, semana, posicion, valor_txt, unidad = (c.strip() for c in fila[:5])
        codigo_zona = ZONAS.get(zona.lower())
        m = _RE_SEMANA.search(semana)
        if codigo_zona is None or m is None:
            continue
        dia, mes, anyo = (int(x) for x in m.groups())
        anyo = anyo + 2000 if anyo < 100 else anyo
        try:
            valor = float(valor_txt.replace(",", "."))
        except ValueError:
            continue
        if valor <= 0:
            continue
        fecha, anyo_iso, codigo = periodo_semanal(date(anyo, mes, dia))
        resultado.append(
            ObservacionParseada(
                territorio_clave=PREFIJO_CLAVE_NUTS + codigo_zona,
                territorio_nombre_origen=zona,
                periodo_fecha=fecha,
                anyo=anyo_iso,
                periodo_codigo=codigo,
                valor=valor,
                unidad=unidad or None,
                escala=None,
                tipo_dato=None,
                secreto=False,
                serie_nombre_origen=f"{zona}. {producto}. {posicion}",
                serie_codigo_origen=f"junta|{producto_id}|{posicion}|{unidad}|{codigo_zona}",
                serie_atributos={
                    "producto": {"nombre": producto, "codigo": producto_id},
                    "posicion_comercial": {"nombre": posicion, "codigo": posicion},
                },
            )
        )
    return resultado


class ObservatorioClient:
    def __init__(self, timeout: int = 180, pausa: float = 1.0):
        self.timeout = timeout
        self.pausa = pausa
        self.sesion = requests.Session()
        self.sesion.headers.update({"User-Agent": "Mozilla/5.0 (extremadura-en-datos; uso personal)"})

    def listado(self) -> tuple[str, dict[str, str]]:
        resp = self.sesion.get(LISTADO, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text, productos(resp.text)

    def exportar(self, html_listado: str, producto_id: str, campañas: list[str]) -> dict[str, str]:
        """Devuelve {campaña: texto CSV} para un producto (peticiones en serie)."""
        m = re.search(rf'href="([^"]*entidad_precio_seleccionada_id={producto_id}[^"]*)"', html_listado)
        if not m:
            raise ObservatorioError(f"Producto {producto_id} no está en el listado.")
        ficha = self.sesion.get(urljoin(BASE, m.group(1).replace("&amp;", "&")), timeout=self.timeout)
        ficha.raise_for_status()
        form = _Formulario()
        form.feed(ficha.text)
        if not form.action or not form.form_id:
            raise ObservatorioError(f"Ficha del producto {producto_id} sin formulario reconocible.")
        action = urljoin(BASE, form.action)
        pref = form.form_id
        boton = form.boton_csv or f"{pref}:j_idt60"
        resultado: dict[str, str] = {}
        for campaña in campañas:
            campos = [(k, v) for k, v in form.campos if k != f"{pref}:MOSTRAR_input"]
            campos.append((f"{pref}:MOSTRAR_input", campaña))
            ajax = campos + [
                ("javax.faces.partial.ajax", "true"),
                ("javax.faces.source", f"{pref}:MOSTRAR"),
                ("javax.faces.partial.execute", f"{pref}:MOSTRAR"),
                ("javax.faces.partial.render", pref),
                ("javax.faces.behavior.event", "valueChange"),
            ]
            time.sleep(self.pausa)
            self.sesion.post(action, data=ajax, headers={"Faces-Request": "partial/ajax"}, timeout=self.timeout).raise_for_status()
            time.sleep(self.pausa)
            resp = self.sesion.post(action, data=campos + [(boton, "Exportar a CSV")], timeout=self.timeout)
            resp.raise_for_status()
            if "csv" not in resp.headers.get("content-type", "").lower():
                # Visto en producción (2026-09-16): algunos productos no tienen
                # la campaña pedida (p.ej. 2023 en arroz, avena, cebada) y el
                # servidor devuelve la página HTML en vez del CSV. Se salta
                # esa campaña y se sigue con las demás del mismo producto.
                logger.warning("Observatorio: %s sin campaña %s (no devolvió CSV), se omite.", producto_id, campaña)
                continue
            resultado[campaña] = resp.content.decode("cp1252", errors="replace")
        if not resultado:
            raise ObservatorioError(f"El producto {producto_id} no devolvió CSV en ninguna campaña {campañas}.")
        return resultado


def ingerir_indicador(conn, cfg: Config, indicador: Indicador, modo: str, cliente: ObservatorioClient | None = None) -> None:
    indicador_id = db.get_or_create_indicador(conn, indicador)
    hoy = date.today()
    if modo == "incremental":
        ultima = db.origen_actualizado(conn, indicador_id)
        if ultima:
            try:
                dias = (hoy - datetime.fromisoformat(ultima).date()).days
            except ValueError:
                dias = DIAS_ENTRE_DESCARGAS
            if dias < DIAS_ENTRE_DESCARGAS:
                logger.info("%s: última descarga hace %d días (<%d) -- se omite.", indicador.codigo, dias, DIAS_ENTRE_DESCARGAS)
                return
        campañas = ["ACTU"]
    else:
        campañas = [str(a) for a in range(AÑO_INICIO_HISTORICO, hoy.year + 1)]

    logger.info("--- %s (Observatorio Junta, campañas %s) ---", indicador.codigo, campañas)
    cliente = cliente or ObservatorioClient()
    total, errores = 0, []
    try:
        html, lista = cliente.listado()
    except requests.RequestException as exc:
        db.registrar_carga(conn, indicador_id, "error", f"Listado: {exc}")
        logger.error("%s: no se pudo leer el listado: %s", indicador.codigo, exc)
        return
    logger.info("%s: %d productos en el listado.", indicador.codigo, len(lista))
    for producto_id, nombre in lista.items():
        try:
            csvs = cliente.exportar(html, producto_id, campañas)
        except (requests.RequestException, ObservatorioError) as exc:
            logger.error("%s: %s (%s): %s", indicador.codigo, nombre, producto_id, exc)
            errores.append(f"{nombre}: {exc}")
            continue
        filas: list[ObservacionParseada] = []
        for campaña, texto in csvs.items():
            guarda_crudo(cfg.datasets_dir, "junta_observatorio", f"{producto_id}_{campaña}", texto, extension="csv")
            try:
                filas.extend(parsear_csv(texto, producto_id, nombre))
            except ObservatorioError as exc:
                errores.append(str(exc))
        if filas:
            n, _ = db.upsert_observaciones(conn, indicador_id, filas)
            total += n
            logger.info("%s: %s -> %d filas.", indicador.codigo, nombre, n)

    estado = "error" if errores and total == 0 else "ok"
    mensaje = "ok" if not errores else f"{len(errores)} productos con error: {'; '.join(errores)[:1500]}"
    db.registrar_carga(conn, indicador_id, estado, mensaje, filas_leidas=total, filas_insertadas=total)
    if estado == "ok" and len(errores) < len(lista):
        db.guardar_origen_actualizado(conn, indicador_id, hoy.isoformat())
    logger.info("%s: %d filas cargadas/actualizadas (%d errores).", indicador.codigo, total, len(errores))
