from __future__ import annotations

import logging
from pathlib import Path


def configurar_registro(directorio_logs: Path, nivel: str = 'INFO') -> None:
    directorio_logs.mkdir(parents=True, exist_ok=True)
    ruta_log = directorio_logs / 'aplicacion.log'

    registrador_raiz = logging.getLogger()
    if registrador_raiz.handlers:
        return

    registrador_raiz.setLevel(getattr(logging, nivel.upper(), logging.INFO))

    formato = logging.Formatter(
        fmt='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    manejador_archivo = logging.FileHandler(ruta_log, encoding='utf-8')
    manejador_archivo.setFormatter(formato)

    manejador_consola = logging.StreamHandler()
    manejador_consola.setFormatter(formato)

    registrador_raiz.addHandler(manejador_archivo)
    registrador_raiz.addHandler(manejador_consola)
