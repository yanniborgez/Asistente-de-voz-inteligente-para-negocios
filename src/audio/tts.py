from __future__ import annotations

import logging
import re
import uuid
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

registrador = logging.getLogger(__name__)


@dataclass
class ConfiguracionTTS:
    habilitar_tts: bool
    ruta_voz_tts: str
    ruta_configuracion_voz_tts: str
    hablante_tts: int = 0
    escala_longitud_tts: float = 0.92
    escala_ruido_tts: float = 0.5
    escala_ruido_w_tts: float = 0.65


class ServicioTTS:
    def __init__(self, configuracion: ConfiguracionTTS, raiz_proyecto: Path, directorio_temporal: Path) -> None:
        self.configuracion = configuracion
        self.raiz_proyecto = raiz_proyecto
        self.directorio_temporal = directorio_temporal
        self._voz = None
        self._ruta_voz_resuelta: Path | None = None

    def calentar(self) -> str:
        if not self.configuracion.habilitar_tts:
            return 'Síntesis de voz desactivada.'
        self._asegurar_carga()
        return f'Síntesis de voz lista con {self._ruta_voz_resuelta.name if self._ruta_voz_resuelta else "voz local"}.'

    def sintetizar_a_archivo(self, texto: str) -> Optional[str]:
        if not self.configuracion.habilitar_tts:
            return None
        texto_limpio = self._normalizar_texto_para_voz(texto)
        if not texto_limpio:
            return None

        self._asegurar_carga()
        self.directorio_temporal.mkdir(parents=True, exist_ok=True)
        self._limpiar_archivos_antiguos()
        ruta_salida = self.directorio_temporal / f"respuesta_{uuid.uuid4().hex}.wav"

        try:
            from piper import SynthesisConfig
        except Exception as error:
            raise RuntimeError('No se pudo importar la configuración de Piper.') from error

        configuracion_sintesis = SynthesisConfig(
            speaker_id=self.configuracion.hablante_tts,
            length_scale=self.configuracion.escala_longitud_tts,
            noise_scale=self.configuracion.escala_ruido_tts,
            noise_w_scale=self.configuracion.escala_ruido_w_tts,
        )

        with wave.open(str(ruta_salida), 'wb') as archivo_wav:
            self._voz.synthesize_wav(texto_limpio, archivo_wav, syn_config=configuracion_sintesis)

        registrador.info('Audio generado en %s', ruta_salida)
        return str(ruta_salida)

    def _normalizar_texto_para_voz(self, texto: str) -> str:
        limpio = texto.strip()
        limpio = limpio.replace('**', '')
        limpio = limpio.replace('%', ' por ciento')
        limpio = limpio.replace('pp', ' puntos')
        limpio = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1', limpio)
        limpio = re.sub(r'^[\-•]\s*', '', limpio, flags=re.MULTILINE)
        limpio = limpio.replace('\n', '. ')
        limpio = re.sub(r'\s+', ' ', limpio)
        limpio = re.sub(r'\.\s*\.', '.', limpio)
        return limpio.strip(' .')

    def _asegurar_carga(self) -> None:
        if self._voz is not None:
            return

        try:
            from piper import PiperVoice
        except Exception as error:
            raise RuntimeError('No se pudo importar PiperVoice.') from error

        ruta_voz = self._resolver_ruta_voz()
        if not ruta_voz.exists():
            raise FileNotFoundError(f'No se encontró la voz en {ruta_voz}.')

        self._ruta_voz_resuelta = ruta_voz
        registrador.info('Cargando voz TTS desde %s', ruta_voz)
        self._voz = PiperVoice.load(str(ruta_voz))

    def _resolver_ruta_voz(self) -> Path:
        configurada = Path(self.configuracion.ruta_voz_tts)
        if not configurada.is_absolute():
            configurada = (self.raiz_proyecto / configurada).resolve()

        candidatos: list[Path] = []
        directorio_tts = configurada.parent
        if directorio_tts.exists():
            for patron in [
                'es_MX-claude-high.onnx',
                'es_MX-*-high.onnx',
                'es_MX-*-medium.onnx',
                '*.onnx',
            ]:
                candidatos.extend(sorted(directorio_tts.glob(patron)))

        if configurada.exists():
            nombre = configurada.name.lower()
            if 'ald-medium' in nombre:
                for candidato in candidatos:
                    if candidato.name != configurada.name:
                        return candidato
            return configurada

        if candidatos:
            return candidatos[0]
        return configurada

    def _limpiar_archivos_antiguos(self) -> None:
        if not self.directorio_temporal.exists():
            return
        archivos = sorted(
            self.directorio_temporal.glob('respuesta_*.wav'),
            key=lambda ruta: ruta.stat().st_mtime,
            reverse=True,
        )
        for archivo in archivos[8:]:
            try:
                archivo.unlink(missing_ok=True)
            except Exception:
                pass
