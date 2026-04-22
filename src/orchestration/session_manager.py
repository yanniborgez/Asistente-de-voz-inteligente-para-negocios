from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.data.business_snapshot import ResumenNegocio


@dataclass
class SesionConjunto:
    nombre: str
    vista_previa_cruda: list[dict]
    mapa_esquema: dict[str, Any]
    vista_previa_indicadores: list[dict]
    resumen_negocio: ResumenNegocio


@dataclass
class SesionAplicacion:
    conjuntos: list[SesionConjunto] = field(default_factory=list)
    indice_conjunto_activo: int = 0
    historial_chat: list[tuple[str, str]] = field(default_factory=list)

    def limpiar_chat(self) -> None:
        self.historial_chat.clear()

    def conjunto_activo(self) -> Optional[SesionConjunto]:
        if not self.conjuntos:
            return None
        indice = max(0, min(self.indice_conjunto_activo, len(self.conjuntos) - 1))
        return self.conjuntos[indice]

    def a_historial_chatbot(self) -> list[dict[str, str]]:
        mensajes: list[dict[str, str]] = []
        for usuario, asistente in self.historial_chat:
            mensajes.append({'role': 'user', 'content': usuario})
            mensajes.append({'role': 'assistant', 'content': asistente})
        return mensajes

    def a_estado(self) -> dict[str, Any]:
        return {
            'conjuntos': [
                {
                    'nombre': conjunto.nombre,
                    'vista_previa_cruda': conjunto.vista_previa_cruda,
                    'mapa_esquema': conjunto.mapa_esquema,
                    'vista_previa_indicadores': conjunto.vista_previa_indicadores,
                    'resumen_negocio': conjunto.resumen_negocio.a_diccionario(),
                }
                for conjunto in self.conjuntos
            ],
            'indice_conjunto_activo': self.indice_conjunto_activo,
            'historial_chat': self.historial_chat,
        }
