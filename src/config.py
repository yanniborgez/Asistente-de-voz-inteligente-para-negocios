from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Configuracion:
    bruto: dict[str, Any]
    raiz_proyecto: Path

    def seccion(self, nombre: str) -> dict[str, Any]:
        return self.bruto.get(nombre, {})

    @property
    def aplicacion(self) -> dict[str, Any]:
        return self.seccion('aplicacion')

    @property
    def rutas(self) -> dict[str, Any]:
        return self.seccion('rutas')

    @property
    def modelo(self) -> dict[str, Any]:
        return self.seccion('modelo')

    @property
    def audio(self) -> dict[str, Any]:
        return self.seccion('audio')

    @property
    def negocio(self) -> dict[str, Any]:
        return self.seccion('negocio')

    @property
    def interfaz(self) -> dict[str, Any]:
        return self.seccion('interfaz')

    def resolver_ruta(self, ruta_relativa_o_absoluta: str) -> Path:
        ruta = Path(ruta_relativa_o_absoluta)
        if ruta.is_absolute():
            return ruta
        return (self.raiz_proyecto / ruta).resolve()

    def asegurar_directorios(self) -> None:
        for clave in (
            'directorio_datos',
            'directorio_temporal',
            'directorio_logs',
            'directorio_modelo',
            'directorio_asr',
            'directorio_tts',
        ):
            valor = self.rutas.get(clave)
            if valor:
                self.resolver_ruta(valor).mkdir(parents=True, exist_ok=True)


def cargar_configuracion(ruta_configuracion: str | os.PathLike[str]) -> Configuracion:
    ruta_configuracion = Path(ruta_configuracion).resolve()
    raiz_proyecto = ruta_configuracion.parent.parent if ruta_configuracion.parent.name == 'config' else ruta_configuracion.parent
    with ruta_configuracion.open('r', encoding='utf-8') as archivo:
        bruto = yaml.safe_load(archivo) or {}
    configuracion = Configuracion(bruto=bruto, raiz_proyecto=raiz_proyecto)
    configuracion.asegurar_directorios()
    return configuracion
