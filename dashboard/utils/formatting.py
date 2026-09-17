"""Formatting helpers used by the dashboard."""

def formatear_duracion(minutos):
    """Convierte minutos a una duración legible para el operador."""
    try:
        total = max(0, int(round(float(minutos))))
    except Exception:
        total = 0
    horas, mins = divmod(total, 60)
    if horas and mins:
        return f"{horas} h {mins:02d} min"
    if horas:
        return f"{horas} h"
    return f"{mins} min"
