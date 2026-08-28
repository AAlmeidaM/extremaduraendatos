"""Calendario oficial de publicaciones del INE: gobierna qué indicadores
necesitan de verdad una llamada a la API en cada ejecución de la ingesta
diaria (`--modo incremental`).

Antes (ver PROJECT.md §17, decisión sustituida por esta): se llamaba a la API
para las 23 tablas activas todos los días, confiando en que el upsert es
idempotente. El usuario pidió conectar el calendario oficial del INE para que
sea ese calendario el que decida, tabla por tabla, si hoy toca de verdad o no.

Cómo funciona (verificado contra la API real el 2026-08-28, ver
docs/fuentes-ine.md e indicadores.py):

    1. Cada indicador ya sabe su `ine_operacion_id` (y casi todos también su
       `ine_publicacion_id` -- ver indicadores.py). Estos dos ids se sacaron
       directamente de SERIES_TABLA/{tabla_id_externo} (trae FK_Operacion y
       FK_Publicacion en cada serie), sin falta de ningún otro endpoint.
    2. Con `ine_publicacion_id` se pide PUBLICACIONFECHA_PUBLICACION/{id},
       que da las fechas de publicación (pasadas y previstas) de esa
       publicación. Se guardan en `calendario_publicacion`.
    3. En cada ejecución incremental, antes de llamar a fetch_tabla() de
       verdad: si hay alguna fecha de esa tabla ya vencida (<= hoy) y sin
       marcar como procesada, se ingiere; si no, se salta la llamada de hoy.
    4. Red de seguridad: si un indicador no tiene `ine_operacion_id` (no
       debería pasar con el catálogo actual, pero cubre el caso de un
       indicador nuevo sin rellenar este dato) o si el calendario nunca ha
       podido leerse (fallo de red, API caída...), SIEMPRE se ingiere -- este
       módulo solo puede hacer que se ingiera con más criterio, nunca que se
       deje de ingerir por falta de datos de calendario.

`--modo historico` (recarga completa manual) no pasa por aquí: siempre trae
todo el histórico, calendario aparte.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from . import db
from .indicadores import Indicador
from .ine_client import IneApiError, IneClient

logger = logging.getLogger(__name__)

# Cada cuántos días se vuelve a consultar PUBLICACIONFECHA_PUBLICACION para
# un indicador. El calendario de una operación del INE apenas cambia de un
# día para otro, así que no hace falta pedirlo cada vez -- pero tampoco tanto
# margen como para tardar días en enterarse de un cambio de fecha.
DIAS_ENTRE_REFRESCOS = 3


def _parsear_fecha_ine(valor: Any) -> date | None:
    """La API del INE representa fechas como epoch-millis (mismo formato que
    usa en Data[].Fecha de DATOS_TABLA, ver parse.py) en la mayoría de
    endpoints Tempus3; por si acaso, también se admite una cadena ISO."""
    if valor is None:
        return None
    try:
        if isinstance(valor, (int, float)):
            return datetime.utcfromtimestamp(int(valor) / 1000).date()
        if isinstance(valor, str) and valor.strip().isdigit():
            return datetime.utcfromtimestamp(int(valor) / 1000).date()
        if isinstance(valor, str):
            return datetime.fromisoformat(valor[:10]).date()
    except (ValueError, OverflowError, OSError, TypeError):
        return None
    return None


def _resolver_publicacion_id(cliente: IneClient, indicador: Indicador) -> int | None:
    """Autodescubre ine_publicacion_id cuando el catálogo no lo trae (tablas
    con formato "CRE" de SERIES_TABLA, que no incluye FK_Publicacion por
    serie -- ver indicadores.py). Se pide PUBLICACIONES_OPERACION/{operacion}
    y se toma la primera publicación -- para las operaciones de este
    catálogo cada una solo tiene una publicación relevante (verificado
    2026-08-28); si en el futuro alguna operación tuviera varias habría que
    afinar el criterio (p.ej. por periodicidad)."""
    if indicador.ine_operacion_id is None:
        return None
    publicaciones = cliente.fetch_json(f"PUBLICACIONES_OPERACION/{indicador.ine_operacion_id}")
    if not isinstance(publicaciones, list) or not publicaciones:
        return None
    primera = publicaciones[0]
    if isinstance(primera, dict):
        return primera.get("Id")
    return None


def refrescar_si_hace_falta(conn, cliente: IneClient, indicador_id: int, indicador: Indicador) -> None:
    """Actualiza calendario_publicacion desde la API del INE si hace más de
    DIAS_ENTRE_REFRESCOS días que no se consulta (o nunca). Nunca lanza --
    un fallo aquí jamás debe impedir la ingesta real (ver docstring del
    módulo, red de seguridad)."""
    if indicador.ine_operacion_id is None:
        return
    if db.calendario_reciente(conn, indicador_id, DIAS_ENTRE_REFRESCOS):
        return
    try:
        publicacion_id = indicador.ine_publicacion_id
        if publicacion_id is None:
            publicacion_id = _resolver_publicacion_id(cliente, indicador)
            if publicacion_id is not None:
                db.guardar_ine_publicacion_id(conn, indicador_id, publicacion_id)
                logger.info(
                    "%s: ine_publicacion_id autodescubierto = %s.", indicador.codigo, publicacion_id
                )
        if publicacion_id is None:
            logger.warning(
                "%s: no se pudo determinar ine_publicacion_id (operación %s); "
                "se ingerirá sin gobernar por calendario hasta que se resuelva.",
                indicador.codigo, indicador.ine_operacion_id,
            )
            return

        fechas_raw = cliente.fetch_json(f"PUBLICACIONFECHA_PUBLICACION/{publicacion_id}")
        fechas: list[tuple[date, str | None]] = []
        if isinstance(fechas_raw, list):
            for item in fechas_raw:
                if not isinstance(item, dict):
                    continue
                fecha = _parsear_fecha_ine(item.get("Fecha"))
                if fecha is not None:
                    periodo = item.get("LiteralFecha") or item.get("Anyo")
                    fechas.append((fecha, str(periodo) if periodo is not None else None))

        if fechas:
            db.upsert_fechas_calendario(conn, indicador_id, fechas)
        db.marcar_calendario_actualizado(conn, indicador_id)
        logger.info("%s: calendario actualizado (%d fechas conocidas).", indicador.codigo, len(fechas))
    except IneApiError as exc:
        logger.warning("%s: fallo consultando el calendario del INE (%s); se ingerirá igualmente.", indicador.codigo, exc)
    except Exception:  # noqa: BLE001 - un fallo aquí nunca debe frenar la ingesta
        logger.exception("%s: error inesperado actualizando el calendario; se ingerirá igualmente.", indicador.codigo)


def debe_ingerir_hoy(conn, cliente: IneClient, indicador_id: int, indicador: Indicador) -> bool:
    """True si hoy toca llamar de verdad a la API para este indicador."""
    if indicador.ine_operacion_id is None:
        return True  # sin mapeo a operación del INE: comportamiento anterior (llamar siempre)

    refrescar_si_hace_falta(conn, cliente, indicador_id, indicador)

    if not db.hay_fechas_calendario(conn, indicador_id):
        # Calendario aún desconocido (primera vez, o la API falló todas las
        # veces) -- nunca se deja de ingerir por esto.
        return True

    return db.hay_publicacion_pendiente(conn, indicador_id)


def marcar_procesado(conn, indicador_id: int) -> None:
    db.marcar_publicaciones_procesadas(conn, indicador_id)
