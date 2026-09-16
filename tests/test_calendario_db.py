"""upsert_fechas_calendario no debe mandar la misma fecha dos veces en el
mismo INSERT (CardinalityViolation vista en producción el 2026-09-16)."""
from __future__ import annotations

from datetime import date

from extremadura_datos import db


class _CursorFalso:
    def __init__(self, registro):
        self.registro = registro

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _ConexionFalsa:
    def __init__(self):
        self.registro = []

    def cursor(self):
        return _CursorFalso(self.registro)

    def commit(self):
        pass


def test_fechas_repetidas_se_deduplican(monkeypatch):
    capturado = {}

    def execute_values_falso(cur, sql, registros):
        capturado["registros"] = registros

    monkeypatch.setattr(db.psycopg2.extras, "execute_values", execute_values_falso)
    fechas = [
        (date(2026, 9, 23), "Agosto 2026"),
        (date(2026, 9, 23), "Agosto 2026 (avance)"),
        (date(2026, 10, 23), "Septiembre 2026"),
    ]
    db.upsert_fechas_calendario(_ConexionFalsa(), 7, fechas)
    assert sorted(r[1] for r in capturado["registros"]) == [date(2026, 9, 23), date(2026, 10, 23)]
    assert len({r[1] for r in capturado["registros"]}) == len(capturado["registros"])
