"""Utilities for the official Mexico Central production time."""

from datetime import datetime
import pytz

ZONA_HORARIA_MEXICO = pytz.timezone("America/Mexico_City")
SQL_AHORA_MEXICO = "(CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City')"
def ahora_mexico():
    """Hora actual de Ciudad de México sin tzinfo para PostgreSQL."""
    return datetime.now(ZONA_HORARIA_MEXICO).replace(tzinfo=None)
def ahora_mexico_texto(formato="%d/%m/%Y %H:%M:%S"):
    return ahora_mexico().strftime(formato)
