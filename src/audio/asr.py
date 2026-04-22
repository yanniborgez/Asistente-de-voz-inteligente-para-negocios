from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

registrador = logging.getLogger(__name__)


@dataclass
class ConfiguracionASR:
    habilitar_asr: bool
    modelo_asr: str
    dispositivo_asr: str = 'cpu'
    tipo_calculo_asr: str = 'int8'
    idioma_asr: Optional[str] = 'es'


class ServicioASR:
    def __init__(self, configuracion: ConfiguracionASR, raiz_proyecto: Path) -> None:
        self.configuracion = configuracion
        self.raiz_proyecto = raiz_proyecto
        self._modelo = None

    def calentar(self) -> str:
        if not self.configuracion.habilitar_asr:
            return 'Reconocimiento de voz desactivado.'
        self._asegurar_carga()
        return f'Reconocimiento de voz listo con modelo {self.configuracion.modelo_asr}.'

    def transcribir(self, ruta_audio: str | Path) -> str:
        if not self.configuracion.habilitar_asr:
            raise RuntimeError('El reconocimiento de voz está desactivado en la configuración.')
        self._asegurar_carga()

        segmentos, informacion = self._modelo.transcribe(
            str(ruta_audio),
            beam_size=1,
            best_of=1,
            temperature=0.0,
            language=self.configuracion.idioma_asr,
            vad_filter=False,
            condition_on_previous_text=False,
            word_timestamps=False,
            initial_prompt='Conversación de negocio sobre ventas, costos, sucursales, ticket promedio y planes de acción.',
        )
        texto = ' '.join(segmento.text.strip() for segmento in segmentos if segmento.text.strip()).strip()
        registrador.info(
            'Idioma detectado=%s probabilidad=%.3f',
            getattr(informacion, 'language', 'n/d'),
            getattr(informacion, 'language_probability', 0.0),
        )
        return texto

    def _asegurar_carga(self) -> None:
        if self._modelo is not None:
            return
        try:
            from faster_whisper import WhisperModel
        except Exception as error:
            raise RuntimeError('No se pudo importar faster_whisper.') from error

        referencia_modelo = self.configuracion.modelo_asr
        ruta_candidata = Path(referencia_modelo)
        if not ruta_candidata.is_absolute():
            ruta_absoluta = (self.raiz_proyecto / referencia_modelo).resolve()
            if ruta_absoluta.exists():
                referencia_modelo = str(ruta_absoluta)

        registrador.info(
            'Cargando modelo de voz=%s dispositivo=%s tipo=%s',
            referencia_modelo,
            self.configuracion.dispositivo_asr,
            self.configuracion.tipo_calculo_asr,
        )
        self._modelo = WhisperModel(
            referencia_modelo,
            device=self.configuracion.dispositivo_asr,
            compute_type=self.configuracion.tipo_calculo_asr,
        )
