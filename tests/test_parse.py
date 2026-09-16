"""Pruebas de parse.py con JSON de ejemplo basado en respuestas REALES del INE.

Los fixtures de abajo reproducen la forma exacta de la respuesta que devuelve
DATOS_TABLA (confirmado contra las tablas 50913 -IPC, CCAA- y 3996 -EPA paro,
provincia- el 2026-08-28, navegando directamente a la API): `Fecha` como
string ISO 8601, `T3_Unidad`/`T3_Escala`/`T3_TipoDato` como strings simples, y
`MetaData` como lista de dimensiones con `T3_Variable`/`Nombre`/`Codigo`. Ver
docs/fuentes-ine.md para el detalle de lo verificado y src/extremadura_datos/parse.py
para la cita completa de un fragmento real.
"""

from __future__ import annotations

from datetime import date

from extremadura_datos.parse import parsear_tabla

# Reproduce el caso que motivó el paso a modelo `serie` (ver sql/001_schema.sql):
# una tabla como el IPC (50913) trae VARIAS series para el MISMO territorio y
# el MISMO periodo (una por rubro/tipo de dato). Si se colapsaran a
# territorio+periodo se perderían todas menos una. Estructura y nombres de
# campo tomados de la serie real IPC256217 (Extremadura, índice general).
EJEMPLO_TABLA_IPC_CCAA = [
    {
        "COD": "IPC300001",
        "Nombre": "Extremadura. Índice general. Variación mensual. ",
        "T3_Unidad": "Porcentaje",
        "T3_Escala": " ",
        "MetaData": [
            {"Id": 1, "T3_Variable": "Tipo de dato", "Nombre": "Variación mensual", "Codigo": "3"},
            {"Id": 2, "T3_Variable": "Rubros", "Nombre": "Índice general", "Codigo": "50"},
            {
                "Id": 9007,
                "T3_Variable": "Comunidades y Ciudades Autónomas",
                "Nombre": "Extremadura",
                "Codigo": "11",
            },
        ],
        "Data": [
            {
                "Fecha": "2025-12-01T00:00:00.000+01:00",
                "T3_TipoDato": "Definitivo",
                "T3_Periodo": "M12",
                "Anyo": 2025,
                "Valor": 0.3,
                "Secreto": False,
            }
        ],
    },
    {
        "COD": "IPC300002",
        "Nombre": "Extremadura. Alimentos y bebidas no alcohólicas. Variación mensual. ",
        "T3_Unidad": "Porcentaje",
        "T3_Escala": " ",
        "MetaData": [
            {"Id": 1, "T3_Variable": "Tipo de dato", "Nombre": "Variación mensual", "Codigo": "3"},
            {"Id": 2, "T3_Variable": "Rubros", "Nombre": "Alimentos y bebidas no alcohólicas", "Codigo": "1"},
            {
                "Id": 9007,
                "T3_Variable": "Comunidades y Ciudades Autónomas",
                "Nombre": "Extremadura",
                "Codigo": "11",
            },
        ],
        "Data": [
            {
                "Fecha": "2025-12-01T00:00:00.000+01:00",
                "T3_TipoDato": "Definitivo",
                "T3_Periodo": "M12",
                "Anyo": 2025,
                "Valor": 1.1,
                "Secreto": False,
            }
        ],
    },
    {
        "COD": "IPC300003",
        "Nombre": "Extremadura. Índice general. Índice. ",
        "T3_Unidad": "Índice",
        "T3_Escala": " ",
        "MetaData": [
            {"Id": 1, "T3_Variable": "Tipo de dato", "Nombre": "Índice", "Codigo": "1"},
            {"Id": 2, "T3_Variable": "Rubros", "Nombre": "Índice general", "Codigo": "50"},
            {
                "Id": 9007,
                "T3_Variable": "Comunidades y Ciudades Autónomas",
                "Nombre": "Extremadura",
                "Codigo": "11",
            },
        ],
        "Data": [
            {
                "Fecha": "2025-12-01T00:00:00.000+01:00",
                "T3_TipoDato": "Definitivo",
                "T3_Periodo": "M12",
                "Anyo": 2025,
                "Valor": 118.4,
                "Secreto": False,
            }
        ],
    },
    # Misma tabla, otra CCAA: debe descartarse al filtrar por Extremadura.
    {
        "COD": "IPC300099",
        "Nombre": "Madrid, Comunidad de. Índice general. Índice. ",
        "T3_Unidad": "Índice",
        "T3_Escala": " ",
        "MetaData": [
            {"Id": 1, "T3_Variable": "Tipo de dato", "Nombre": "Índice", "Codigo": "1"},
            {"Id": 2, "T3_Variable": "Rubros", "Nombre": "Índice general", "Codigo": "50"},
            {
                "Id": 9013,
                "T3_Variable": "Comunidades y Ciudades Autónomas",
                "Nombre": "Madrid, Comunidad de",
                "Codigo": "13",
            },
        ],
        "Data": [
            {
                "Fecha": "2025-12-01T00:00:00.000+01:00",
                "T3_TipoDato": "Definitivo",
                "T3_Periodo": "M12",
                "Anyo": 2025,
                "Valor": 120.9,
                "Secreto": False,
            }
        ],
    },
]


def test_filtra_solo_extremadura():
    filas = parsear_tabla(
        EJEMPLO_TABLA_IPC_CCAA, filtro_territorio=("extremadura",), periodicidad="mensual"
    )
    assert len(filas) == 3
    assert all(f.territorio_clave == "extremadura" for f in filas)


def test_ignora_series_sin_match():
    filas = parsear_tabla(
        EJEMPLO_TABLA_IPC_CCAA, filtro_territorio=("badajoz", "caceres"), periodicidad="mensual"
    )
    assert filas == []


def test_varias_series_mismo_territorio_y_periodo_no_se_pierden():
    filas = parsear_tabla(
        EJEMPLO_TABLA_IPC_CCAA, filtro_territorio=("extremadura",), periodicidad="mensual"
    )
    assert len(filas) == 3
    nombres = {f.serie_nombre_origen for f in filas}
    assert len(nombres) == 3, "cada rubro debe conservarse como una serie distinta"
    codigos = {f.serie_codigo_origen for f in filas}
    assert codigos == {"IPC300001", "IPC300002", "IPC300003"}
    assert all(f.periodo_fecha == filas[0].periodo_fecha for f in filas)
    assert {f.valor for f in filas} == {0.3, 1.1, 118.4}


def test_fecha_iso_se_parsea_bien():
    """Fecha real del INE: string ISO 8601 con offset, no epoch-ms."""
    filas = parsear_tabla(
        EJEMPLO_TABLA_IPC_CCAA, filtro_territorio=("extremadura",), periodicidad="mensual"
    )
    from datetime import date

    assert all(f.periodo_fecha == date(2025, 12, 1) for f in filas)
    assert all(f.anyo == 2025 for f in filas)


def test_usa_periodo_codigo_del_ine_si_viene():
    filas = parsear_tabla(
        EJEMPLO_TABLA_IPC_CCAA, filtro_territorio=("extremadura",), periodicidad="mensual"
    )
    assert all(f.periodo_codigo == "M12" for f in filas)


def test_unidad_tipo_dato_desde_campos_t3():
    filas = parsear_tabla(
        EJEMPLO_TABLA_IPC_CCAA, filtro_territorio=("extremadura",), periodicidad="mensual"
    )
    indice = next(f for f in filas if f.serie_codigo_origen == "IPC300003")
    assert indice.unidad == "Índice"
    assert indice.tipo_dato == "Definitivo"
    assert indice.escala is None  # " " (blanco) se normaliza a None


def test_metadata_no_territorial_se_guarda_como_atributo():
    filas = parsear_tabla(
        EJEMPLO_TABLA_IPC_CCAA, filtro_territorio=("extremadura",), periodicidad="mensual"
    )
    variacion = next(f for f in filas if f.serie_codigo_origen == "IPC300001")
    assert variacion.serie_atributos["Tipo de dato"] == {"nombre": "Variación mensual", "codigo": "3"}
    assert variacion.serie_atributos["Rubros"] == {"nombre": "Índice general", "codigo": "50"}
    # El territorio no se duplica como atributo aparte.
    assert "Comunidades y Ciudades Autónomas" not in variacion.serie_atributos


# Tabla a nivel provincia (EPA, tabla 3996): T3_Variable "Provincias" en vez de
# "Comunidades y Ciudades Autónomas", periodicidad trimestral (T3_Periodo
# tipo "T4"). Estructura tomada de la serie real de Badajoz.
EJEMPLO_TABLA_EPA_PROVINCIA = [
    {
        "COD": "EPA11361",
        "Nombre": "Tasa de actividad. Badajoz. Ambos sexos. Total. ",
        "T3_Unidad": "Tasas",
        "T3_Escala": " ",
        "MetaData": [
            {"Id": 1, "T3_Variable": "Tipo de dato", "Nombre": "Tasa de actividad", "Codigo": "1"},
            {"Id": 2, "T3_Variable": "Provincias", "Nombre": "Badajoz", "Codigo": "06"},
            {"Id": 3, "T3_Variable": "Sexo", "Nombre": "Ambos sexos", "Codigo": "0"},
            {"Id": 4, "T3_Variable": "Nacionalidad", "Nombre": "Total", "Codigo": "0"},
        ],
        "Data": [
            {
                "Fecha": "2023-10-01T00:00:00.000+02:00",
                "T3_TipoDato": "Definitivo",
                "T3_Periodo": "T4",
                "Anyo": 2023,
                "Valor": 56.75,
                "Secreto": False,
            }
        ],
    },
    {
        "COD": "EPA11400",
        "Nombre": "Tasa de actividad. Cáceres. Ambos sexos. Total. ",
        "T3_Unidad": "Tasas",
        "T3_Escala": " ",
        "MetaData": [
            {"Id": 1, "T3_Variable": "Tipo de dato", "Nombre": "Tasa de actividad", "Codigo": "1"},
            {"Id": 2, "T3_Variable": "Provincias", "Nombre": "Cáceres", "Codigo": "10"},
            {"Id": 3, "T3_Variable": "Sexo", "Nombre": "Ambos sexos", "Codigo": "0"},
            {"Id": 4, "T3_Variable": "Nacionalidad", "Nombre": "Total", "Codigo": "0"},
        ],
        "Data": [
            {
                "Fecha": "2023-10-01T00:00:00.000+02:00",
                "T3_TipoDato": "Definitivo",
                "T3_Periodo": "T4",
                "Anyo": 2023,
                "Valor": 54.2,
                "Secreto": False,
            }
        ],
    },
]


def test_provincias_badajoz_y_caceres():
    filas = parsear_tabla(
        EJEMPLO_TABLA_EPA_PROVINCIA,
        filtro_territorio=("badajoz", "caceres"),
        periodicidad="trimestral",
    )
    assert {f.territorio_clave for f in filas} == {"badajoz", "caceres"}
    assert all(f.periodo_codigo == "T4" for f in filas)


def test_provincia_sin_match_se_descarta():
    filas = parsear_tabla(
        EJEMPLO_TABLA_EPA_PROVINCIA, filtro_territorio=("extremadura",), periodicidad="trimestral"
    )
    assert filas == []


# Respaldo: una tabla sin MetaData reconocible debe seguir funcionando por
# subcadena en el nombre (método usado antes de verificar MetaData).
EJEMPLO_TABLA_SIN_METADATA = [
    {
        "Nombre": "Extremadura. Ambos sexos. Todas las edades. Tasa de paro",
        "T3_Unidad": "Porcentaje",
        "Data": [
            {
                "Fecha": "2025-01-01T00:00:00.000+01:00",
                "Anyo": 2025,
                "Valor": 17.42,
                "Secreto": False,
                "T3_TipoDato": "Dato base",
            }
        ],
    },
    {
        "Nombre": "Madrid, Comunidad de. Ambos sexos. Todas las edades. Tasa de paro",
        "T3_Unidad": "Porcentaje",
        "Data": [
            {"Fecha": "2025-01-01T00:00:00.000+01:00", "Anyo": 2025, "Valor": 9.1, "Secreto": False}
        ],
    },
]


def test_respaldo_sin_metadata_usa_subcadena_del_nombre():
    filas = parsear_tabla(
        EJEMPLO_TABLA_SIN_METADATA, filtro_territorio=("extremadura",), periodicidad="trimestral"
    )
    assert len(filas) == 1
    assert filas[0].territorio_clave == "extremadura"
    assert filas[0].valor == 17.42
    assert filas[0].periodo_codigo == "T1"  # no hay T3_Periodo, se deriva de la fecha


# Segunda variante de formato encontrada el 2026-08-28 en las tablas de
# Contabilidad Regional de España (77196 CCAA, 76926 provincia): sin COD, sin
# T3_Unidad/T3_Escala/T3_TipoDato, y cada punto de Data trae NombrePeriodo
# ("2024(A)", "2023(P)") en vez de Fecha/Anyo/T3_Periodo. Estructura tomada
# de series reales de esas dos tablas.
EJEMPLO_TABLA_CRE_CCAA = [
    {
        "Nombre": "Extremadura, A. Agricultura, ganadería, silvicultura y pesca, Valor",
        "MetaData": [
            {"T3_Variable": "Comunidades y Ciudades Autónomas", "Nombre": "Extremadura", "Codigo": "11"},
            {"T3_Variable": "ramas de actividad", "Nombre": "A. Agricultura, ganadería, silvicultura y pesca", "Codigo": "aagricultura"},
            {"T3_Variable": "magnitud", "Nombre": "Valor", "Codigo": "valor"},
        ],
        "Data": [{"NombrePeriodo": "2024(A)", "Valor": 2175719.0}],
    },
    {
        "Nombre": "Extremadura, A. Agricultura, ganadería, silvicultura y pesca, Tasas de variación interanuales",
        "MetaData": [
            {"T3_Variable": "Comunidades y Ciudades Autónomas", "Nombre": "Extremadura", "Codigo": "11"},
            {"T3_Variable": "ramas de actividad", "Nombre": "A. Agricultura, ganadería, silvicultura y pesca", "Codigo": "aagricultura"},
            {"T3_Variable": "magnitud", "Nombre": "Tasas de variación interanuales", "Codigo": "tasas"},
        ],
        "Data": [{"NombrePeriodo": "2024(A)", "Valor": 17.7}],
    },
    {
        "Nombre": "Madrid, Comunidad de, A. Agricultura, ganadería, silvicultura y pesca, Valor",
        "MetaData": [
            {"T3_Variable": "Comunidades y Ciudades Autónomas", "Nombre": "Madrid, Comunidad de", "Codigo": "13"},
            {"T3_Variable": "ramas de actividad", "Nombre": "A. Agricultura, ganadería, silvicultura y pesca", "Codigo": "aagricultura"},
            {"T3_Variable": "magnitud", "Nombre": "Valor", "Codigo": "valor"},
        ],
        "Data": [{"NombrePeriodo": "2024(A)", "Valor": 999.0}],
    },
]


def test_formato_nombreperiodo_sin_fecha_ni_cod():
    filas = parsear_tabla(
        EJEMPLO_TABLA_CRE_CCAA, filtro_territorio=("extremadura",), periodicidad="anual"
    )
    assert len(filas) == 2  # las dos magnitudes de Extremadura; Madrid se descarta
    assert all(f.territorio_clave == "extremadura" for f in filas)
    assert all(f.serie_codigo_origen is None for f in filas)  # esta tabla no da COD
    valor_absoluto = next(f for f in filas if f.valor == 2175719.0)
    assert valor_absoluto.periodo_fecha == date(2024, 1, 1)
    assert valor_absoluto.anyo == 2024
    assert valor_absoluto.periodo_codigo == "A"
    assert valor_absoluto.tipo_dato == "A"  # la letra entre parentesis de NombrePeriodo
    assert valor_absoluto.serie_atributos["magnitud"] == {"nombre": "Valor", "codigo": "valor"}
    # nombre_origen difiere entre las dos series (magnitud va en el nombre),
    # asi que no colisionan aunque no haya COD.
    nombres = {f.serie_nombre_origen for f in filas}
    assert len(nombres) == 2


def test_formato_nombreperiodo_letra_no_es_siempre_a():
    """La tabla provincial (76926) usa NombrePeriodo tipo '2023(P)', no '(A)'."""
    tabla = [
        {
            "Nombre": "Badajoz, A. Agricultura, ganadería, silvicultura y pesca",
            "MetaData": [
                {"T3_Variable": "Provincias", "Nombre": "Badajoz", "Codigo": "06"},
                {"T3_Variable": "ramas de actividad", "Nombre": "A. Agricultura...", "Codigo": "aagricultura"},
            ],
            "Data": [{"NombrePeriodo": "2023(P)", "Valor": 1022573.0}],
        },
    ]
    filas = parsear_tabla(tabla, filtro_territorio=("badajoz", "caceres"), periodicidad="anual")
    assert len(filas) == 1
    assert filas[0].periodo_fecha == date(2023, 1, 1)
    assert filas[0].periodo_codigo == "A"
    assert filas[0].tipo_dato == "P"


def test_formato_nombreperiodo_anyo_sin_letra():
    """2026-09-16: en la ingesta incremental real, las tablas CRE traen los
    años consolidados como '2022' a secas (sin '(A)'/'(P)')."""
    from extremadura_datos.parse import _fecha_desde_nombre_periodo

    assert _fecha_desde_nombre_periodo("2022") == (date(2022, 1, 1), 2022, "A", None)
    assert _fecha_desde_nombre_periodo("2023(P)") == (date(2023, 1, 1), 2023, "A", "P")
