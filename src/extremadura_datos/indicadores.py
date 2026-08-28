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
cada tabla, y el porqué de cada elección).

Nota sobre `ine_epa_paro_provincia`: sustituye a la tabla 72989 que se usó en
la primera versión de este proyecto (mismo concepto — tasas de paro/actividad
por provincia — pero el Excel del usuario especifica la tabla 3996; se
adopta esa por ser la fuente autorizada).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Territorios de Extremadura, tal cual los espera parse.py (ver
# db.TERRITORIO_CLAVE_A_NOMBRE). Se reutiliza para no repetir la tupla en
# cada entrada.
_CCAA = ("extremadura",)
_PROVINCIA = ("badajoz", "caceres")
_CCAA_Y_PROVINCIA = ("extremadura", "badajoz", "caceres")


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


INDICADORES: list[Indicador] = [
    # --- Precios ---------------------------------------------------------
    Indicador(
        codigo="ine_ipc_ccaa",
        tabla_id_externo="50913",
        nombre="IPC Base 2021",
        categoria="precios",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_CCAA,
    ),
    # --- Industria y Empresa ----------------------------------------------
    Indicador(
        codigo="ine_soc_mercantiles_resumen_ccaa",
        tabla_id_externo="13912",
        nombre="Resumen de sociedades mercantiles",
        categoria="industria_empresa",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_CCAA,
    ),
    Indicador(
        codigo="ine_soc_mercantiles_constituidas_ccaa",
        tabla_id_externo="13913",
        nombre="Sociedades mercantiles constituidas",
        categoria="industria_empresa",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_CCAA,
    ),
    Indicador(
        codigo="ine_soc_mercantiles_disueltas_provincia",
        tabla_id_externo="13923",
        nombre="Sociedades mercantiles disueltas",
        categoria="industria_empresa",
        nivel_territorial="provincia",
        periodicidad="mensual",
        filtro_territorio=_PROVINCIA,
    ),
    Indicador(
        codigo="ine_ipi_ccaa",
        tabla_id_externo="26061",
        nombre="Índice de Producción Industrial (Base 2015)",
        categoria="industria_empresa",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_CCAA,
    ),
    Indicador(
        codigo="ine_icn_industria_ccaa",
        tabla_id_externo="26002",
        nombre="Índices de cifras de negocios en la industria (Base 2015)",
        categoria="industria_empresa",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_CCAA,
    ),
    Indicador(
        codigo="ine_icn_comercio_menor_ccaa",
        tabla_id_externo="25992",
        nombre="Índice de cifra de negocios comercio al por menor (Precios Constantes)",
        categoria="industria_empresa",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_CCAA,
    ),
    Indicador(
        codigo="ine_confianza_empresarial_ccaa",
        tabla_id_externo="8027",
        nombre="Situación, expectativas e índice de confianza",
        categoria="industria_empresa",
        nivel_territorial="ccaa",
        periodicidad="trimestral",
        filtro_territorio=_CCAA,
    ),
    # --- Turismo -----------------------------------------------------------
    Indicador(
        codigo="ine_turismo_viajeros_alojamiento_ccaa",
        tabla_id_externo="2941",
        nombre="Viajeros, pernoctaciones por tipo de alojamiento",
        categoria="turismo",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_CCAA,
    ),
    Indicador(
        codigo="ine_turismo_viajeros_pernoctaciones_ccaa",
        tabla_id_externo="2074",
        nombre="Viajeros y pernoctaciones totales",
        categoria="turismo",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_CCAA,
    ),
    Indicador(
        codigo="ine_turismo_establecimientos_ccaa",
        tabla_id_externo="2942",
        nombre="Establecimientos, plazas y personal empleado por tipo de alojamiento",
        categoria="turismo",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_CCAA,
    ),
    Indicador(
        codigo="ine_turismo_estancia_media_ccaa",
        tabla_id_externo="2940",
        nombre="Estancia media, por tipo de alojamiento",
        categoria="turismo",
        nivel_territorial="ccaa",
        periodicidad="mensual",
        filtro_territorio=_CCAA,
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
        filtro_territorio=_CCAA,
        activo=False,
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
    ),
    Indicador(
        codigo="ine_compraventa_vivienda_ccaa_provincia",
        tabla_id_externo="6150",
        nombre="Compraventa de viviendas según régimen y estado",
        categoria="vivienda",
        nivel_territorial="ccaa_y_provincia",
        periodicidad="mensual",
        filtro_territorio=_CCAA_Y_PROVINCIA,
    ),
    Indicador(
        codigo="ine_viviendas_transmitidas_ccaa_provincia",
        tabla_id_externo="6149",
        nombre="Viviendas transmitidas según título de adquisición",
        categoria="vivienda",
        nivel_territorial="ccaa_y_provincia",
        periodicidad="mensual",
        filtro_territorio=_CCAA_Y_PROVINCIA,
    ),
    Indicador(
        codigo="ine_ipv_ccaa",
        tabla_id_externo="25171",
        nombre="Índice de Precios de Vivienda (IPV). Base 2015",
        categoria="vivienda",
        nivel_territorial="ccaa",
        periodicidad="trimestral",
        filtro_territorio=_CCAA,
    ),
    Indicador(
        codigo="ine_fincas_rusticas_ccaa_provincia",
        tabla_id_externo="6147",
        nombre="Total fincas rústicas transmitidas según título de adquisición",
        categoria="vivienda",
        nivel_territorial="ccaa_y_provincia",
        periodicidad="mensual",
        filtro_territorio=_CCAA_Y_PROVINCIA,
    ),
    # --- Empleo ------------------------------------------------------------
    Indicador(
        codigo="ine_coste_laboral_ccaa",
        tabla_id_externo="6062",
        nombre="Coste laboral por hora efectiva, CCAA, sectores de actividad",
        categoria="empleo",
        nivel_territorial="ccaa",
        periodicidad="trimestral",
        filtro_territorio=_CCAA,
    ),
    Indicador(
        codigo="ine_tiempo_trabajo_ccaa",
        tabla_id_externo="6063",
        nombre="Tiempo de trabajo por trabajador y mes, CCAA, tipo de jornada, sectores de actividad",
        categoria="empleo",
        nivel_territorial="ccaa",
        periodicidad="trimestral",
        filtro_territorio=_CCAA,
    ),
    Indicador(
        codigo="ine_epa_paro_provincia",
        tabla_id_externo="3996",
        nombre="Tasas de actividad, paro y empleo por provincia y sexo (EPA)",
        categoria="empleo",
        nivel_territorial="provincia",
        periodicidad="trimestral",
        filtro_territorio=_PROVINCIA,
    ),
    # --- Ya existían (no vienen del Excel, se mantienen) ------------------
    Indicador(
        codigo="ine_epa_ccaa",
        tabla_id_externo="75803",
        nombre="Tasas de paro por grupos de edad, sexo y comunidad autónoma (EPA)",
        categoria="mercado_laboral",
        nivel_territorial="ccaa",
        periodicidad="trimestral",
        filtro_territorio=_CCAA,
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
    ),
    Indicador(
        codigo="ine_cre_ccaa",
        tabla_id_externo="77196",
        nombre="PIB pm y VAB por ramas de actividad, precios corrientes, por CCAA (CRE)",
        categoria="economia",
        nivel_territorial="ccaa",
        periodicidad="anual",
        filtro_territorio=_CCAA,
    ),
]


def _validar_catalogo() -> None:
    codigos = [i.codigo for i in INDICADORES]
    tablas = [i.tabla_id_externo for i in INDICADORES]
    duplicados_codigo = {c for c in codigos if codigos.count(c) > 1}
    duplicados_tabla = {t for t in tablas if tablas.count(t) > 1}
    if duplicados_codigo:
        raise ValueError(f"Códigos de indicador duplicados en indicadores.py: {duplicados_codigo}")
    if duplicados_tabla:
        raise ValueError(f"Tablas del INE duplicadas en indicadores.py: {duplicados_tabla}")


_validar_catalogo()
