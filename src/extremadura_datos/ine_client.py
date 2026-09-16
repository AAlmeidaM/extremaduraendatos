"""Cliente mínimo para la API JSON del INE (Tempus3).

Referencia: https://www.ine.es/dyngs/DAB/index.htm?cid=1100

El formato de respuesta (lista de series con `COD`, `Nombre`, `T3_Unidad`,
`T3_Escala`, `MetaData`, `Data`...) está verificado contra respuestas reales
del INE para 3 tablas estructuralmente distintas (50913, 3996, 6150 — ver
docs/fuentes-ine.md y CHANGELOG 2026-08-28), no solo contra documentación.
Las 21 tablas restantes del catálogo comparten el mismo motor de parseo y no
se han descargado una por una individualmente; si alguna da 0 filas o error
al ingerir, usar:

    python -m extremadura_datos.inspect_table <id_tabla>

para volcar su JSON crudo a E:\\Lab\\datasets\\extremadura-en-datos\\raw y
revisarlo — el ajuste, si hace falta, se hace en `parsear_tabla()` /
`_extrae_territorio_y_atributos()` en `parse.py` (único sitio que hay que
tocar para las 24 tablas a la vez).
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)


class IneApiError(RuntimeError):
    pass


class IneClient:
    def __init__(self, base_url: str, timeout: int = 30, delay_seconds: float = 1.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.delay_seconds = delay_seconds
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": "extremadura-en-datos/0.1 (uso personal, Office Lab)"}
        )

    def fetch_tabla(
        self,
        tabla_id: str,
        tip: str = "AM",
        nult: int | None = None,
        det: int | None = None,
        extra_params: dict[str, Any] | list[tuple[str, Any]] | tuple | None = None,
    ) -> Any:
        """Descarga los datos de una tabla completa (DATOS_TABLA), en una sola petición.

        `tip=AM` pide formato amigable + metadatos (nombres de unidad, escala...).
        Sin filtros `tv=` se traen TODAS las series de la tabla (todas las CCAA o
        provincias); el filtrado a Extremadura/Badajoz/Cáceres se hace después,
        en parse.py, por nombre de serie — así no dependemos de adivinar los
        códigos internos de variable/valor que usa el INE puertas adentro.

        ⚠️ Nota histórica (2026-08-28): esta función tenía antes un bucle de
        "paginación" que pedía `page=2`, `page=3`... mientras la respuesta
        trajera 500 o más series, asumiendo (sin haberlo verificado nunca)
        que `DATOS_TABLA` pagina en bloques de 500. Al ejecutar la ingesta
        real por primera vez contra el INE (tabla 50913, modo histórico) se
        vio que la API real NO reconoce ese parámetro `page` — devuelve la
        respuesta completa entera en la primera petición, así que pedir
        `page=2` devolvía exactamente lo mismo, y el bucle nunca terminaba
        (bucle infinito real, descubierto porque se quedó machacando la API
        del INE varios minutos sin avanzar). Se ha comprobado además, en
        toda la verificación tabla por tabla de este proyecto (ver
        docs/fuentes-ine.md), que `DATOS_TABLA` siempre devuelve TODAS las
        series de golpe en una sola respuesta (hasta 1080 series vistas),
        nunca truncada por el propio INE — por eso ahora es una única
        petición sin bucle.
        """
        # Lista de pares (no dict): el filtro `tv=VARIABLE:VALOR` del INE se
        # repite para pedir varios valores (2026-09-16, tablas de la ECP).
        params: list[tuple[str, Any]] = [("tip", tip)]
        if nult is not None:
            params.append(("nult", nult))
        if det is not None:
            params.append(("det", det))
        if extra_params:
            items = extra_params.items() if isinstance(extra_params, dict) else extra_params
            params.extend(items)

        url = f"{self.base_url}/DATOS_TABLA/{tabla_id}"
        logger.debug("GET %s params=%s", url, params)
        resp = self._session.get(url, params=params, timeout=self.timeout)
        if resp.status_code != 200:
            raise IneApiError(
                f"HTTP {resp.status_code} al pedir la tabla {tabla_id}: {resp.text[:500]}"
            )
        try:
            data = resp.json()
        except ValueError as exc:
            raise IneApiError(
                f"Respuesta no-JSON para la tabla {tabla_id}: {resp.text[:500]}"
            ) from exc

        if isinstance(data, dict) and "Nombre" in data and "Descripción" in data:
            # El INE a veces responde un único objeto de error/aviso en vez de lista.
            raise IneApiError(f"Respuesta inesperada para tabla {tabla_id}: {data}")

        time.sleep(self.delay_seconds)
        return data

    def fetch_json(self, path: str) -> Any:
        """GET genérico a cualquier endpoint de Tempus3 (p.ej.
        'PUBLICACIONES_OPERACION/25' o 'PUBLICACIONFECHA_PUBLICACION/8').

        Usado por calendario.py para consultar el calendario oficial de
        publicaciones del INE -- fetch_tabla() se queda específico de
        DATOS_TABLA porque tiene su propia validación de forma de respuesta.
        """
        url = f"{self.base_url}/{path}"
        logger.debug("GET %s", url)
        resp = self._session.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            raise IneApiError(f"HTTP {resp.status_code} al pedir {path}: {resp.text[:500]}")
        try:
            data = resp.json()
        except ValueError as exc:
            raise IneApiError(f"Respuesta no-JSON para {path}: {resp.text[:500]}") from exc
        time.sleep(self.delay_seconds)
        return data
