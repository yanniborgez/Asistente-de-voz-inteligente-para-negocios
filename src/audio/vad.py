from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DecisionVoz:
    hay_voz: bool
    motivo: str = 'En esta versión la detección se delega al motor de transcripción.'


class DetectorVozSimple:
    def inspeccionar(self, *_args, **_kwargs) -> DecisionVoz:
        return DecisionVoz(hay_voz=True)
