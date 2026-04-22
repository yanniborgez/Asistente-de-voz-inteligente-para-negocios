from __future__ import annotations

import sys
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_PROYECTO))

from src.audio.asr import ConfiguracionASR, ServicioASR
from src.audio.tts import ConfiguracionTTS, ServicioTTS
from src.config import cargar_configuracion
from src.llm.engine import ConfiguracionModelo, ModeloLocal


def iniciar() -> None:
    configuracion = cargar_configuracion(RAIZ_PROYECTO / 'config' / 'settings.yaml')

    modelo = ModeloLocal(ConfiguracionModelo(**configuracion.modelo), raiz_proyecto=RAIZ_PROYECTO)
    servicio_asr = ServicioASR(
        ConfiguracionASR(
            habilitar_asr=bool(configuracion.audio.get('habilitar_asr', True)),
            modelo_asr=str(configuracion.audio.get('modelo_asr', 'base')),
            dispositivo_asr=str(configuracion.audio.get('dispositivo_asr', 'cpu')),
            tipo_calculo_asr=str(configuracion.audio.get('tipo_calculo_asr', 'int8')),
            idioma_asr=configuracion.audio.get('idioma_asr', 'es'),
        ),
        raiz_proyecto=RAIZ_PROYECTO,
    )
    servicio_tts = ServicioTTS(
        ConfiguracionTTS(
            habilitar_tts=bool(configuracion.audio.get('habilitar_tts', True)),
            ruta_voz_tts=str(configuracion.audio.get('ruta_voz_tts', 'models/tts/voz.onnx')),
            ruta_configuracion_voz_tts=str(configuracion.audio.get('ruta_configuracion_voz_tts', 'models/tts/voz.onnx.json')),
            hablante_tts=int(configuracion.audio.get('hablante_tts', 0)),
            escala_longitud_tts=float(configuracion.audio.get('escala_longitud_tts', 1.0)),
            escala_ruido_tts=float(configuracion.audio.get('escala_ruido_tts', 0.667)),
            escala_ruido_w_tts=float(configuracion.audio.get('escala_ruido_w_tts', 0.8)),
        ),
        raiz_proyecto=RAIZ_PROYECTO,
        directorio_temporal=configuracion.resolver_ruta(configuracion.rutas.get('directorio_temporal', 'temp')),
    )

    for nombre, funcion in [('Modelo', modelo.calentar), ('Entrada de voz', servicio_asr.calentar), ('Salida de voz', servicio_tts.calentar)]:
        try:
            print(f'{nombre}: {funcion()}')
        except Exception as error:
            print(f'{nombre}: ERROR -> {error}')


if __name__ == '__main__':
    iniciar()
