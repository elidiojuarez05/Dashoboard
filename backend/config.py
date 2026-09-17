MACHINE_CONFIGS = {
    'EPSON 1': {
        'cols': 6,
        'rows': 100,
        'type': 'epson',
        'produccion': {
            'unidad': 'M2',
            'min_por_m2': 4.5394736842,
            'min_por_m2_tinta_blanca': 9.4736842105,
            # Registro con tinta blanca: rollo de 50 m x 1.52 m = 12 h.
            'rollo_50m_tinta_blanca_min': 720.0,
            'rollo_50m_tinta_blanca_pasadas_min': {
                'MAXIMA': {12: 720.0},
                'ESTANDAR': {12: 720.0},
            },
            'avance_continuo_m_por_ml': 0.02
        }
    },

    'EPSON 2': {
        'cols': 6,
        'rows': 100,
        'type': 'epson',
        'produccion': {
            'unidad': 'M2',
            'min_por_m2': 4.5394736842,
            'min_por_m2_tinta_blanca': 9.4736842105,
            # Registro con tinta blanca: rollo de 50 m x 1.52 m = 12 h.
            'rollo_50m_tinta_blanca_min': 720.0,
            'rollo_50m_tinta_blanca_pasadas_min': {
                'MAXIMA': {12: 720.0},
                'ESTANDAR': {12: 720.0},
            },
            'avance_continuo_m_por_ml': 0.02
        }
    },

    # ============================================================
    # VUTEK PRO
    # ============================================================
    'VUTEK PRO': {
        'cols': 46,
        'rows': 800,
        'type': 'standard',
        'threshold_constant': 7,
        'pixel_min_limit': 0.04,
        'use_dilation': False,

        'produccion': {
            'unidad': 'ML',
            'ancho_referencia_m': 1.52,
            'ancho_flexible_estandar_m': 1.52,
            'calculo_continuo': True,

            # FLEXIBLE — rollo de 50 m x 1.52 m.
            # Valores reales proporcionados por producción.
            'rollo_50m_pasadas_min': {
                12: 47.42,
                16: 61.80,
                24: 81.60,
                32: 123.60
            },
            'rollo_50m_pasadas_min_estandar': {
                12: 76.20,
                16: 93.60,
                24: 151.80,
                32: 211.00
            },

            # RÍGIDO — referencia: 40 láminas de 1.22 x 2.44 m.
            'tiempo_40_laminas_pasadas_min': {
                'MAXIMA': {12: 60.00, 16: 102.00, 24: 81.60, 32: 123.60},
                'ESTANDAR': {12: 87.60, 16: 93.60, 24: 151.80, 32: 211.00}
            },

            # RÍGIDO — TINTA BLANCA: referencia exacta de producción sobre
            # 40 láminas de 1.22 x 2.44 m. 3.47 h = 3 h 47 min;
            # 6.56 h = 6 h 56 min.
            'tiempo_40_laminas_tinta_blanca_pasadas_min': {
                'MAXIMA': {48: 227.00},
                'ESTANDAR': {48: 416.00},
            },

            # RÍGIDO — DAY & NIGHT: referencia exacta sobre 40 láminas.
            # 5.40 h = 5 h 40 min; 10.24 h = 10 h 24 min.
            'tiempo_40_laminas_day_night_pasadas_min': {
                'MAXIMA': {72: 340.00},
                'ESTANDAR': {72: 624.00},
            },

            'rollo_50m_tinta_blanca_pasadas_min': {
                'MAXIMA': {48: 184.80},
                'ESTANDAR': {48: 327.60},
            },
            'rollo_50m_day_night_pasadas_min': {
                'MAXIMA': {72: 421.80},
                'ESTANDAR': {72: 754.80},
            },
            'multiplicador_tinta_blanca': 2,
            'multiplicador_day_night': 3
        }
    },

    # ============================================================
    # VUTEK F4
    # ============================================================
    'VUTEK F4': {
        'rows': 700,
        'cols': 48,
        'type': 'standard',
        'threshold_constant': 7,
        'pixel_min_limit': 0.03,
        'use_dilation': False,

        'produccion': {
            'unidad': 'ML',
            'ancho_referencia_m': 1.52,
            'ancho_flexible_estandar_m': 1.52,
            'calculo_continuo': True,

            # FLEXIBLE — rollo de 50 m x 1.52 m.
            'rollo_50m_pasadas_min': {
                8: 32.00,
                12: 47.00,
                16: 61.80
            },
            'rollo_50m_pasadas_min_estandar': {
                8: 58.00,
                12: 76.20,
                16: 93.60
            },

            # RÍGIDO — referencia: 40 láminas de 1.22 x 2.44 m.
            'tiempo_40_laminas_pasadas_min': {
                'MAXIMA': {8: 38.00, 12: 57.00, 16: 69.60},
                'ESTANDAR': {8: 70.00, 12: 105.00, 16: 140.00}
            }
        }
    },


    # ============================================================
    # RESTO DE IMPRESORAS
    # ============================================================

    'VUTEK H5': {
        'cols': 40,
        'rows': 500,
        'type': 'standard',
        'threshold_constant': 6,
        'pixel_min_limit': 0.03,
        'use_blur': True,
        'ignore_empty_cols': False,
        'produccion': {
            'ancho_flexible_estandar_m': 1.52,
            'unidad': 'M2',
            'min_por_m2': 4,
            'avance_continuo_m_por_ml': 0.30
        }
    },

    'DURST 312': {
        'rows': 32,
        'cols': 8,
        'type': 'durst_block',
        'threshold_constant': 4,
        'pixel_min_limit': 0.23,
        'use_dilation': False,
        'use_blur': True,
        'produccion': {
            'ancho_flexible_estandar_m': 1.52,
            'unidad': 'M2',
            'avance_continuo_m_por_ml': 0.10,
            'min_por_m2_pasadas': {
                4: 0.85625,
                6: 1.40625,
                8: 9
            },
            'min_por_m2_pasadas_doble_saturacion': {
                4: 1.71875,
                6: 2.4375
            }
        }
    },

    'DURST P10 PLUS': {
        'rows': 128,
        'cols': 32,
        'type': 'durst_p10',
        'threshold_constant': 15,
        'pixel_min_limit': 0.35,
        'ignore_empty_cols': True,
        'use_dilation': False,
        'produccion': {
            'ancho_flexible_estandar_m': 1.52,
            'unidad': 'M2',
            'min_por_m2': 6,
            'min_por_m2_pasadas_flexible': {4: 4.0, 6: 6.0},
            'laminas_por_hora_pasadas': {4: 16.0, 6: 7.0},
            'avance_continuo_m_por_ml': 0.18
        }
    },

    'FAVUTEK': {
        'cols': 64,
        'rows': 100,
        'type': 'standard',
        'threshold_constant': 6,
        'pixel_min_limit': 0.23,
        'use_blur': True,
        'ignore_empty_cols': True,
        'produccion': {
            'ancho_flexible_estandar_m': 3.20,
            'ancho_referencia_m': 3.20,
            'unidad': 'ML',
            # Rollo real: 50 m x 3.20 m = 60 minutos.
            'calibracion_rollo_50m_min': 60.0,
            'avance_continuo_m_por_ml': 0.04
        }
    },

    'MIMAKI': {
        'cols': 32,
        'rows': 100,
        'type': 'standard',
        'produccion': {
            'ancho_flexible_estandar_m': 1.52,
            'unidad': 'M2',
            'min_por_m2': 1.5789473684,
            'calibracion_rollo_50m_min': 120.0,
            'avance_continuo_m_por_ml': 0.02
        }
    },

    'POLAROID': {
        'cols': 12,
        'rows': 160,
        'type': 'standard',
        'threshold_constant': 9.5,
        'pixel_min_limit': 0.05,
        'ignore_empty_cols': True,
        'use_blur': True,
        'block_width_factor': 0.8,
        'produccion': {
            'unidad': 'M2',
            'min_por_m2': 5
        }
    },

    'GRANDO': {
        'cols': 32,
        'rows': 137,
        'type': 'epson',
        'produccion': {
            'ancho_flexible_estandar_m': 1.52,
            'unidad': 'M2',
            'min_por_m2': 1.1842105263,
            'calibracion_rollo_50m': {1.52: 90.0, 2.50: 150.0, 3.20: 210.0},
            'avance_continuo_m_por_ml': 0.05
        }
    },

    'ALLWIN': {
        'cols': 32,
        'rows': 7232,
        'threshold_constant': 15,
        'pixel_min_limit': 0.35,
        'ignore_empty_cols': True,
        'use_dilation': False,
        'produccion': {
            'ancho_flexible_estandar_m': 1.52,
            'unidad': 'M2',
            'min_por_m2': 1.1842105263,
            'calibracion_rollo_50m': {1.52: 90.0, 3.20: 150.0},
            'avance_continuo_m_por_ml': 0.05
        }
    },

    # ============================================================
    # ROUTERS
    # ============================================================

    'Router Konsgberg': {
        'type': 'manual',
        'status_only': True,
        'produccion': {
            'tipos_corte': [
                'PLECA POR LAMINA',
                'BROCA CON DESBASTE',
                'CORTE COMPLETO STICKER',
                'NAVAJA TROVICEL 6MM',
                'NAVAJA SENCILLO',
                'NAVAJA COMPLEJIDAD MEDIO',
                # Compatibilidad con registros anteriores.
                'BROCA',
                'NAVAJA',
                'CORTE 45',
                'PLECA'
            ],
            'min_por_corte': {
                'PLECA POR LAMINA': 10.0,
                'BROCA CON DESBASTE': 60.0,
                'CORTE COMPLETO STICKER': 80.0,
                'NAVAJA TROVICEL 6MM': 15.0,
                'NAVAJA SENCILLO': 3.0,
                'NAVAJA COMPLEJIDAD MEDIO': 8.0,
                'BROCA': 60.0,
                'NAVAJA': 3.0,
                'CORTE 45': 8.0,
                'PLECA': 10.0
            }
        }
    },

    'Router Zund XL': {
        'type': 'manual',
        'status_only': True,
        'produccion': {
            'tipos_corte': [
                'PLECA POR LAMINA',
                'BROCA CON DESBASTE',
                'CORTE COMPLETO STICKER',
                'NAVAJA TROVICEL 6MM',
                'NAVAJA SENCILLO',
                'NAVAJA COMPLEJIDAD MEDIO',
                # Compatibilidad con registros anteriores.
                'BROCA',
                'NAVAJA',
                'CORTE 45',
                'PLECA'
            ],
            'min_por_corte': {
                'PLECA POR LAMINA': 10.0,
                'BROCA CON DESBASTE': 60.0,
                'CORTE COMPLETO STICKER': 80.0,
                'NAVAJA TROVICEL 6MM': 15.0,
                'NAVAJA SENCILLO': 3.0,
                'NAVAJA COMPLEJIDAD MEDIO': 8.0,
                'BROCA': 60.0,
                'NAVAJA': 3.0,
                'CORTE 45': 8.0,
                'PLECA': 10.0
            }
        }
    },

    'Router Zund G3': {
        'type': 'manual',
        'status_only': True,
        'produccion': {
            'tipos_corte': [
                'PLECA POR LAMINA',
                'BROCA CON DESBASTE',
                'CORTE COMPLETO STICKER',
                'NAVAJA TROVICEL 6MM',
                'NAVAJA SENCILLO',
                'NAVAJA COMPLEJIDAD MEDIO',
                # Compatibilidad con registros anteriores.
                'BROCA',
                'NAVAJA',
                'CORTE 45',
                'PLECA'
            ],
            'min_por_corte': {
                'PLECA POR LAMINA': 10.0,
                'BROCA CON DESBASTE': 60.0,
                'CORTE COMPLETO STICKER': 80.0,
                'NAVAJA TROVICEL 6MM': 15.0,
                'NAVAJA SENCILLO': 3.0,
                'NAVAJA COMPLEJIDAD MEDIO': 8.0,
                'BROCA': 60.0,
                'NAVAJA': 3.0,
                'CORTE 45': 8.0,
                'PLECA': 10.0
            }
        }
    },

    'Plotter Recorte': {
        'type': 'manual',
        'status_only': True,
        'produccion': {
            'uso': 'RECORTE DE VINIL',
            'materiales': ['VINIL'],
            'tipos_corte': ['RECORTE DE VINIL'],
            'min_por_corte': {
                'RECORTE DE VINIL': 8
            }
        }
    },

    # ============================================================
    # XEROX
    # ============================================================

    'XEROX': {
        'cols': 1,
        'rows': 1,
        'type': 'standard',
        'materiales': ['PAPEL COUCHÉ'],
        'produccion': {
            'unidad': 'HOJA',
            'min_por_hoja': 2
        }
    }
}

