"""Pruebas de la fase 3 (precios agrarios) con muestras REALES.

- tests/fixtures/agrifood_muestra.json: respuestas reales del portal
  Agri-food (semana 31/08–06/09/2026 y meses de 2026), capturadas el
  2026-09-16 desde el navegador del PC de producción.
- Los CSV del Observatorio de la Junta y de la FAO de abajo copian el formato
  real (cabecera y primeras filas) visto el 2026-09-15/16.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from extremadura_datos import agrifood, fao, observatorio_junta
from extremadura_datos.precios_util import precio_desde_texto

FIX = json.loads((Path(__file__).parent / "fixtures" / "agrifood_muestra.json").read_text(encoding="utf-8"))


def test_precio_desde_texto():
    assert precio_desde_texto("€699.95") == 699.95
    assert precio_desde_texto("€233,00") == 233.0
    assert precio_desde_texto("€1,008.50") == 1008.5
    assert precio_desde_texto("1.008,50 €") == 1008.5
    assert precio_desde_texto(364) == 364.0
    assert precio_desde_texto("€,00") is None  # sin cotización
    assert precio_desde_texto(None) is None
    assert precio_desde_texto("n.d.") is None


def test_agrifood_porcino_espana_y_ue():
    filas = agrifood.parsear("pigmeat/prices", FIX["pig"])
    idx = {(f.territorio_clave, f.serie_atributos["pigClass"]["codigo"]): f for f in filas}
    es_s = idx[("nuts:ES", "S")]
    assert es_s.valor == 178.08
    assert es_s.unidad == "€/100 kg"
    assert es_s.periodo_fecha == date(2026, 8, 31)
    assert es_s.periodo_codigo == "S36" and es_s.anyo == 2026
    assert idx[("nuts:EU27_2020", "S")].valor == 172.88  # media UE
    assert idx[("nuts:ES", "Piglet")].unidad == "€/cabeza"
    assert es_s.serie_codigo_origen == "agrifood|pigmeat/prices|pigClass=S|100 KG|ES"


def test_agrifood_cereales_coma_decimal_y_mercado_badajoz():
    muestra = list(FIX["cer"])
    # Badajoz existe como mercado de cereales en la API real (visto en 2025);
    # se añade una fila con su forma exacta para probar el paso a provincia.
    muestra.append(dict(FIX["cer"][0], marketName="Badajoz", productName="Feed maize", price="€231,50"))
    filas = agrifood.parsear("cereal/prices", muestra)
    sevilla = next(f for f in filas if f.serie_atributos["marketName"]["nombre"] == "Sevilla" and f.valor == 246.6)
    assert sevilla.territorio_clave == "nuts:ES" and sevilla.unidad == "€/t"
    badajoz = next(f for f in filas if f.serie_atributos["marketName"]["nombre"] == "Badajoz")
    assert badajoz.territorio_clave == "nuts:ES431" and badajoz.valor == 231.5


def test_agrifood_aceite_mercado_con_codigo_nuts():
    muestra = list(FIX["oil"]) + [dict(FIX["oil"][0], market="Badajoz (ES431)", price="€330.00")]
    filas = agrifood.parsear("oliveOil/prices", muestra)
    terr = {f.serie_atributos["market"]["nombre"]: f.territorio_clave for f in filas}
    assert terr["Jaén (ES616)"] == "nuts:ES"  # otros NUTS3 cuelgan del país
    assert terr["Average national price"] == "nuts:ES"
    assert terr["Badajoz (ES431)"] == "nuts:ES431"


def test_agrifood_mensuales_leche_y_fertilizantes():
    leche = agrifood.parsear("rawMilk/prices", FIX["milk"])
    assert {(f.periodo_fecha, f.periodo_codigo) for f in leche} == {(date(2026, 8, 1), "M08"), (date(2026, 7, 1), "M07")}
    fert = agrifood.parsear("fertiliser/prices", FIX["fert"])
    assert all(f.territorio_clave == "nuts:EU27_2020" for f in fert)
    assert fert[0].periodo_fecha == date(2026, 8, 1) and fert[0].valor == 364.0 and fert[0].unidad == "€/t"


def test_agrifood_descarta_eu_mas_uk_y_precio_vacio():
    filas = agrifood.parsear("cereal/prices", [
        dict(FIX["cer"][0], memberStateCode="EU+UK"),
        dict(FIX["cer"][0], price=None),
        dict(FIX["cer"][0], price="€,00"),
    ])
    assert filas == []


CSV_JUNTA = (
    "CODIGO ZONA;SEMANA;POSICION COMERCIAL;VALOR;UNIDAD MEDIDA;\n"
    "Badajoz;Semana 21: (19/05/25 - 25/05/25);En origen;130.00;€/100 kg;\n"
    "Cáceres;Semana 21: (19/05/25 - 25/05/25);En origen;128.50;€/100 kg;\n"
    "Badajoz;Semana 01: (29/12/25 - 4/01/26);En origen;5.20;€/kg de pepita;\n"
)


def test_junta_csv():
    filas = observatorio_junta.parsear_csv(CSV_JUNTA, "26", "Melocotón todas las variedades")
    assert len(filas) == 3
    bad = filas[0]
    assert bad.territorio_clave == "nuts:ES431" and bad.valor == 130.0
    assert bad.periodo_fecha == date(2025, 5, 19) and bad.periodo_codigo == "S21"
    assert filas[1].territorio_clave == "nuts:ES432"
    # Semana que cruza el año: año ISO 2026, semana 1
    assert filas[2].periodo_fecha == date(2025, 12, 29) and filas[2].anyo == 2026 and filas[2].periodo_codigo == "S01"
    assert bad.serie_codigo_origen == "junta|26|En origen|€/100 kg|ES431"


HTML_FICHA = """
<form id="_precios_WAR_x_:frmDatos" name="_precios_WAR_x_:frmDatos" method="post" action="/precios?p_auth=abc&amp;p_p_lifecycle=1">
<input type="hidden" name="_precios_WAR_x_:frmDatos" value="_precios_WAR_x_:frmDatos" />
<input type="hidden" name="javax.faces.encodedURL" value="https://x/precios" />
<select name="_precios_WAR_x_:frmDatos:MOSTRAR_input"><option value="ACTU" selected="selected">Actual</option><option value="2025">2025</option></select>
<input type="text" name="_precios_WAR_x_:frmDatos:tabla:j_idt50:filter" value="" />
<input type="submit" name="_precios_WAR_x_:frmDatos:j_idt60" value="Exportar a CSV" />
<input type="hidden" name="javax.faces.ViewState" value="123:-456" />
</form>
<a href="/precios?p_p_id=precios&amp;_precios_entidad_precio_seleccionada_id=26&amp;x=1">Melocotón todas las variedades</a>
<a href="/precios?_precios_entidad_precio_seleccionada_id=42200#main">Saltar al contenido</a>
"""


def test_junta_formulario_y_listado():
    form = observatorio_junta._Formulario()
    form.feed(HTML_FICHA)
    assert form.form_id == "_precios_WAR_x_:frmDatos"
    assert form.action == "/precios?p_auth=abc&p_p_lifecycle=1"
    campos = dict(form.campos)
    assert campos["javax.faces.ViewState"] == "123:-456"
    assert campos["_precios_WAR_x_:frmDatos:MOSTRAR_input"] == "ACTU"
    assert form.boton_csv == "_precios_WAR_x_:frmDatos:j_idt60"
    assert observatorio_junta.productos(HTML_FICHA) == {"26": "Melocotón todas las variedades"}


CSV_FAO = (
    "FAO Food Price Index,,,,,,,,\n"
    "2014-2016=100,,,,,,,,\n"
    "Date,Food Price Index,Meat,Dairy,Cereals,Oils,Sugar,,\n"
    ",,,,,,,,\n"
    "1990-01,64.4,74.3,53.5,64.1,44.59,87.9,,\n"
    "2026-08,133.3,127.9,119.2,116.3,196.9,106.4,,\n"
)


def test_fao_csv_y_enlace():
    filas = fao.parsear_csv(CSV_FAO)
    assert len(filas) == 12
    ago = {f.serie_atributos["grupo"]["codigo"]: f for f in filas if f.periodo_fecha == date(2026, 8, 1)}
    assert ago["Food Price Index"].valor == 133.3 and ago["Oils"].valor == 196.9
    assert ago["Meat"].territorio_clave == "nuts:WORLD" and ago["Meat"].periodo_codigo == "M08"
    html = '<a href="/media/docs/worldfoodsituationlibraries/default-document-library/food_price_indices_data.csv?sfvrsn=523ebd2a_83&amp;download=true">CSV</a>'
    assert fao.url_csv(html) == "https://www.fao.org/media/docs/worldfoodsituationlibraries/default-document-library/food_price_indices_data.csv?sfvrsn=523ebd2a_83&download=true"
