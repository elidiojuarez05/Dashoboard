"""Helpers for ODP priority normalization and display."""

PRIORIDADES_ODP = ["NORMAL", "URGENTE", "BOMBERAZO"]
def normalizar_prioridad_odp(valor):
    p = str(valor or "NORMAL").strip().upper()
    if p in {"BOMBERAZO", "🔥 BOMBERAZO", "BOMBERAZO 🚨"}: return "BOMBERAZO"
    if p in {"URGENTE", "⚠️ URGENTE", "URGENTE ⚠️"}: return "URGENTE"
    return "NORMAL"
def etiqueta_prioridad_odp(valor):
    return {"BOMBERAZO":"🚨 BOMBERAZO", "URGENTE":"⚠️ URGENTE", "NORMAL":"🔵 NORMAL"}[normalizar_prioridad_odp(valor)]
def prioridad_es_critica(valor):
    return normalizar_prioridad_odp(valor) == "BOMBERAZO"
