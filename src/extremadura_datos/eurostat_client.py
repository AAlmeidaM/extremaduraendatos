"""Cliente mínimo para la API de difusión de Eurostat (JSON-stat 2.0).

Referencia: https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-getting-started/api

Verificado contra la API real el 2026-09-15 (ver docs/fuentes-europa-agro.md §1):

- Sin autenticación. `GET {base}/data/{dataset}?dim=COD&dim=COD2&sinceTimePeriod=AAAA`.
- Un parámetro de dimensión se repite para pedir varios valores (`unit=MIO_EUR&unit=EUR_HAB`).
- Extracciones de más de 5.000.000 de celdas → HTTP 413 `EXTRACTION_TOO_BIG`:
  el catálogo filtra siempre las dimensiones que no interesan (ver
  `Indicador.eurostat_filtros` en indicadores.py).
- El campo `updated` de la respuesta indica la última actualización del
  dataset; se usa en modo incremental para no volver a descargar un dataset
  que no ha cambiado (ver `fecha_actualizacion`).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Iterable

import requests

logger = logging.getLogger(__name__)

# Territorio usado para la petición "sonda" de fecha de actualización: la
# respuesta es mínima y todos los datasets del catálogo lo tienen.
GEO_SONDA = "ES43"


class EurostatApiError(RuntimeError):
    pass


class EurostatClient:
    def __init__(self, base_url: str, timeout: int = 120, delay_seconds: float = 1.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.delay_seconds = delay_seconds
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": "extremadura-en-datos/0.1 (uso personal, Office Lab)"}
        )

    @staticmethod
    def _params(
        filtros: Iterable[tuple[str, Iterable[str]]], extra: dict[str, Any] | None = None
    ) -> list[tuple[str, str]]:
        params: list[tuple[str, str]] = []
        for dimension, codigos in filtros:
            params.extend((dimension, codigo) for codigo in codigos)
        for clave, valor in (extra or {}).items():
            if valor is not None:
                params.append((clave, str(valor)))
        return params

    def _get(self, dataset: str, params: list[tuple[str, str]]) -> dict[str, Any]:
        url = f"{self.base_url}/data/{dataset}"
        logger.debug("GET %s params=%s", url, params)
        resp = self._session.get(url, params=params, timeout=self.timeout)
        if resp.status_code != 200:
            detalle = resp.text[:500]
            try:
                errores = resp.json().get("error") or []
                if errores:
                    detalle = "; ".join(str(e.get("label", e)) for e in errores)
            except ValueError:
                pass
            raise EurostatApiError(f"HTTP {resp.status_code} al pedir {dataset}: {detalle}")
        try:
            data = resp.json()
        except ValueError as exc:
            raise EurostatApiError(f"Respuesta no-JSON para {dataset}: {resp.text[:500]}") from exc
        time.sleep(self.delay_seconds)
        return data

    def fetch_dataset(
        self,
        dataset: str,
        filtros: Iterable[tuple[str, Iterable[str]]] = (),
        since_time_period: str | int | None = None,
    ) -> dict[str, Any]:
        """Descarga un dataset completo (todas las regiones) con los filtros de
        dimensión indicados. `since_time_period=None` trae todo el histórico."""
        params = self._params(filtros, {"sinceTimePeriod": since_time_period})
        return self._get(dataset, params)

    def fecha_actualizacion(
        self, dataset: str, filtros: Iterable[tuple[str, Iterable[str]]] = ()
    ) -> str | None:
        """Devuelve el campo `updated` del dataset con una petición mínima
        (un territorio, último periodo). None si no se puede obtener — quien
        llama debe entonces descargar igualmente (red de seguridad)."""
        filtros = list(filtros)
        params = self._params(filtros, {"geo": GEO_SONDA, "lastTimePeriod": 1})
        try:
            data = self._get(dataset, params)
        except (EurostatApiError, requests.RequestException) as exc:
            logger.warning("No se pudo consultar la fecha de actualización de %s: %s", dataset, exc)
            return None
        actualizado = data.get("updated") if isinstance(data, dict) else None
        return str(actualizado) if actualizado else None
