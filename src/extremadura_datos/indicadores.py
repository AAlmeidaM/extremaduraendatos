"""Catálogo declarativo de indicadores a ingerir.

Añadir un indicador nuevo = añadir una entrada aquí (y, si es de una fuente
nueva, dar de alta esa fuente en la base — ver sql/001_schema.sql). No hace
falta tocar ingest.py, parse.py ni db.py: el motor es genérico y funciona
igual para cualquier tabla del INE, tenga una serie por territorio o cientos
(rubro x tipo de dato x territorio...) — ver `serie` en sql/001_schema.sql.

Catálogo actual: las 21 tablas de `Datos_Extremadura_Mensual.xlsx` (aportado
por el usuario el 2026-08-28 — categorías Precios, Industria y Empresa,
Turismo, Vivienda y Empleo) más 3 que ya estaban del bloque de Economía /
Mercado laboral (ver docs/fuentes-ine.md para el detalle y los enlaces de
cada tabla, y el porqué de cada elección), más 2 tablas de Demografía
(población por CCAA/provincia, añadidas el mismo día para poder normalizar
por habitante — ver la nota junto a esas dos entradas más abajo).

Nota sobre `ine_epa_paro_provincia`: sustituye a la tabla 72989 que se usó en
la primera versión de este proyecto (mismo concepto — tasas de paro/actividad
por provincia — pero el Excel del usuario especifica la tabla 3996; se
adopta esa por ser la fuente autorizada).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Territorios tal cual los espera parse.py (ver db.TERRITORIO_CLAVE_A_NOMBRE).
# Se reutiliza para no repetir la tupla en cada entrada.
#
# _CCAA / _CCAA_Y_PROVINCIA (uso original, solo Extremadura): quedan para los
# 4 indicadores de ámbito exclusivamente provincial que no se han ampliado
# (ver docs/fuentes-ine.md, no piden desglose por CCAA a la API del INE).
_CCAA = ("extremadura",)
_PROVINCIA = ("badajoz", "caceres")
_CCAA_Y_PROVINCIA = ("extremadura", "badajoz", "caceres")

# _TODAS_CCAA / _TODAS_CCAA_Y_PROVINCIA (2026-08-28): las 19 Comunidades y
# Ciudades Autónomas + las dos etiquetas nacionales que usa el INE ("Nacional"
# / "Total Nacional", según la tabla) + Extremadura. Se usan en los 19
# indicadores de ámbito CCAA para poder comparar Extremadura con el resto de
# España (objetivo del proyecto: web de análisis actualizada a diario, ver
# PROJECT.md §3 y §17) sin tener que volver a pedirle el dato nacional a la
# API en cada consulta. Los nombres deben coincidir EXACTOS (normalizados: sin
# acentos, minúsculas) con lo que trae `MetaData` del INE — verificado contra
# datos reales de 7 tablas el 2026-08-28 (ver docs/fuentes-ine.md); si el INE
# usa otra grafía en alguna tabla nueva, añadirla aquí y en
# db.TERRITORIO_CLAVE_A_NOMBRE (los dos sitios van siempre juntos).
_TODAS_CCAA = (
    "andalucia", "aragon", "asturias, principado de", "balears, illes",
    "canarias", "cantabria", "castilla - la mancha", "castilla y leon",
    "cataluna", "ceuta", "comunitat valenciana", "extremadura", "galicia",
    "madrid, comunidad de", "melilla", "murcia, region de",
    "navarra, comunidad foral de", "pais vasco", "rioja, la",
    "nacional", "total nacional",
)
_TODAS_CCAA_Y_PROVINCIA = _TODAS_CCAA + ("badajoz", "caceres")


@dataclass(frozen=True)
class Indicador:
    codigo: str  # slug interno, único
    tabla_id_externo: str  # id de tabla en la fuente (INE)
    nombre: str
    categoria: str
    # 'ccaa' | 'provincia' | 'ccaa_y_provincia' — documental; el filtrado real
    # lo hace filtro_territorio.
    nivel_territorial: str
    periodicidad: str  # 'trimestral' | 'anual' | 'mensual'
    # Subcadenas (sin acentos, en minúsculas) que deben aparecer en el nombre
    # de la serie del INE para quedarse con esa fila. Ver parse.py:_normaliza.
    filtro_territorio: tuple[str, ...] = field(default_factory=tuple)
    activo: bool = True
    # ine_operacion_id / ine_publicacion_id (2026-08-28): identifican la
    # "operación" y "publicación" del INE a las que pertenece esta tabla —
    # hace falta para consultar su calendario oficial de publicaciones
    # (PUBLICACIONES_OPERACION / PUBLICACIONFECHA_PUBLICACION) y así poder
    # gobernar la ingesta diaria (ver calendario.py y PROJECT.md §17: esto
    # sustituye a la decisión anterior de "llamar siempre, el upsert es
    # idempotente"). Se sacan de SERIES_TABLA/{tabla_id_externo}, que ya trae
    # FK_Operacion y FK_Publicacion en cada serie — no hizo falta ningún
    # rodeo por SERIE/{id}?det=2 (que no devuelve esos campos). Verificado
    # contra la API real el 2026-08-28 para las 24 tablas del catálogo.
    # ine_publicacion_id=None en ine_cre_provincia/ine_cre_ccaa porque esas
    # tablas usan el formato "CRE" de SERIES_TABLA (sin COD/FK_Publicacion en
    # cada serie, ver parse.py) — calendario.py lo autodescubre en tiempo de
    # ejecución vía PUBLICACIONES_OPERACION y lo guarda en la base.
    ine_operacion_id: int | None = None
    ine_publicacion_id: int | None = None
    # naturaleza_dato (2026-08-28): la naturaleza estadística *por defecto* de
    # esta tabla — 'indice' (base 100 en un año, IPC/IPI/ICN/IPV/confianza),
    # 'tasa' (porcentaje, EPA/paro), 'conteo' (recuento absoluto: viviendas,
    # sociedades, pernoctaciones...), 'monetario' (importe: coste laboral,
    # PIB/VAB, gasto turístico) o 'promedio' (media continua: estancia media,
    # tiempo de trabajo). Sirve para no mezclar naturalezas al analizar (ver
    # v_analisis en sql/001_schema.sql) y para decidir cuándo tiene sentido
    # normalizar por población (solo 'conteo'). Es solo el valor *por
    # defecto* de la tabla: dentro de una misma tabla puede haber series de
    # otra naturaleza (p.ej. IPC trae tanto el índice como su variación
    # mensual/anual, que SÍ es una tasa) — v_analisis corrige esos casos
    # mirando el `tipo_dato` real de cada observación, no este campo a solas.
    naturaleza_dato: str | None = None
    # fuente (2026-09-15): código de la tabla `fuente` ('ine' | 'eurostat').
    # Decide qué cliente/parser usa ingest.py.
    fuente: str = "ine"
    # eurostat_filtros (solo fuente='eurostat'): filtros de dimensión que se
    # mandan a la API, como tupla de (dimensión, (códigos...)). No se filtra
    # `geo` (se pide Europa entera y eurostat_parse.clasificar_geo decide qué
    # territorios se guardan) ni `time`. Imprescindible para no superar el
    # límite de 5M celdas de Eurostat (HTTP 413) — ver
    # docs/fuentes-europa-agro.md §1.
    eurostat_filtros: tuple[tuple[str, tuple[str, ...]], ...] = ()


INDICADORES: list[Indicador] = [
    # --- Precios ---------------------------------------------------------
    Indicador(
        codigo="ine_ipc_ccaa",
        tabla_id_externo="50913",
        nombre="IPC Base 2021",
        categoria="precios",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_TODAS_CCAA,
        ine_operacion_id=25,
        ine_publicacion_id=8,
        naturaleza_dato="indice",
    ),
    # --- Industria y Empresa ----------------------------------------------
    Indicador(
        codigo="ine_soc_mercantiles_resumen_ccaa",
        tabla_id_externo="13912",
        nombre="Resumen de sociedades mercantiles",
        categoria="industria_empresa",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_TODAS_CCAA,
        ine_operacion_id=125,
        ine_publicacion_id=24,
        naturaleza_dato="conteo",
    ),
    Indicador(
        codigo="ine_soc_mercantiles_constituidas_ccaa",
        tabla_id_externo="13913",
        nombre="Sociedades mercantiles constituidas",
        categoria="industria_empresa",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_TODAS_CCAA,
        ine_operacion_id=125,
        ine_publicacion_id=24,
        naturaleza_dato="conteo",
    ),
    Indicador(
        codigo="ine_soc_mercantiles_disueltas_provincia",
        tabla_id_externo="13923",
        nombre="Sociedades mercantiles disueltas",
        categoria="industria_empresa",
        nivel_territorial="provincia",
        periodicidad="mensual",
        filtro_territorio=_PROVINCIA,
        ine_operacion_id=125,
        ine_publicacion_id=24,
        naturaleza_dato="conteo",
    ),
    Indicador(
        codigo="ine_ipi_ccaa",
        tabla_id_externo="26061",
        nombre="Índice de Producción Industrial (Base 2015)",
        categoria="industria_empresa",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_TODAS_CCAA,
        ine_operacion_id=26,
        ine_publicacion_id=10,
        naturaleza_dato="indice",
    ),
    Indicador(
        codigo="ine_icn_industria_ccaa",
        tabla_id_externo="26002",
        nombre="Índices de cifras de negocios en la industria (Base 2015)",
        categoria="industria_empresa",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_TODAS_CCAA,
        ine_operacion_id=42,
        ine_publicacion_id=6,
        naturaleza_dato="indice",
    ),
    Indicador(
        codigo="ine_icn_comercio_menor_ccaa",
        tabla_id_externo="25992",
        nombre="Índice de cifra de negocios comercio al por menor (Precios Constantes)",
        categoria="industria_empresa",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_TODAS_CCAA,
        ine_operacion_id=32,
        ine_publicacion_id=5,
        naturaleza_dato="indice",
    ),
    Indicador(
        codigo="ine_confianza_empresarial_ccaa",
        tabla_id_externo="8027",
        nombre="Situación, expectativas e índice de confianza",
        categoria="industria_empresa",
        nivel_territorial="ccaa",
        periodicidad="trimestral",
        filtro_territorio=_TODAS_CCAA,
        ine_operacion_id=163,
        ine_publicacion_id=61,
        naturaleza_dato="indice",
    ),
    # --- Turismo -----------------------------------------------------------
    Indicador(
        codigo="ine_turismo_viajeros_alojamiento_ccaa",
        tabla_id_externo="2941",
        nombre="Viajeros, pernoctaciones por tipo de alojamiento",
        categoria="turismo",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_TODAS_CCAA,
        ine_operacion_id=238,
        ine_publicacion_id=1,
        naturaleza_dato="conteo",
    ),
    Indicador(
        codigo="ine_turismo_viajeros_pernoctaciones_ccaa",
        tabla_id_externo="2074",
        nombre="Viajeros y pernoctaciones totales",
        categoria="turismo",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_TODAS_CCAA,
        ine_operacion_id=238,
        ine_publicacion_id=1,
        naturaleza_dato="conteo",
    ),
    Indicador(
        codigo="ine_turismo_establecimientos_ccaa",
        tabla_id_externo="2942",
        nombre="Establecimientos, plazas y personal empleado por tipo de alojamiento",
        categoria="turismo",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_TODAS_CCAA,
        ine_operacion_id=238,
        ine_publicacion_id=1,
        naturaleza_dato="conteo",
    ),
    Indicador(
        codigo="ine_turismo_estancia_media_ccaa",
        tabla_id_externo="2940",
        nombre="Estancia media, por tipo de alojamiento",
        categoria="turismo",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_TODAS_CCAA,
        ine_operacion_id=238,
        ine_publicacion_id=1,
        naturaleza_dato="promedio",
    ),
    Indicador(
        # Desactivada: verificado contra la API real el 2026-08-28 (tabla
        # 10839, EGATUR) — esta tabla del INE solo desglosa por CCAA las seis
        # comunidades con más turismo internacional (Andalucía, Baleares,
        # Canarias, Cataluña, C. Valenciana, Madrid); el resto, incluida
        # Extremadura, va agregado en "Otras Comunidades Autónomas", sin
        # desglose propio. No es un fallo de parseo ni un id incorrecto: el
        # INE no publica el dato para Extremadura en esta tabla. Se deja
        # activo=False para no ingerir en vano cada día — ver
        # docs/fuentes-ine.md.
        codigo="ine_turismo_gasto_turistas_ccaa",
        tabla_id_externo="10839",
        nombre="Gasto de los turistas internacionales",
        categoria="turismo",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_TODAS_CCAA,
        activo=False,
        ine_operacion_id=329,
        ine_publicacion_id=408,
        naturaleza_dato="monetario",
    ),
    # --- Vivienda ------------------------------------------------------------
    Indicador(
        codigo="ine_hipotecas_provincia",
        tabla_id_externo="3204",
        nombre="Hipotecas constituidas sobre fincas urbanas por entidad que concede el préstamo",
        categoria="vivienda",
        nivel_territorial="provincia",
        periodicidad="mensual",
        filtro_territorio=_PROVINCIA,
        ine_operacion_id=40,
        ine_publicacion_id=3,
        naturaleza_dato="conteo",
    ),
    Indicador(
        codigo="ine_compraventa_vivienda_ccaa_provincia",
        tabla_id_externo="6150",
        nombre="Compraventa de viviendas según régimen y estado",
        categoria="vivienda",
        nivel_territorial="ccaa_y_provincia",
        periodicidad="mensual",
        filtro_territorio=_TODAS_CCAA_Y_PROVINCIA,
        ine_operacion_id=7,
        ine_publicacion_id=28,
        naturaleza_dato="conteo",
    ),
    Indicador(
        codigo="ine_viviendas_transmitidas_ccaa_provincia",
        tabla_id_externo="6149",
        nombre="Viviendas transmitidas según título de adquisición",
        categoria="vivienda",
        nivel_territorial="ccaa_y_provincia",
        periodicidad="mensual",
        filtro_territorio=_TODAS_CCAA_Y_PROVINCIA,
        ine_operacion_id=7,
        ine_publicacion_id=28,
        naturaleza_dato="conteo",
    ),
    Indicador(
        codigo="ine_ipv_ccaa",
        tabla_id_externo="25171",
        nombre="Índice de Precios de Vivienda (IPV). Base 2015",
        categoria="vivienda",
        nivel_territorial="ccaa",
        periodicidad="trimestral",
        filtro_territorio=_TODAS_CCAA,
        ine_operacion_id=15,
        ine_publicacion_id=21,
        naturaleza_dato="indice",
    ),
    Indicador(
        codigo="ine_fincas_rusticas_ccaa_provincia",
        tabla_id_externo="6147",
        nombre="Total fincas rústicas transmitidas según título de adquisición",
        categoria="vivienda",
        nivel_territorial="ccaa_y_provincia",
        periodicidad="mensual",
        filtro_territorio=_TODAS_CCAA_Y_PROVINCIA,
        ine_operacion_id=7,
        ine_publicacion_id=28,
        naturaleza_dato="conteo",
    ),
    # --- Empleo ------------------------------------------------------------
    Indicador(
        codigo="ine_coste_laboral_ccaa",
        tabla_id_externo="6062",
        nombre="Coste laboral por hora efectiva, CCAA, sectores de actividad",
        categoria="empleo",
        nivel_territorial="ccaa",
        periodicidad="trimestral",
        filtro_territorio=_TODAS_CCAA,
        ine_operacion_id=303,
        ine_publicacion_id=360,
        naturaleza_dato="monetario",
    ),
    Indicador(
        codigo="ine_tiempo_trabajo_ccaa",
        tabla_id_externo="6063",
        nombre="Tiempo de trabajo por trabajador y mes, CCAA, tipo de jornada, sectores de actividad",
        categoria="empleo",
        nivel_territorial="ccaa",
        periodicidad="trimestral",
        filtro_territorio=_TODAS_CCAA,
        ine_operacion_id=303,
        ine_publicacion_id=360,
        naturaleza_dato="promedio",
    ),
    Indicador(
        codigo="ine_epa_paro_provincia",
        tabla_id_externo="3996",
        nombre="Tasas de actividad, paro y empleo por provincia y sexo (EPA)",
        categoria="empleo",
        nivel_territorial="provincia",
        periodicidad="trimestral",
        filtro_territorio=_PROVINCIA,
        ine_operacion_id=293,
        ine_publicacion_id=330,
        naturaleza_dato="tasa",
    ),
    # --- Ya existían (no vienen del Excel, se mantienen) ------------------
    Indicador(
        codigo="ine_epa_ccaa",
        tabla_id_externo="75803",
        nombre="Tasas de paro por grupos de edad, sexo y comunidad autónoma (EPA)",
        categoria="mercado_laboral",
        nivel_territorial="ccaa",
        periodicidad="trimestral",
        filtro_territorio=_TODAS_CCAA,
        ine_operacion_id=293,
        ine_publicacion_id=330,
        naturaleza_dato="tasa",
    ),
    Indicador(
        codigo="ine_cre_provincia",
        # 72946 (id original de esta entrada) da 404 en DATOS_TABLA -- no es
        # un id de tabla de Tempus3 (parece ser solo el identificador interno
        # de datos.gob.es, que no siempre coincide con el id real de INE).
        # Corregido a 76926 tras localizarlo navegando la operación real del
        # INE (Contabilidad Regional de España > Resultados > Enfoque
        # funcional > provincias > Tablas PC-Axis) y verificarlo contra la
        # API real el 2026-08-28 — ver docs/fuentes-ine.md.
        tabla_id_externo="76926",
        nombre="PIB pm y VAB por ramas de actividad, precios corrientes, por provincia (CRE)",
        categoria="economia",
        nivel_territorial="provincia",
        periodicidad="anual",
        filtro_territorio=_PROVINCIA,
        ine_operacion_id=257,
        # ine_publicacion_id: ver nota junto a la clase Indicador -- se
        # autodescubre en tiempo de ejecución (calendario.py).
        naturaleza_dato="monetario",
    ),
    Indicador(
        codigo="ine_cre_ccaa",
        tabla_id_externo="77196",
        nombre="PIB pm y VAB por ramas de actividad, precios corrientes, por CCAA (CRE)",
        categoria="economia",
        nivel_territorial="ccaa",
        periodicidad="anual",
        filtro_territorio=_TODAS_CCAA,
        ine_operacion_id=257,
        # ine_publicacion_id: ver nota junto a la clase Indicador -- se
        # autodescubre en tiempo de ejecución (calendario.py).
        naturaleza_dato="monetario",
    ),
    # --- Demografía (2026-08-28) ------------------------------------------
    # Población por CCAA/provincia y sexo — "Cifras Oficiales de Población
    # (Revisión del Padrón municipal)", serie DPOP del INE. Se añade para
    # poder normalizar por habitante los indicadores de tipo 'conteo'
    # (sociedades, viviendas, pernoctaciones...) al compararlos entre
    # territorios de tamaño muy distinto (ver v_analisis en
    # sql/001_schema.sql). Tablas localizadas vía datos.gob.es (no vía la API
    # del INE directamente, sin acceso de red desde este entorno) — id de
    # tabla y alcance confirmados (2853 = CCAA+ciudades autónomas, anual,
    # 1996 en adelante; 2852 = provincias, misma serie), pero la FORMA exacta
    # de la respuesta (nombre de la dimensión "Sexo", etiqueta para "ambos
    # sexos") NO se ha verificado aún contra la API real -- pendiente de
    # confirmar en la primera ingesta real (motor genérico: si el parseo
    # fallara, se registraría en carga_log con 0 filas, sin romper el resto
    # de la ingesta). ine_operacion_id se deja sin rellenar a propósito hasta
    # confirmarlo: sin él, calendario.py simplemente ingiere siempre este
    # indicador (dato anual, coste insignificante).
    Indicador(
        codigo="ine_poblacion_ccaa",
        tabla_id_externo="2853",
        nombre="Población por comunidades y ciudades autónomas y sexo",
        categoria="demografia",
        nivel_territorial="ccaa",
        periodicidad="anual",
        filtro_territorio=_TODAS_CCAA,
        naturaleza_dato="conteo",
    ),
    Indicador(
        codigo="ine_poblacion_provincia",
        tabla_id_externo="2852",
        nombre="Población por provincias y sexo",
        categoria="demografia",
        nivel_territorial="provincia",
        periodicidad="anual",
        filtro_territorio=_PROVINCIA,
        naturaleza_dato="conteo",
    ),
    # =====================================================================
    # --- Eurostat: comparativa NUTS2 europea (2026-09-15) -----------------
    # =====================================================================
    # Fase 1 de docs/ampliacion-nuts2-agro.md. Todos anuales. Se descarga
    # Europa entera; se guardan la UE-27 (agregado), los 27 países, todas sus
    # NUTS2 y Badajoz/Cáceres (NUTS3) — ver eurostat_parse.clasificar_geo.
    # Filtros y tamaño de cada petición verificados contra la API real el
    # 2026-09-15 (todos < 9 MB, ningún 413; detalle en
    # docs/fuentes-europa-agro.md §1). Las CCAA españolas son NUTS2, así que
    # estos datos caen en los MISMOS territorios que los del INE (enlazados
    # por territorio.codigo_nuts).
    Indicador(
        codigo="eurostat_pib_nuts2",
        tabla_id_externo="nama_10r_2gdp",
        nombre="PIB regional a precios corrientes (NUTS2)",
        categoria="economia",
        nivel_territorial="nuts2",
        periodicidad="anual",
        naturaleza_dato="monetario",
        fuente="eurostat",
        eurostat_filtros=(("unit", ("MIO_EUR", "EUR_HAB", "PPS_EU27_2020_HAB")),),
    ),
    Indicador(
        codigo="eurostat_vab_ramas_nuts2",
        tabla_id_externo="nama_10r_3gva",
        nombre="VAB a precios básicos por ramas de actividad (NUTS2)",
        categoria="economia",
        nivel_territorial="nuts2",
        periodicidad="anual",
        naturaleza_dato="monetario",
        fuente="eurostat",
        eurostat_filtros=(("unit", ("CP_MEUR",)),),
    ),
    Indicador(
        codigo="eurostat_paro_nuts2",
        tabla_id_externo="lfst_r_lfu3rt",
        nombre="Tasa de paro por sexo y edad (NUTS2)",
        categoria="empleo",
        nivel_territorial="nuts2",
        periodicidad="anual",
        naturaleza_dato="tasa",
        fuente="eurostat",
        eurostat_filtros=(
            ("isced11", ("TOTAL",)),
            ("sex", ("T", "M", "F")),
            ("age", ("Y15-74", "Y15-24")),
        ),
    ),
    Indicador(
        codigo="eurostat_empleo_nuts2",
        tabla_id_externo="lfst_r_lfe2emprt",
        nombre="Tasa de empleo 20-64 años por sexo (NUTS2)",
        categoria="empleo",
        nivel_territorial="nuts2",
        periodicidad="anual",
        naturaleza_dato="tasa",
        fuente="eurostat",
        eurostat_filtros=(("sex", ("T", "M", "F")), ("age", ("Y20-64",))),
    ),
    Indicador(
        codigo="eurostat_ocupados_ramas_nuts2",
        tabla_id_externo="lfst_r_lfe2en2",
        nombre="Ocupados por rama de actividad, miles (NUTS2)",
        categoria="empleo",
        nivel_territorial="nuts2",
        periodicidad="anual",
        naturaleza_dato="conteo",
        fuente="eurostat",
        eurostat_filtros=(("sex", ("T",)), ("age", ("Y15-74",))),
    ),
    Indicador(
        codigo="eurostat_id_nuts2",
        tabla_id_externo="rd_e_gerdreg",
        nombre="Gasto en I+D por sector de ejecución (NUTS2)",
        categoria="innovacion",
        nivel_territorial="nuts2",
        periodicidad="anual",
        # Mezcla % del PIB y €/habitante: la naturaleza por defecto es la
        # tasa; distinguir por serie_atributos->'unit' al analizar.
        naturaleza_dato="tasa",
        fuente="eurostat",
        eurostat_filtros=(("unit", ("PC_GDP", "EUR_HAB")),),
    ),
    Indicador(
        codigo="eurostat_poblacion_nuts2",
        tabla_id_externo="demo_r_d2jan",
        nombre="Población a 1 de enero (NUTS2)",
        categoria="demografia",
        nivel_territorial="nuts2",
        periodicidad="anual",
        naturaleza_dato="conteo",
        fuente="eurostat",
        eurostat_filtros=(("sex", ("T",)), ("age", ("TOTAL",))),
    ),
    Indicador(
        codigo="eurostat_renta_hogares_nuts2",
        tabla_id_externo="nama_10r_2hhinc",
        nombre="Renta disponible neta de los hogares (NUTS2)",
        categoria="economia",
        nivel_territorial="nuts2",
        periodicidad="anual",
        naturaleza_dato="monetario",
        fuente="eurostat",
        eurostat_filtros=(
            ("unit", ("PPS_EU27_2020_HAB", "EUR_HAB")),
            ("na_item", ("B6N",)),
            ("direct", ("BAL",)),
        ),
    ),
    Indicador(
        codigo="eurostat_ganaderia_nuts2",
        tabla_id_externo="ef_lsk_main",
        nombre="Cabaña ganadera por especie (NUTS2, encuesta de estructuras agrarias)",
        categoria="agrario",
        nivel_territorial="nuts2",
        periodicidad="anual",
        naturaleza_dato="conteo",
        fuente="eurostat",
        eurostat_filtros=(
            ("farmtype", ("TOTAL",)),
            ("so_eur", ("TOTAL",)),
            ("uaarea", ("TOTAL",)),
            ("lsu", ("TOTAL",)),
            ("statinfo", ("TOTAL",)),
            ("unit", ("LSU", "HD")),
        ),
    ),
]


def _validar_catalogo() -> None:
    codigos = [i.codigo for i in INDICADORES]
    tablas = [(i.fuente, i.tabla_id_externo) for i in INDICADORES]
    duplicados_codigo = {c for c in codigos if codigos.count(c) > 1}
    duplicados_tabla = {t for t in tablas if tablas.count(t) > 1}
    if duplicados_codigo:
        raise ValueError(f"Códigos de indicador duplicados en indicadores.py: {duplicados_codigo}")
    if duplicados_tabla:
        raise ValueError(f"Tablas duplicadas (fuente, tabla) en indicadores.py: {duplicados_tabla}")
    fuentes_validas = {"ine", "eurostat"}
    desconocidas = {i.fuente for i in INDICADORES} - fuentes_validas
    if desconocidas:
        raise ValueError(f"Fuentes desconocidas en indicadores.py: {desconocidas}")


_validar_catalogo()
