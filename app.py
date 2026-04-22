from __future__ import annotations

from pathlib import Path

from src.config import cargar_configuracion
from src.ui.gradio_app import construir_aplicacion
from src.utils.logging import configurar_registro


def iniciar() -> None:
    raiz_proyecto = Path(__file__).resolve().parent
    configuracion = cargar_configuracion(raiz_proyecto / 'config' / 'settings.yaml')
    configurar_registro(configuracion.resolver_ruta(configuracion.rutas.get('directorio_logs', 'logs')))
    aplicacion = construir_aplicacion(configuracion)
    aplicacion.launch(
        server_name=configuracion.aplicacion.get('host', '127.0.0.1'),
        server_port=int(configuracion.aplicacion.get('port', 7860)),
        share=bool(configuracion.aplicacion.get('share', False)),
        debug=bool(configuracion.aplicacion.get('debug', False)),
    )


if __name__ == '__main__':
    iniciar()
