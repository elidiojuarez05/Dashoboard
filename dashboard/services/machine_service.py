"""Servicios de compatibilidad entre estaciones, materiales y rutas.

Fase 12 de la refactorización: centraliza las reglas de compatibilidad
máquina/material sin modificar la interfaz de producción.
"""

MAQUINAS_FLEXIBLES = {
    "EPSON 1", "EPSON 2", "ALLWIN", "GRANDO", "DURST 312",
    "MIMAKI", "FAVUTEK"
}

MAQUINAS_RIGIDO_FLEXIBLE = {
    "VUTEK PRO", "VUTEK F4", "VUTEK H5", "DURST P10 PLUS"
}

# Nombres históricos incluidos deliberadamente para mantener compatibilidad
# con configuraciones y registros existentes.
ROUTERS_RIGIDO_FLEXIBLE = {
    "ROUTER ZUND XL", "ROUTER ZUND G3", "ROUTER KONSGGBERG",
    "ROUTER KONSGBERG", "ROUTER KONSGSBERG", "ROUTER KONSGBERG",
    "ROUTER KONSGBERG", "ROUTER KONSGGBERG"
}


def _norm_nombre_estacion(nombre):
    """Normaliza nombres de máquinas/estaciones para comparaciones seguras."""
    return " ".join(str(nombre or "").strip().upper().split())


def maquina_compatible_material(nombre_maquina, material):
    """Determina si una estación puede procesar un material dado."""
    n = _norm_nombre_estacion(nombre_maquina)
    m = _norm_nombre_estacion(material)

    if not n or not m:
        return False

    # Xerox: exclusivamente papel couché.
    if n == "XEROX":
        return m in {"PAPEL COUCHÉ", "PAPEL COUCHE"}

    # Plotter de recorte: exclusivamente vinil.
    if "PLOTTER RECORTE" in n:
        return m == "VINIL"

    # Routers de mesa: rígido y flexible, además de papel couché para
    # conservar la compatibilidad histórica de trabajos provenientes de Xerox.
    if "ROUTER" in n:
        return m in {
            "RIGIDO", "RÍGIDO", "FLEXIBLE", "GENERAL",
            "PAPEL COUCHÉ", "PAPEL COUCHE"
        }

    # Impresoras capaces de trabajar rígido y flexible.
    if n in MAQUINAS_RIGIDO_FLEXIBLE:
        return m in {"RIGIDO", "RÍGIDO", "FLEXIBLE", "VINIL", "GENERAL"}

    # Impresoras exclusivamente flexibles.
    if n in MAQUINAS_FLEXIBLES:
        return m in {"FLEXIBLE", "VINIL", "GENERAL"}

    # Para configuraciones antiguas/no clasificadas, GENERAL no bloquea.
    return m == "GENERAL"


def maquinas_impresion_compatibles(material, maquinas):
    """Filtra estaciones de impresión compatibles con el material."""
    return [m for m in (maquinas or []) if maquina_compatible_material(m, material)]


def routers_compatibles(material, maquinas):
    """Filtra routers compatibles con el material."""
    return [m for m in (maquinas or []) if maquina_compatible_material(m, material)]
