from __future__ import annotations

import unittest
from pathlib import Path

from src.data.business_snapshot import ConstructorResumenNegocio
from src.data.kpi_engine import MotorIndicadores
from src.data.loader import CargadorCSV
from src.data.schema_mapper import MapeadorEsquema
from src.llm.engine import ConfiguracionModelo, ModeloLocal


class PruebaFlujoNegocio(unittest.TestCase):
    def test_flujo_completo_mensual(self):
        raiz_proyecto = Path(__file__).resolve().parent.parent
        cargador = CargadorCSV()
        mapeador = MapeadorEsquema()
        motor = MotorIndicadores()
        constructor = ConstructorResumenNegocio()

        conjunto = cargador.cargar_uno(raiz_proyecto / 'examples' / 'comida_mensual_realista.csv')
        mapa = mapeador.mapear_dataframe(conjunto.tabla)
        resultado = motor.ejecutar(conjunto.tabla, mapa)
        resumen = constructor.construir(conjunto.nombre_origen, mapa, resultado)

        modelo = ModeloLocal(
            ConfiguracionModelo(modo='pruebas', ruta_modelo='models/llm/model.gguf'),
            raiz_proyecto=raiz_proyecto,
        )
        respuesta = modelo.generar(resumen, '¿Por qué cayeron los ingresos?', [])

        self.assertTrue(resumen.observaciones)
        self.assertTrue(respuesta.respuesta)
        self.assertIn('caída de ingresos', respuesta.respuesta.lower() if 'caída de ingresos' in respuesta.respuesta.lower() else 'caida de ingresos')
        self.assertIsInstance(respuesta.acciones, list)

    def test_flujo_completo_complejo(self):
        raiz_proyecto = Path(__file__).resolve().parent.parent
        cargador = CargadorCSV()
        mapeador = MapeadorEsquema()
        motor = MotorIndicadores()
        constructor = ConstructorResumenNegocio()

        conjunto = cargador.cargar_uno(raiz_proyecto / 'examples' / 'comida_operacion_compleja.csv')
        mapa = mapeador.mapear_dataframe(conjunto.tabla)
        resultado = motor.ejecutar(conjunto.tabla, mapa)
        resumen = constructor.construir(conjunto.nombre_origen, mapa, resultado)

        self.assertGreaterEqual(resultado.resumen['cantidad_periodos'], 6)
        self.assertTrue(resumen.contexto_avanzado.get('sucursales'))


if __name__ == '__main__':
    unittest.main()
