"""Pruebas de eurostat_parse.py con respuestas JSON-stat REALES de Eurostat.

Los fixtures de tests/fixtures/ se capturaron el 2026-09-15 desde el
navegador del PC de producción (ver docs/fuentes-europa-agro.md §1),
recortando solo el bloque `extension.annotation` (metadatos de difusión que
el parser no usa):

- eurostat_nama_10r_2gdp.json: PIB, 2 unidades x 9 códigos geo x 3 años.
  Incluye a propósito códigos que NO deben guardarse: NUTS1 (`ES4`),
  Extra-Regio (`ESZZ`), región no UE (`NO08`, sin datos, y `TR10`).
- eurostat_rd_e_gerdreg.json: I+D, con flags reales `e` (estimado) y `b`
  (ruptura de serie). La posición 17 (`BES`, ES43, 2024) lleva un flag
  `|C` (confidencial, sin valor) AÑADIDO a mano para probar ese caso: el
  flag es real (visto en ef_lsk_main y nama_10r_3gva), pero no aparece en
  este recorte concreto.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from extremadura_datos.eurostat_parse import (
    clasificar_geo,
    parsear_dataset,
    periodo_desde_time,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _carga(nombre: str) -> dict:
    return json.loads((FIXTURES / nombre).read_text(encoding="utf-8"))


def _por_serie_y_anyo(filas):
    return {(f.serie_codigo_origen, f.anyo): f for f in filas}


def test_clasificar_geo():
    assert clasificar_geo("EU27_2020") == "agregado"
    assert clasificar_geo("ES") == "pais"
    assert clasificar_geo("EL") == "pais"  # Grecia usa EL en Eurostat
    assert clasificar_geo("ES43") == "nuts2"
    assert clasificar_geo("FR10") == "nuts2"
    assert clasificar_geo("ES431") == "provincia"
    assert clasificar_geo("ES432") == "provincia"
    # Descartados
    assert clasificar_geo("ES4") is None  # NUTS1
    assert clasificar_geo("ESZZ") is None  # Extra-Regio
    assert clasificar_geo("FR101") is None  # otros NUTS3
    assert clasificar_geo("NO08") is None  # fuera de la UE-27
    assert clasificar_geo("TR10") is None
    assert clasificar_geo("EA20") is None  # otros agregados
    assert clasificar_geo("EU") is None
    assert clasificar_geo("UK") is None


def test_periodo_desde_time():
    assert periodo_desde_time("2024") == (date(2024, 1, 1), 2024, "A")
    assert periodo_desde_time("2024-Q3") == (date(2024, 7, 1), 2024, "T3")
    assert periodo_desde_time("2024Q1") == (date(2024, 1, 1), 2024, "T1")
    assert periodo_desde_time("2024-05") == (date(2024, 5, 1), 2024, "M05")
    assert periodo_desde_time("2024M11") == (date(2024, 11, 1), 2024, "M11")
    assert periodo_desde_time("2024-S2") == (date(2024, 7, 1), 2024, "S2")
    assert periodo_desde_time("2024-W05") is None


def test_pib_valores_y_territorios_reales():
    filas = parsear_dataset(_carga("eurostat_nama_10r_2gdp.json"), "nama_10r_2gdp")

    territorios = {f.territorio_clave for f in filas}
    assert territorios == {"nuts:EU27_2020", "nuts:EL30", "nuts:ES", "nuts:ES43", "nuts:FR10"}
    # 5 territorios x 2 unidades x 3 años, todos con dato
    assert len(filas) == 30

    idx = _por_serie_y_anyo(filas)
    ext_mio = idx[("nama_10r_2gdp|freq=A.unit=MIO_EUR|ES43", 2024)]
    assert ext_mio.valor == 26583.5
    assert ext_mio.tipo_dato == "provisional"
    assert ext_mio.unidad == "Million euro"
    assert ext_mio.periodo_fecha == date(2024, 1, 1)
    assert ext_mio.periodo_codigo == "A"
    assert ext_mio.territorio_nombre_origen == "Extremadura"
    assert ext_mio.serie_atributos["unit"] == {"nombre": "Million euro", "codigo": "MIO_EUR"}
    assert "geo" not in ext_mio.serie_atributos and "time" not in ext_mio.serie_atributos

    # Valores contrastados con la consulta en vivo del 2026-09-15
    assert idx[("nama_10r_2gdp|freq=A.unit=PPS_EU27_2020_HAB|ES43", 2024)].valor == 28100
    assert idx[("nama_10r_2gdp|freq=A.unit=PPS_EU27_2020_HAB|ES", 2024)].valor == 36400
    assert idx[("nama_10r_2gdp|freq=A.unit=PPS_EU27_2020_HAB|EU27_2020", 2024)].valor == 39900
    # Sin flag → tipo_dato None
    assert idx[("nama_10r_2gdp|freq=A.unit=MIO_EUR|EU27_2020", 2022)].tipo_dato is None
    assert idx[("nama_10r_2gdp|freq=A.unit=MIO_EUR|FR10", 2023)].valor == 829638.3


def test_id_flags_huecos_y_confidencial():
    filas = parsear_dataset(_carga("eurostat_rd_e_gerdreg.json"), "rd_e_gerdreg")
    idx = _por_serie_y_anyo(filas)

    total_ext = "rd_e_gerdreg|freq=A.sectperf=TOTAL.unit=PC_GDP|ES43"
    assert idx[(total_ext, 2022)].valor == 0.67
    assert idx[(total_ext, 2023)].valor == 0.71
    # 2024 no tiene valor ni flag → no genera fila (hueco disperso)
    assert (total_ext, 2024) not in idx

    ue = "rd_e_gerdreg|freq=A.sectperf=TOTAL.unit=PC_GDP|EU27_2020"
    assert idx[(ue, 2023)].valor == 2.26
    assert idx[(ue, 2023)].tipo_dato == "estimated"

    stuttgart_bes = "rd_e_gerdreg|freq=A.sectperf=BES.unit=PC_GDP|DE11"
    assert idx[(stuttgart_bes, 2023)].valor == 6.9
    assert idx[(stuttgart_bes, 2023)].tipo_dato == "break in time series"

    confidencial = idx[("rd_e_gerdreg|freq=A.sectperf=BES.unit=PC_GDP|ES43", 2024)]
    assert confidencial.secreto is True
    assert confidencial.valor is None

    # El nombre de la serie no repite la frecuencia y empieza por el territorio
    assert idx[(total_ext, 2022)].serie_nombre_origen == (
        "Extremadura. All sectors. Percentage of gross domestic product (GDP)"
    )


def test_respuesta_no_jsonstat_no_rompe():
    assert parsear_dataset({"error": [{"status": 413}]}, "x") == []
    assert parsear_dataset([], "x") == []
