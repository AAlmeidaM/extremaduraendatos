"""Utilidades comunes de la fase 3 (precios agrarios): lectura de precios en
texto, periodos semanales/mensuales y guardado del crudo.

Ver docs/fuentes-europa-agro.md §2, §3 y §5 para el formato real de cada fuente.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

MESES_EN = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1
)}


def precio_desde_texto(valor: Any) -> float | None:
    """Convierte un precio a float.

    Formatos reales vistos (portal Agri-food, 2026-09-15/16): `"€699.95"`,
    `"€233,00"` (coma decimal en cereales), `"€,00"`, `null`, y números
    (fertilizantes). También admite miles con separador (`"1,008.50"`,
    `"1.008,50"`): el último separador que aparece es el decimal.
    Devuelve None si no hay número o si el precio no es positivo (un 0 en
    estas fuentes significa "sin cotización", no un precio real).
    """
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        numero = float(valor)
    else:
        texto = re.sub(r"[^0-9,.\-]", "", str(valor))
        if not re.search(r"\d", texto):
            return None
        if "," in texto and "." in texto:
            if texto.rfind(",") > texto.rfind("."):
                texto = texto.replace(".", "").replace(",", ".")
            else:
                texto = texto.replace(",", "")
        elif "," in texto:
            texto = texto.replace(",", ".")
        try:
            numero = float(texto)
        except ValueError:
            return None
    return numero if numero > 0 else None


def fecha_ddmmyyyy(texto: str) -> date:
    return datetime.strptime(texto.strip(), "%d/%m/%Y").date()


def periodo_semanal(inicio: date) -> tuple[date, int, str]:
    """Semana que empieza en `inicio` → (fecha, año ISO, "S07")."""
    iso = inicio.isocalendar()
    return inicio, iso[0], f"S{iso[1]:02d}"


def periodo_mensual(anyo: int, mes: int) -> tuple[date, int, str]:
    return date(anyo, mes, 1), anyo, f"M{mes:02d}"


def guarda_crudo(datasets_dir: Path, fuente: str, nombre: str, datos: Any, extension: str = "json") -> None:
    destino_dir = datasets_dir / "raw" / fuente
    destino_dir.mkdir(parents=True, exist_ok=True)
    marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    nombre_limpio = re.sub(r"[^A-Za-z0-9_.-]+", "_", nombre)
    destino = destino_dir / f"{nombre_limpio}_{marca}.{extension}"
    if extension == "json":
        destino.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    else:
        destino.write_text(str(datos), encoding="utf-8")
