from __future__ import annotations

from dataclasses import dataclass

from src.llm.engine import ModeloLocal
from src.llm.response_parser import RespuestaModelo
from src.orchestration.session_manager import SesionAplicacion


@dataclass
class ResultadoTurno:
    respuesta: RespuestaModelo
    markdown_completo: str


class GestorDialogo:
    def __init__(self, modelo: ModeloLocal) -> None:
        self.modelo = modelo

    def responder(self, sesion: SesionAplicacion, mensaje_usuario: str) -> ResultadoTurno:
        activo = sesion.conjunto_activo()
        if activo is None:
            respuesta = RespuestaModelo(
                respuesta='Primero carga y procesa un archivo antes de conversar.',
                pregunta='¿Qué archivo quieres revisar?',
            )
            return ResultadoTurno(respuesta=respuesta, markdown_completo=respuesta.a_markdown())

        respuesta = self.modelo.generar(
            resumen_negocio=activo.resumen_negocio,
            mensaje_usuario=mensaje_usuario,
            historial_chat=sesion.historial_chat,
        )
        sesion.historial_chat.append((mensaje_usuario, respuesta.a_markdown()))
        return ResultadoTurno(respuesta=respuesta, markdown_completo=respuesta.a_markdown())

    def resumir_conversacion(self, sesion: SesionAplicacion) -> str:
        activo = sesion.conjunto_activo()
        if activo is None:
            return 'No hay un archivo activo para resumir.'
        return self.modelo.resumir_conversacion(activo.resumen_negocio, sesion.historial_chat)
