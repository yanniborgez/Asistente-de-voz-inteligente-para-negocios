from __future__ import annotations

import unittest

import pandas as pd

from src.data.schema_mapper import MapeadorEsquema


class PruebaMapeadorEsquema(unittest.TestCase):
    def test_detecta_columnas_basicas(self):
        tabla = pd.DataFrame(
            {
                'Fecha': ['2025-01', '2025-02'],
                'Ingresos_Brutos': [100, 110],
                'Costo de ventas': [40, 44],
                'Gastos Operativos': [20, 21],
            }
        )
        mapeador = MapeadorEsquema()
        mapa = mapeador.mapear_dataframe(tabla)
        self.assertEqual(mapa.columnas_mapeadas['periodo'], 'Fecha')
        self.assertEqual(mapa.columnas_mapeadas['ingresos'], 'Ingresos_Brutos')
        self.assertEqual(mapa.columnas_mapeadas['costo_ventas'], 'Costo de ventas')
        self.assertEqual(mapa.columnas_mapeadas['gasto_operativo'], 'Gastos Operativos')

    def test_no_toma_personal_como_costo_directo(self):
        tabla = pd.DataFrame(
            {
                'fecha': ['2025-01', '2025-02'],
                'ingresos_brutos': [100, 110],
                'costo_personal': [30, 32],
                'renta_local': [10, 10],
                'costo_insumos': [25, 28],
            }
        )
        mapeador = MapeadorEsquema()
        mapa = mapeador.mapear_dataframe(tabla)
        self.assertEqual(mapa.columnas_mapeadas['ingresos'], 'ingresos_brutos')
        self.assertEqual(mapa.columnas_mapeadas['costo_ventas'], 'costo_insumos')


if __name__ == '__main__':
    unittest.main()
