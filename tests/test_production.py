import unittest

from backend.services.production import (
    calcular_tiempo_produccion,
    calcular_tiempo_corte,
    estimar_produccion,
    calcular_area_produccion,
    opciones_pasadas_para_maquina,
)


class ProductionCalibrationTests(unittest.TestCase):
    def test_epson_50m_without_white(self):
        self.assertAlmostEqual(
            calcular_tiempo_produccion('EPSON 1', 'FLEXIBLE', metros_lineales=50, ancho_material_m=1.52),
            345.0,
            places=4,
        )

    def test_epson_50m_white(self):
        self.assertAlmostEqual(
            calcular_tiempo_produccion('EPSON 1', 'FLEXIBLE', metros_lineales=50, ancho_material_m=1.52, tinta_blanca=True),
            720.0,
            places=4,
        )

    def test_vutek_rigid_40_sheets_12_passes(self):
        self.assertAlmostEqual(
            calcular_tiempo_produccion('VUTEK PRO', 'RÍGIDO', cantidad_laminas=40, pasadas=12),
            60.0,
            places=4,
        )

    def test_vutek_f4_flexible_50m_max(self):
        # 50 m, 50 copies, 0.50 m gain -> 25.5 effective m.
        self.assertAlmostEqual(
            calcular_tiempo_produccion('VUTEK F4', 'FLEXIBLE', metros_lineales=50, pasadas=12, modo_velocidad='MAXIMA'),
            25.5 * 2.17,
            places=4,
        )

    def test_durst_312_roll_calibration(self):
        self.assertAlmostEqual(
            calcular_tiempo_produccion('DURST 312', 'FLEXIBLE', metros_lineales=50, ancho_material_m=3.20, pasadas=4),
            137.0,
            places=4,
        )
        self.assertAlmostEqual(
            calcular_tiempo_produccion('DURST 312', 'FLEXIBLE', metros_lineales=50, ancho_material_m=3.20, pasadas=6, doble_saturacion=True),
            390.0,
            places=4,
        )

    def test_p10_flexible_and_rigid(self):
        self.assertAlmostEqual(
            calcular_tiempo_produccion('DURST P10 PLUS', 'FLEXIBLE', metros_lineales=50, pasadas=4),
            120.0,
            places=4,
        )
        self.assertAlmostEqual(
            calcular_tiempo_produccion('DURST P10 PLUS', 'RÍGIDO', cantidad_laminas=16, pasadas=4),
            60.0,
            places=4,
        )

    def test_router_is_separate_from_print(self):
        imp, corte, total = estimar_produccion(
            'VUTEK F4', 'Router Zund XL', 'RÍGIDO', 'IMPRESION + CORTE',
            0, 1, 12, False, False, 'NAVAJA', 1,
        )
        self.assertGreater(imp, 0)
        self.assertEqual(corte, 4.0)
        self.assertAlmostEqual(total, imp + corte, places=4)
        self.assertEqual(calcular_tiempo_corte('Router Zund XL', 'NAVAJA', 1), 4.0)

    def test_area_rigid_is_standardized(self):
        self.assertAlmostEqual(calcular_area_produccion('RÍGIDO', cantidad_laminas=3), 3 * 1.22 * 2.44)

    def test_passes_are_integers(self):
        self.assertEqual(opciones_pasadas_para_maquina('VUTEK F4'), [8, 12, 16])
        self.assertEqual(opciones_pasadas_para_maquina('DURST 312'), [4, 6])


if __name__ == '__main__':
    unittest.main()
