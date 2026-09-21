"""Servicios de cálculo y calibración de producción.

Fase 10 de la refactorización: la UI no contiene reglas de negocio para
calcular tiempos de impresión/corte, áreas o pasadas.
"""

ANCHO_LAMINA_RIGIDA_M = 1.22
LARGO_LAMINA_RIGIDA_M = 2.44
M2_POR_LAMINA_RIGIDA = ANCHO_LAMINA_RIGIDA_M * LARGO_LAMINA_RIGIDA_M


def _numero_seguro(valor, default=0.0):
    try:
        if valor is None:
            return default
        return float(valor)
    except (TypeError, ValueError):
        return default


def _norm_nombre_estacion(nombre):
    return " ".join(str(nombre or "").strip().upper().split())


def _config_produccion_maquina(nombre_maquina):
    """
    Obtiene la calibración canónica de producción.

    Todas las tarifas están expresadas en MINUTOS por unidad:

    - Impresoras: minutos / m²
    - Xerox: minutos / hoja
    - Routers: minutos / corte

    VUTEK PRO y VUTEK F4 tienen dos velocidades:
        MAXIMA
        ESTANDAR
    """

    if not nombre_maquina:
        return {}

    n = (
        _norm_nombre_estacion(nombre_maquina)
        if "_norm_nombre_estacion" in globals()
        else " ".join(str(nombre_maquina).strip().upper().split())
    )

    calibracion = {

        # ============================================================
        # EPSON
        # ============================================================

        "EPSON 1": {
            "unidad": "ML",
            "ancho_referencia_m": 1.52,
            "ganancia_entre_copias_m": 0.02,
            # Rollo real: 50 m x 1.52 m ≈ 5 h 45 min.
            "rollo_50m_min": 345.0,
            # Rollo real con tinta blanca a registro ≈ 12 h.
            # Calibración específica: 50 m x 1.52 m a 12 pasadas = 720 min.
            "rollo_50m_tinta_blanca_min": 720.0,
            "rollo_50m_tinta_blanca_pasadas_min": {
                "MAXIMA": {12: 720.0},
                "ESTANDAR": {12: 720.0},
            },
        },

        "EPSON 2": {
            "unidad": "ML",
            "ancho_referencia_m": 1.52,
            "ganancia_entre_copias_m": 0.02,
            "rollo_50m_min": 345.0,
            "rollo_50m_tinta_blanca_min": 720.0,
            "rollo_50m_tinta_blanca_pasadas_min": {
                "MAXIMA": {12: 720.0},
                "ESTANDAR": {12: 720.0},
            },
        },

        # ============================================================
        # VUTEK PRO
        # ============================================================

        "VUTEK PRO": {
            "unidad": "ML",
            "ancho_referencia_m": 1.52,
            "ganancia_entre_copias_m": 0.50,

            # FLEXIBLE — rollo de 50 m x 1.52 m.
            "rollo_50m_pasadas_min": {
                12: 47.42,
                16: 61.80,
                24: 81.60,
                32: 123.60,
            },
            "rollo_50m_pasadas_min_estandar": {
                12: 76.20,
                16: 93.60,
                24: 151.80,
                32: 211.00,
            },

            # RÍGIDO — referencia: 40 láminas de 1.22 x 2.44 m.
                        # RÍGIDO — NUEVAS REFERENCIAS REALES: 1 a 20 láminas.
            # Las referencias expresadas como HORAS en la hoja fuente se convierten
            # a minutos (ej. 1.01 h = 61 min; 1.16 h = 76 min).
            "tiempo_laminas_pasadas_min": {
                "MAXIMA": {
                    16: {1: 3.45, 2: 5.39, 3: 7.30, 4: 9.23, 5: 11.17, 6: 13.11, 7: 15.02, 8: 16.55, 9: 18.49, 10: 20.43, 11: 22.36, 12: 24.27, 13: 26.24, 14: 28.15, 15: 30.08, 16: 32.02, 17: 33.53, 18: 35.46, 19: 37.40, 20: 39.34},
                    24: {1: 5.22, 2: 8.10, 3: 11.00, 4: 13.48, 5: 16.41, 6: 19.29, 7: 22.17, 8: 25.07, 9: 28.01, 10: 30.45, 11: 33.36, 12: 36.26, 13: 39.17, 14: 42.05, 15: 44.55, 16: 47.46, 17: 50.33, 18: 53.27, 19: 56.14, 20: 59.02},
                    32: {1: 6.55, 2: 10.40, 3: 14.24, 4: 18.09, 5: 21.50, 6: 25.32, 7: 29.19, 8: 33.01, 9: 36.43, 10: 40.27, 11: 44.09, 12: 47.53, 13: 51.38, 14: 55.20, 15: 59.07, 16: 62.00, 17: 66.00, 18: 70.00, 19: 73.00, 20: 77.00},
                },
                "ESTANDAR": {
                    16: {1: 6.29, 2: 9.58, 3: 13.22, 4: 16.51, 5: 20.20, 6: 23.49, 7: 27.13, 8: 30.42, 9: 34.10, 10: 37.39, 11: 41.08, 12: 44.32, 13: 48.06, 14: 51.30, 15: 54.59, 16: 58.28, 17: 61.00, 18: 65.00, 19: 68.00, 20: 72.00},
                    24: {1: 9.27, 2: 14.35, 3: 19.48, 4: 24.57, 5: 30.15, 6: 35.23, 7: 40.32, 8: 45.45, 9: 51.03, 10: 56.07, 11: 61.00, 12: 76.00, 13: 71.00, 14: 86.00, 15: 82.00, 16: 97.00, 17: 92.00, 18: 97.00, 19: 102.00, 20: 118.00},
                    32: {1: 12.19, 2: 19.12, 3: 26.04, 4: 32.57, 5: 39.44, 6: 46.32, 7: 53.30, 8: 60.00, 9: 67.00, 10: 73.00, 11: 80.00, 12: 87.00, 13: 94.00, 14: 101.00, 15: 108.00, 16: 114.00, 17: 121.00, 18: 128.00, 19: 135.00, 20: 142.00},
                },
            },

"tiempo_40_laminas_pasadas_min": {
                "MAXIMA": {12: 60.00, 16: 102.00, 24: 113.00, 32: 123.60},
                "ESTANDAR": {12: 87.60, 16: 93.60, 24: 151.80, 32: 211.00},
            },

            # RÍGIDO — TINTA BLANCA: 40 láminas de 1.22 x 2.44 m.
            "tiempo_40_laminas_tinta_blanca_pasadas_min": {
                "MAXIMA": {48: 227.00},   # 3.47 h
                "ESTANDAR": {48: 416.00}, # 6.56 h
            },
            # RÍGIDO — DAY & NIGHT: 40 láminas de 1.22 x 2.44 m.
            "tiempo_40_laminas_day_night_pasadas_min": {
                "MAXIMA": {72: 340.00},   # 5.40 h
                "ESTANDAR": {72: 624.00}, # 10.24 h
            },

            # Calibraciones reales especiales: rollo 50 m x 1.52 m.
            "rollo_50m_tinta_blanca_pasadas_min": {
                "MAXIMA": {48: 184.80},
                "ESTANDAR": {48: 327.60},
            },
            "rollo_50m_day_night_pasadas_min": {
                "MAXIMA": {72: 421.80},
                "ESTANDAR": {72: 754.80},
            },

            "multiplicador_tinta_blanca": 2.0,
            "multiplicador_day_night": 3.0,
        },

        # ============================================================
        # VUTEK F4
        # ============================================================

        "VUTEK F4": {
            "unidad": "ML",
            "ancho_referencia_m": 1.52,
            "ganancia_entre_copias_m": 0.50,

            # FLEXIBLE — rollo de 50 m x 1.52 m.
            "rollo_50m_pasadas_min": {
                8: 32.00,
                12: 47.00,
                16: 61.80,
            },
            "rollo_50m_pasadas_min_estandar": {
                8: 58.00,
                12: 76.20,
                16: 93.60,
            },

            # RÍGIDO — referencia: 40 láminas de 1.22 x 2.44 m.
                        # RÍGIDO — NUEVAS REFERENCIAS REALES: 1 a 20 láminas.
            "tiempo_laminas_pasadas_min": {
                "MAXIMA": {
                    12: {1: 2.57, 2: 4.22, 3: 5.47, 4: 7.10, 5: 8.35, 6: 10.00, 7: 11.50, 8: 12.51, 9: 14.16, 10: 15.41, 11: 17.04, 12: 18.29, 13: 19.54, 14: 21.19, 15: 22.45, 16: 24.10, 17: 25.32, 18: 26.58, 19: 28.23, 20: 29.48},
                    16: {1: 3.45, 2: 5.39, 3: 7.30, 4: 9.23, 5: 11.17, 6: 13.11, 7: 15.02, 8: 16.55, 9: 18.49, 10: 20.43, 11: 22.36, 12: 24.27, 13: 26.24, 14: 28.15, 15: 30.08, 16: 32.02, 17: 33.53, 18: 35.46, 19: 37.40, 20: 39.34},
                },
                "ESTANDAR": {
                    12: {1: 5.00, 2: 7.37, 3: 10.14, 4: 12.45, 5: 15.22, 6: 17.58, 7: 20.35, 8: 23.12, 9: 25.49, 10: 28.26, 11: 30.57, 12: 33.33, 13: 36.10, 14: 38.47, 15: 41.24, 16: 44.00, 17: 46.32, 18: 49.08, 19: 51.45, 20: 54.22},
                    16: {1: 6.29, 2: 9.58, 3: 13.22, 4: 16.51, 5: 20.20, 6: 23.49, 7: 27.13, 8: 30.42, 9: 34.10, 10: 37.39, 11: 41.08, 12: 44.32, 13: 48.06, 14: 51.30, 15: 54.59, 16: 58.28, 17: 61.00, 18: 65.00, 19: 68.00, 20: 72.00},
                },
            },

"tiempo_40_laminas_pasadas_min": {
                "MAXIMA": {8: 38.00, 12: 57.00, 16: 69.60},
                "ESTANDAR": {8: 70.00, 12: 105.00, 16: 140.00},
            },
        },

        # ============================================================
        # RESTO DE IMPRESORAS
        # ============================================================

        "VUTEK H5": {
            "unidad": "M2",
            "min_por_m2": 4.0,
            "ganancia_entre_copias_m": 0.30,
        },

        "DURST 312": {
            "unidad": "ML",
            "ancho_referencia_m": 3.20,
            "ganancia_entre_copias_m": 0.10,
            # Rollo 50 m x 3.20 m.
            "rollo_50m_por_ancho": {
                "3.20": {
                    "4": 137.0,
                    "6": 225.0,
                    "4_DOBLE": 275.0,
                    "6_DOBLE": 390.0,
                }
            },
        },

        "DURST P10 PLUS": {
            "unidad": "ML",
            "ancho_referencia_m": 1.52,
            "ganancia_entre_copias_m": 0.18,
            # Rígido: 16 láminas/h a 4 pasadas; 7 láminas/h a 6 pasadas.
            "laminas_por_hora_pasadas": {4: 16.0, 6: 7.0},
            # Flexible: rollo 50 m x 1.52 m.
            "rollo_50m_pasadas_min": {4: 120.0, 6: 180.0},
        },

        "FAVUTEK": {
            "unidad": "ML",
            "ancho_referencia_m": 3.20,
            "ganancia_entre_copias_m": 0.04,
            # Rollo real: 50 m x 3.20 m = 60 min.
            "rollo_50m_min": 60.0,
        },

        "MIMAKI": {
            "unidad": "ML",
            "ancho_referencia_m": 1.52,
            "ganancia_entre_copias_m": 0.02,
            # Rollo ≈ 2 h / 50 m.
            "rollo_50m_min": 120.0,
        },

        "GRANDO": {
            "unidad": "ML",
            "ancho_referencia_m": 1.52,
            "ganancia_entre_copias_m": 0.05,
            # Rollo 50 m: 1.52 m ≈ 1.5 h; 2.50 m ≈ 2.5 h; 3.20 m ≈ 3.5 h.
            "rollo_50m_por_ancho": {
                "1.52": 90.0,
                "2.50": 150.0,
                "3.20": 210.0,
            },
        },

        "ALLWIN": {
            "unidad": "ML",
            "ancho_referencia_m": 1.52,
            "ganancia_entre_copias_m": 0.05,
            # Rollo 50 m: 1.52 m ≈ 1.5 h; 3.20 m ≈ 2 h 30 min.
            "rollo_50m_por_ancho": {
                "1.52": 90.0,
                "3.20": 150.0,
            },
        },

        # ============================================================
        # XEROX
        # ============================================================

        "XEROX": {
            "unidad": "HOJA",
            "min_por_hoja": 2.0,
        },

        # ============================================================
        # ROUTERS — calibración actual
        # ============================================================

        "ROUTER ZUND XL": {
            "unidad": "CORTE",
            "tipos_corte": [
                "PLECA POR LAMINA",
                "BROCA CON DESBASTE",
                "CORTE COMPLETO STICKER",
                "NAVAJA TROVICEL 6MM",
                "NAVAJA SENCILLO",
                "NAVAJA COMPLEJIDAD MEDIO",
                # Compatibilidad con registros anteriores.
                "BROCA", "NAVAJA", "CORTE 45", "PLECA",
            ],
            "min_por_corte": {
                "PLECA POR LAMINA": 10.0,
                "BROCA CON DESBASTE": 60.0,
                "CORTE COMPLETO STICKER": 80.0,
                "NAVAJA TROVICEL 6MM": 15.0,
                "NAVAJA SENCILLO": 3.0,
                "NAVAJA COMPLEJIDAD MEDIO": 8.0,
                "BROCA": 60.0, "NAVAJA": 3.0, "CORTE 45": 8.0, "PLECA": 10.0,
            },
        },

        "ROUTER ZUND G3": {
            "unidad": "CORTE",
            "tipos_corte": [
                "PLECA POR LAMINA",
                "BROCA CON DESBASTE",
                "CORTE COMPLETO STICKER",
                "NAVAJA TROVICEL 6MM",
                "NAVAJA SENCILLO",
                "NAVAJA COMPLEJIDAD MEDIO",
                "BROCA", "NAVAJA", "CORTE 45", "PLECA",
            ],
            "min_por_corte": {
                "PLECA POR LAMINA": 10.0,
                "BROCA CON DESBASTE": 60.0,
                "CORTE COMPLETO STICKER": 80.0,
                "NAVAJA TROVICEL 6MM": 15.0,
                "NAVAJA SENCILLO": 3.0,
                "NAVAJA COMPLEJIDAD MEDIO": 8.0,
                "BROCA": 60.0, "NAVAJA": 3.0, "CORTE 45": 8.0, "PLECA": 10.0,
            },
        },

        "ROUTER KONSGBERG": {
            "unidad": "CORTE",
            "tipos_corte": [
                "PLECA POR LAMINA",
                "BROCA CON DESBASTE",
                "CORTE COMPLETO STICKER",
                "NAVAJA TROVICEL 6MM",
                "NAVAJA SENCILLO",
                "NAVAJA COMPLEJIDAD MEDIO",
                "BROCA", "NAVAJA", "CORTE 45", "PLECA",
            ],
            "min_por_corte": {
                "PLECA POR LAMINA": 10.0,
                "BROCA CON DESBASTE": 60.0,
                "CORTE COMPLETO STICKER": 80.0,
                "NAVAJA TROVICEL 6MM": 15.0,
                "NAVAJA SENCILLO": 3.0,
                "NAVAJA COMPLEJIDAD MEDIO": 8.0,
                "BROCA": 60.0, "NAVAJA": 3.0, "CORTE 45": 8.0, "PLECA": 10.0,
            },
        },

        # Variantes de nombre usadas en registros históricos.
        "ROUTER KONSGGBERG": {
            "unidad": "CORTE",
            "tipos_corte": [
                "PLECA POR LAMINA", "BROCA CON DESBASTE", "CORTE COMPLETO STICKER",
                "NAVAJA TROVICEL 6MM", "NAVAJA SENCILLO", "NAVAJA COMPLEJIDAD MEDIO",
                "BROCA", "NAVAJA", "CORTE 45", "PLECA",
            ],
            "min_por_corte": {
                "PLECA POR LAMINA": 10.0, "BROCA CON DESBASTE": 60.0,
                "CORTE COMPLETO STICKER": 80.0, "NAVAJA TROVICEL 6MM": 15.0,
                "NAVAJA SENCILLO": 3.0, "NAVAJA COMPLEJIDAD MEDIO": 8.0,
                "BROCA": 60.0, "NAVAJA": 3.0, "CORTE 45": 8.0, "PLECA": 10.0,
            },
        },

        # ============================================================
        # PLOTTER
        # ============================================================

        "PLOTTER RECORTE": {
            "unidad": "CORTE",
            "uso": "RECORTE DE VINIL",
            "materiales": ["VINIL"],
            "tipos_corte": ["RECORTE DE VINIL"],
            "min_por_corte": {
                "RECORTE DE VINIL": 8.0,
            },
        },
    }

    if n in calibracion:
        return calibracion[n]

    # Compatibilidad con máquinas futuras configuradas en MACHINE_CONFIGS
    cfg = MACHINE_CONFIGS.get(nombre_maquina, {})

    if isinstance(cfg, dict):
        prod = cfg.get("produccion") or cfg.get("production")

        if isinstance(prod, dict) and prod:
            return prod

    return {}


def _tiempo_rollo_calibrado(cfg, ml_efectivos, ancho_m=1.52, pasadas=None, tinta_blanca=False, day_night=False, doble_saturacion=False, modo_velocidad='MAXIMA'):
    """Calcula tiempo de un rollo de 50 m usando la calibración más específica.

    Prioridad:
      1) calibración especial por pasadas (tinta blanca / Day & Night),
      2) calibración normal por pasadas y modo,
      3) calibración general del rollo.

    Las calibraciones especiales NO reciben multiplicadores adicionales.
    """
    if ml_efectivos <= 0:
        return 0.0

    modo = str(modo_velocidad or "MAXIMA").strip().upper()
    modo = "ESTANDAR" if modo in {"ESTÁNDAR", "ESTANDAR", "STANDARD", "NORMAL"} else "MAXIMA"

    base_min = None
    es_calibracion_especial = False

    # 1) ESPECIAL: debe tener prioridad sobre cualquier calibración normal.
    if pasadas is not None and tinta_blanca and cfg.get("rollo_50m_tinta_blanca_pasadas_min"):
        tabla = cfg.get("rollo_50m_tinta_blanca_pasadas_min", {}).get(modo, {})
        base_min = tabla.get(pasadas, tabla.get(str(pasadas)))
        es_calibracion_especial = base_min is not None

    if base_min is None and pasadas is not None and day_night and cfg.get("rollo_50m_day_night_pasadas_min"):
        tabla = cfg.get("rollo_50m_day_night_pasadas_min", {}).get(modo, {})
        base_min = tabla.get(pasadas, tabla.get(str(pasadas)))
        es_calibracion_especial = base_min is not None

    # 2) NORMAL: calibración por ancho/pasadas.
    if base_min is None:
        por_ancho = cfg.get("rollo_50m_por_ancho") or {}
        ancho_key = f"{float(ancho_m):.2f}"
        datos = por_ancho.get(ancho_key)
        if isinstance(datos, dict) and pasadas is not None:
            clave = f"{int(pasadas)}_DOBLE" if doble_saturacion else str(int(pasadas))
            base_min = datos.get(clave)
        elif datos is not None and not isinstance(datos, dict):
            base_min = datos

    if base_min is None and pasadas is not None:
        tabla = (cfg.get("rollo_50m_pasadas_min_estandar") or {}) if modo == "ESTANDAR" else (cfg.get("rollo_50m_pasadas_min") or {})
        base_min = tabla.get(pasadas, tabla.get(str(pasadas)))

    # 3) FALLBACK: tiempo general del rollo.
    if base_min is None:
        if tinta_blanca and cfg.get("rollo_50m_tinta_blanca_min") is not None:
            base_min = cfg.get("rollo_50m_tinta_blanca_min")
        elif cfg.get("rollo_50m_min") is not None:
            base_min = cfg.get("rollo_50m_min")

    if base_min is None:
        return 0.0

    minutos = (ml_efectivos / 50.0) * _numero_seguro(base_min, 0)

    if not es_calibracion_especial:
        if tinta_blanca and cfg.get("multiplicador_tinta_blanca") is not None:
            minutos *= _numero_seguro(cfg.get("multiplicador_tinta_blanca"), 1)
        if day_night and cfg.get("multiplicador_day_night") is not None:
            minutos *= _numero_seguro(cfg.get("multiplicador_day_night"), 1)

    return minutos


def _compensacion_rigido_corto(maquina, modo, laminas, tiempo_base):
    """Compensa tiempos de arranque/preparación en tirajes rígidos cortos.

    La calibración de 40 láminas nunca se modifica. Los puntos de compensación
    se definen por máquina y modo; actualmente solo VUTEK PRO tiene puntos
    reales confirmados:
      - 2 láminas / 24 pasadas / ESTÁNDAR = 14 min
      - 2 láminas / 24 pasadas / MÁXIMA ≈ 9 min
    La compensación cae linealmente hasta 0 al llegar a 40 láminas.
    """
    if laminas <= 0 or laminas >= 40 or tiempo_base <= 0:
        return tiempo_base

    maquina_norm = str(maquina or "").strip().upper()
    modo_norm = "ESTANDAR" if str(modo or "").strip().upper() in {"ESTÁNDAR", "ESTANDAR", "STANDARD", "NORMAL"} else "MAXIMA"

    puntos = {
        "VUTEK PRO": {
            "ESTANDAR": 6.41,
            "MAXIMA": 3.35,
        },
    }
    compensacion_2 = _numero_seguro(puntos.get(maquina_norm, {}).get(modo_norm), 0)
    if compensacion_2 <= 0:
        return tiempo_base

    proporcion = (40.0 - float(laminas)) / 38.0
    return tiempo_base + compensacion_2 * max(0.0, min(1.0, proporcion))


def calcular_tiempo_produccion(
    maquina, material, cantidad_m2=0, cantidad_laminas=0, pasadas=None,
    tinta_blanca=False, day_night=False, modo_velocidad="MAXIMA",
    metros_lineales=0.0, cantidad_copias=1, ancho_material_m=1.52, doble_saturacion=False
):
    """Calcula el tiempo de impresión.

    FLEXIBLE:
      - ancho operativo fijo de 1.52 m.
      - las copias se deducen automáticamente del metraje entero.
        Ej.: 3.0 m -> 3 copias; 3.5 m -> 3 copias + 0.50 m restante.
      - la ganancia entre copias se descuenta una sola vez por cada espacio
        entre copias.

    RÍGIDO:
      - cada lámina es una copia de 1.22 x 2.44 m.
      - VUTEK PRO/F4 pueden usar calibración directa de láminas/hora cuando
        existe en configuración (actualmente 12 pasadas = 40 láminas/h).
      - si no existe calibración directa, se utiliza el cálculo por m².

    ROUTERS no pasan por esta función; su cálculo sigue siendo por corte.
    """
    if not maquina:
        return 0.0

    cfg = _config_produccion_maquina(maquina)
    unidad = str(cfg.get("unidad", "M2")).strip().upper()
    modo = str(modo_velocidad or "MAXIMA").strip().upper()
    modo = "ESTANDAR" if modo in {"ESTÁNDAR", "ESTANDAR", "STANDARD", "NORMAL"} else "MAXIMA"
    material_norm = str(material or "").strip().upper()

    ml = max(0.0, _numero_seguro(metros_lineales, 0))

    # ------------------------------------------------------------
    # PROCESOS ESPECIALES: la calibración manda aunque el widget de
    # pasadas haya perdido su valor durante un rerun de Streamlit.
    # Esto evita que el tiempo quede en 0 por una selección normal
    # (12/16/24/32) que no corresponde al proceso especial.
    # ------------------------------------------------------------
    maquina_norm = str(maquina or "").strip().upper()
    if material_norm == "FLEXIBLE" and maquina_norm == "VUTEK PRO":
        if tinta_blanca and not day_night:
            pasadas = 48
        elif day_night and not tinta_blanca:
            pasadas = 72

    if material_norm == "FLEXIBLE" and maquina_norm in {"EPSON 1", "EPSON 2"} and tinta_blanca:
        pasadas = 12

    ganancia = max(0.0, _numero_seguro(cfg.get("ganancia_entre_copias_m", 0), 0))

    # ------------------------------------------------------------
    # FLEXIBLE: copias automáticas según los metros enteros
    # ------------------------------------------------------------
    if material_norm == "FLEXIBLE":
        if ml <= 0 and cantidad_m2:
            ml = _numero_seguro(cantidad_m2, 0) / 1.52

        # No se pide al operador. Para 3.5 m son 3 copias y 0.50 m extra.
        copias_auto = int(ml)
        if ml > 0 and copias_auto == 0:
            copias_auto = 1
        copias = max(1, copias_auto) if ml > 0 else 0

        ml_efectivos = max(0.0, ml - ganancia * max(0, copias - 1))

    # ------------------------------------------------------------
    # RÍGIDO: cada lámina es una copia
    # ------------------------------------------------------------
    elif material_norm in {"RÍGIDO", "RIGIDO"} and cantidad_laminas:
        laminas = max(0, int(cantidad_laminas or 0))
        copias = laminas
        ml = float(laminas) * LARGO_LAMINA_RIGIDA_M

        # Calibraciones especiales de VUTEK PRO en rígido:
        # referencia exacta de 40 láminas de 1.22 x 2.44 m.
        # NO se aplican multiplicadores adicionales porque los tiempos ya
        # son mediciones reales del proceso especial.
        maquina_norm_rigido = str(maquina or "").strip().upper()
        tabla_especial_40 = None
        if maquina_norm_rigido == "VUTEK PRO" and tinta_blanca and not day_night:
            pasadas = 48
            tabla_especial_40 = cfg.get("tiempo_40_laminas_tinta_blanca_pasadas_min") or {}
        elif maquina_norm_rigido == "VUTEK PRO" and day_night and not tinta_blanca:
            pasadas = 72
            tabla_especial_40 = cfg.get("tiempo_40_laminas_day_night_pasadas_min") or {}

        if tabla_especial_40 is not None:
            tabla_modo_especial = tabla_especial_40.get(modo) or tabla_especial_40.get("MAXIMA") or {}
            base_especial_40 = tabla_modo_especial.get(pasadas, tabla_modo_especial.get(str(pasadas)))
            if base_especial_40 is not None and _numero_seguro(base_especial_40, 0) > 0:
                tiempo_base = (laminas / 40.0) * _numero_seguro(base_especial_40, 0)
                return _compensacion_rigido_corto(maquina, modo, laminas, tiempo_base)

        # NUEVAS REFERENCIAS DIRECTAS: 1 a 20 láminas.
        # Cuando existe un dato real para la cantidad solicitada, se usa tal cual.
        # No se aplica la compensación anterior sobre estos puntos calibrados.
        tabla_directa = cfg.get("tiempo_laminas_pasadas_min") or {}
        tabla_modo_directa = tabla_directa.get(modo) or {}
        tabla_pasadas_directa = (
            tabla_modo_directa.get(pasadas, tabla_modo_directa.get(str(pasadas)))
            if pasadas is not None else None
        )
        if isinstance(tabla_pasadas_directa, dict):
            tiempo_directo = tabla_pasadas_directa.get(
                laminas, tabla_pasadas_directa.get(str(laminas))
            )
            if tiempo_directo is not None and _numero_seguro(tiempo_directo, 0) > 0:
                return _numero_seguro(tiempo_directo, 0)

        # Calibración histórica de 40 láminas para cantidades sin referencia nueva.
        tabla_40 = cfg.get("tiempo_40_laminas_pasadas_min") or {}
        tabla_modo = tabla_40.get(modo) or tabla_40.get("MAXIMA") or {}
        base_40 = None
        if pasadas is not None:
            base_40 = tabla_modo.get(pasadas, tabla_modo.get(str(pasadas)))

        if base_40 is not None and _numero_seguro(base_40, 0) > 0:
            minutos = (laminas / 40.0) * _numero_seguro(base_40, 0)

            if tinta_blanca and cfg.get("multiplicador_tinta_blanca") is not None:
                minutos *= _numero_seguro(cfg.get("multiplicador_tinta_blanca"), 1)
            if day_night and cfg.get("multiplicador_day_night") is not None:
                minutos *= _numero_seguro(cfg.get("multiplicador_day_night"), 1)
            return _compensacion_rigido_corto(maquina, modo, laminas, minutos)

        # Compatibilidad con calibraciones antiguas por láminas/hora.
        tabla_h = cfg.get("laminas_por_hora_pasadas") or {}
        rate_h = None
        if pasadas is not None and modo == "MAXIMA":
            rate_h = tabla_h.get(pasadas, tabla_h.get(str(pasadas)))
        if rate_h is not None and _numero_seguro(rate_h, 0) > 0:
            minutos = laminas * 60.0 / _numero_seguro(rate_h, 0)
            if tinta_blanca and cfg.get("multiplicador_tinta_blanca") is not None:
                minutos *= _numero_seguro(cfg.get("multiplicador_tinta_blanca"), 1)
            if day_night and cfg.get("multiplicador_day_night") is not None:
                minutos *= _numero_seguro(cfg.get("multiplicador_day_night"), 1)
            return _compensacion_rigido_corto(maquina, modo, laminas, minutos)

        # Fallback: cálculo tradicional por m², pero conservando la ganancia.
        ml_efectivos = max(0.0, ml - ganancia * max(0, copias - 1))

    else:
        copias = max(1, int(_numero_seguro(cantidad_copias, 1)))
        if ml > 0:
            ml_efectivos = max(0.0, ml - ganancia * max(0, copias - 1))
        else:
            ml_efectivos = 0.0

    # ------------------------------------------------------------
    # CALIBRACIONES REALES POR ROLLO (FLEXIBLE)
    # ------------------------------------------------------------
    if material_norm == "FLEXIBLE":
        # Las calibraciones de rollo son mediciones reales de 50 m continuos.
        # Por eso se usa el metraje solicitado sin descontar la ganancia entre
        # copias: esa ganancia se reserva para las VUTEK de cama continua.
        ml_calibrado = ml if ml > 0 else ml_efectivos
        tiempo_rollo = _tiempo_rollo_calibrado(
            cfg,
            ml_calibrado,
            ancho_m=ancho_material_m or 1.52,
            pasadas=pasadas,
            tinta_blanca=tinta_blanca,
            day_night=day_night,
            doble_saturacion=doble_saturacion,
            modo_velocidad=modo,
        )
        if tiempo_rollo > 0:
            return tiempo_rollo

    # ------------------------------------------------------------
    # XEROX / HOJA
    # ------------------------------------------------------------
    if unidad == "HOJA":
        hojas = max(0, int(cantidad_laminas or 0))
        return hojas * _numero_seguro(cfg.get("min_por_hoja"), 0)

    # ------------------------------------------------------------
    # VUTEK PRO/F4: ML a ancho de referencia 1.52 m
    # ------------------------------------------------------------
    if unidad == "ML":
        tabla_max = cfg.get("min_por_ml_pasadas") or cfg.get("min_por_m2_pasadas") or {}
        tabla_std = cfg.get("min_por_ml_pasadas_estandar") or cfg.get("min_por_m2_pasadas_estandar") or {}
        rate = None
        if pasadas is not None:
            tabla = tabla_std if modo == "ESTANDAR" and tabla_std else tabla_max
            rate = tabla.get(pasadas, tabla.get(str(pasadas)))
        if rate is None:
            rate = cfg.get("min_por_ml", cfg.get("min_por_m2", 0))
        rate = _numero_seguro(rate, 0)
        if rate <= 0 or ml_efectivos <= 0:
            return 0.0
        minutos = ml_efectivos * rate

    # ------------------------------------------------------------
    # RESTO: m² usando metraje efectivo
    # ------------------------------------------------------------
    else:
        if material_norm in {"RÍGIDO", "RIGIDO"} and cantidad_laminas:
            ancho = ANCHO_LAMINA_RIGIDA_M
            m2_efectivos = ml_efectivos * ancho
        elif ml_efectivos > 0:
            m2_efectivos = ml_efectivos * 1.52
        else:
            m2_efectivos = max(0.0, _numero_seguro(cantidad_m2, 0))

        if m2_efectivos <= 0:
            return 0.0

        tabla_max = cfg.get("min_por_m2_pasadas") or cfg.get("min_por_m2_por_pasadas") or {}
        tabla_std = cfg.get("min_por_m2_pasadas_estandar") or {}
        rate = None
        if pasadas is not None:
            tabla = tabla_std if modo == "ESTANDAR" and tabla_std else tabla_max
            rate = tabla.get(pasadas, tabla.get(str(pasadas)))
        if rate is None:
            rate = (cfg.get("min_por_m2_tinta_blanca")
                    if tinta_blanca and cfg.get("min_por_m2_tinta_blanca") is not None
                    else cfg.get("min_por_m2", 0))
        rate = _numero_seguro(rate, 0)
        if rate <= 0:
            return 0.0
        minutos = m2_efectivos * rate

    if tinta_blanca and cfg.get("multiplicador_tinta_blanca") is not None and cfg.get("min_por_m2_tinta_blanca") is None:
        minutos *= _numero_seguro(cfg.get("multiplicador_tinta_blanca"), 1)
    if day_night and cfg.get("multiplicador_day_night") is not None:
        minutos *= _numero_seguro(cfg.get("multiplicador_day_night"), 1)
    return minutos


def calcular_tiempo_corte(maquina_router, tipo_corte, cantidad_cortes=0):
    if not maquina_router or not tipo_corte:
        return 0.0

    cfg = _config_produccion_maquina(maquina_router)
    tabla = cfg.get("min_por_corte") or cfg.get("tiempo_por_corte") or {}
    tipo = str(tipo_corte).strip().upper()
    rate = tabla.get(tipo, tabla.get(str(tipo_corte), 0))
    return max(0.0, _numero_seguro(rate)) * max(0, int(cantidad_cortes or 0))


def estimar_produccion(
    maquina,
    maquina_router,
    material,
    tipo_proceso,
    cantidad_m2,
    cantidad_laminas,
    pasadas,
    tinta_blanca,
    day_night,
    tipo_corte,
    cantidad_cortes,
    modo_velocidad="MAXIMA",
    metros_lineales=0.0, cantidad_copias=1, ancho_material_m=1.52, doble_saturacion=False
):
    """
    Devuelve:

        (min_impresion, min_corte, min_total)

    Todos los tiempos están expresados en minutos.
    """

    tipo_proceso = str(
        tipo_proceso or "IMPRESION"
    ).upper()

    material_norm = str(
        material or ""
    ).strip().upper()

    # ============================================================
    # ÁREA
    # ============================================================

    m2 = max(
        0.0,
        _numero_seguro(cantidad_m2)
    )

    # Fallback para instalaciones antiguas.
    if (
        material_norm == "RÍGIDO"
        and cantidad_laminas
        and m2 <= 0
    ):
        cfg = _config_produccion_maquina(
            maquina
        )

        area_lamina = _numero_seguro(
            cfg.get("m2_por_lamina"),
            0
        )

        if area_lamina > 0:
            m2 = (
                float(cantidad_laminas)
                * area_lamina
            )

    # ============================================================
    # IMPRESIÓN
    # ============================================================

    min_imp = 0.0

    if tipo_proceso != "SOLO CORTE":

        min_imp = calcular_tiempo_produccion(
            maquina=maquina,
            material=material,
            cantidad_m2=m2,
            cantidad_laminas=cantidad_laminas,
            pasadas=pasadas,
            tinta_blanca=tinta_blanca,
            day_night=day_night,
            modo_velocidad=modo_velocidad,
            metros_lineales=metros_lineales, cantidad_copias=cantidad_copias,
            ancho_material_m=ancho_material_m,
            doble_saturacion=doble_saturacion
        )

    # ============================================================
    # CORTE
    # ============================================================

    min_corte = 0.0

    if tipo_proceso in {
        "IMPRESION + CORTE",
        "SOLO CORTE"
    }:

        min_corte = calcular_tiempo_corte(
            maquina_router,
            tipo_corte,
            cantidad_cortes
        )

    # ============================================================
    # TOTAL
    # ============================================================

    min_total = (
        min_imp
        + min_corte
    )

    return (
        min_imp,
        min_corte,
        min_total
    )


def opciones_pasadas_para_maquina(nombre_maquina, tinta_blanca=False, day_night=False):
    cfg = _config_produccion_maquina(nombre_maquina)
    tablas = [
        cfg.get("rollo_50m_pasadas_min") or {},
        cfg.get("rollo_50m_pasadas_min_estandar") or {},
        cfg.get("min_por_m2_pasadas") or {},
        cfg.get("min_por_m2_pasadas_estandar") or {},
    ]

    # Las máquinas rígidas (por ejemplo VUTEK PRO/F4) guardan las pasadas
    # dentro de tablas por modo: {"MAXIMA": {12: ...}, "ESTANDAR": {...}}.
    # Antes solo se revisaban tablas planas, por eso el selector de Pasadas
    # podía desaparecer aunque la calibración sí existiera.
    tabla_40 = cfg.get("tiempo_40_laminas_pasadas_min") or {}
    if isinstance(tabla_40, dict):
        for subtabla in tabla_40.values():
            if isinstance(subtabla, dict):
                tablas.append(subtabla)

    # DURST 312 guarda sus tiempos por ancho y dentro de cada ancho
    # tiene las pasadas 4/6 y las variantes *_DOBLE.
    # Si no recorremos esta estructura, el selector de pasadas queda vacío
    # y el cálculo de tiempo puede terminar en 0 min.
    por_ancho = cfg.get("rollo_50m_por_ancho") or {}
    if isinstance(por_ancho, dict):
        for datos_ancho in por_ancho.values():
            if isinstance(datos_ancho, dict):
                tablas.append(datos_ancho)

    # También contemplamos calibraciones especiales organizadas por modo.
    for clave in (
        "tiempo_40_laminas_tinta_blanca_pasadas_min",
        "tiempo_40_laminas_day_night_pasadas_min",
    ):
        tabla_especial = cfg.get(clave) or {}
        if isinstance(tabla_especial, dict):
            for subtabla in tabla_especial.values():
                if isinstance(subtabla, dict):
                    tablas.append(subtabla)
    if tinta_blanca:
        tablas.extend((cfg.get("rollo_50m_tinta_blanca_pasadas_min") or {}).values())
        tablas.extend((cfg.get("tiempo_40_laminas_tinta_blanca_pasadas_min") or {}).values())
    if day_night:
        tablas.extend((cfg.get("rollo_50m_day_night_pasadas_min") or {}).values())
        tablas.extend((cfg.get("tiempo_40_laminas_day_night_pasadas_min") or {}).values())
    valores = set()
    for tabla in tablas:
        for k in tabla.keys():
            try:
                valores.add(int(k))
            except (TypeError, ValueError):
                pass
    return sorted(valores)


def calcular_area_produccion(material, metros_lineales=0.0, ancho_m=0.0,
                             cantidad_laminas=0, cantidad_m2=0.0,
                             unidad_ancho="M"):
    """Calcula estrictamente el área real en m² según el material."""
    material = str(material or "").strip().upper()

    if material == "FLEXIBLE":
        metros = max(0.0, float(metros_lineales or 0))
        ancho = max(0.0, float(ancho_m or 0))
        unidad = str(unidad_ancho or "M").strip().upper()
        if unidad in {"CM", "CENTIMETROS", "CENTÍMETROS"}:
            ancho /= 100.0
        elif unidad in {"MM", "MILIMETROS", "MILÍMETROS"}:
            ancho /= 1000.0
        return metros * ancho

    elif material == "RÍGIDO":
        return max(0.0, float(cantidad_laminas or 0) * M2_POR_LAMINA_RIGIDA)

    return max(0.0, float(cantidad_m2 or 0))


def etiqueta_area_rigida(cantidad_laminas):
    area = float(cantidad_laminas or 0) * M2_POR_LAMINA_RIGIDA
    return f"{area:.2f} m²"

