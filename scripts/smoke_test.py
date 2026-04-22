from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.data.business_snapshot import ConstructorResumenNegocio
from src.data.kpi_engine import MotorIndicadores
from src.data.loader import CargadorCSV
from src.data.schema_mapper import MapeadorEsquema
from src.llm.engine import ConfiguracionModelo, ModeloLocal


def ejecutar_prueba(ruta_archivo: Path, pregunta: str) -> None:
    cargador = CargadorCSV()
    mapeador = MapeadorEsquema()
    motor = MotorIndicadores()
    constructor = ConstructorResumenNegocio()

    conjunto = cargador.cargar_uno(ruta_archivo)
    mapa = mapeador.mapear_dataframe(conjunto.tabla)
    resultado = motor.ejecutar(conjunto.tabla, mapa)
    resumen = constructor.construir(conjunto.nombre_origen, mapa, resultado)

    modelo = ModeloLocal(ConfiguracionModelo(modo='pruebas', ruta_modelo='models/llm/model.gguf'), raiz_proyecto=RAIZ)
    respuesta = modelo.generar(resumen, pregunta, [])

    print(f'=== {ruta_archivo.name} ===')
    print('Hallazgos:')
    for texto in resumen.observaciones[:4]:
        print('-', texto)
    print('\nRespuesta simulada de pruebas:')
    print(respuesta.a_markdown())
    print()


if __name__ == '__main__':
    ejecutar_prueba(RAIZ / 'examples' / 'comida_mensual_realista.csv', '¿Por qué cayeron los ingresos?')
    ejecutar_prueba(RAIZ / 'examples' / 'comida_operacion_compleja.csv', '¿Qué sucursal debería revisar primero?')
