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
        extra_params: dict[str, Any] | None = None,
    ) -> Any:
        """Descarga los datos de una tabla completa (DATOS_TABLA), con paginación.

        `tip=AM` pide formato amigable + metadatos (nombres de unidad, escala...).
        Sin filtros `tv=` se traen TODAS las series de la tabla (todas las CCAA o
        provincias); el filtrado a Extremadura/Badajoz/Cáceres se hace después,
        en parse.py, por nombre de serie — así no dependemos de adivinar los
        códigos internos de variable/valor que usa el INE puertas adentro.
        """
        params: dict[str, Any] = {"tip": tip}
        if nult is not None:
            params["nult"] = nult
        if det is not None:
            params["det"] = det
        if extra_params:
            params.update(extra_params)

        all_items: list[Any] = []
        page = 1
        while True:
            page_params = dict(params)
            if page > 1:
                page_params["page"] = page

            url = f"{self.base_url}/DATOS_TABLA/{tabla_id}"
            logger.debug("GET %s params=%s", url, page_params)
            resp = self._session.get(url, params=page_params, timeout=self.timeout)
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

            if not isinstance(data, list):
                # Puede que para esta tabla la respuesta no sea una lista de series.
                # Se devuelve tal cual y que parse.py decida — mejor no perder datos
                # por una suposición equivocada aquí.
                return data

            all_items.extend(data)

            if len(data) < 500:
                break
            page += 1
            time.sleep(self.delay_seconds)

        time.sleep(self.delay_seconds)
        return all_items
