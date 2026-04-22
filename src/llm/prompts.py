from __future__ import annotations

from src.data.business_snapshot import ResumenNegocio


MENSAJE_SISTEMA = """Eres un analista de negocio para un restaurante o cadena local de comida.
Responde solo con el contexto recibido.
No inventes cifras, periodos ni causas.
Si infieres algo, dilo como hipótesis plausible.

Devuelve JSON válido y nada más, con exactamente estas claves:
respuesta, pregunta, riesgos, acciones, metricas

Reglas:
- respuesta debe ser un string en español mexicano
- respuesta debe ser directa, humana y concreta
- respuesta debe tener máximo 90 palabras y máximo 3 oraciones
- no pongas tablas
- no pongas listas de objetos
- no pongas anomalías crudas
- no copies el contexto literal
- pregunta debe ser una sola pregunta útil y corta
- riesgos, acciones y metricas deben ser arreglos de strings cortos
"""


def _recortar(texto: str, limite: int) -> str:
    limpio = texto.strip()
    if len(limpio) <= limite:
        return limpio
    return limpio[:limite].rsplit(' ', 1)[0].strip()


def construir_mensajes(resumen_negocio: ResumenNegocio, mensaje_usuario: str, historial_chat: list[tuple[str, str]]) -> list[dict[str, str]]:
    lineas_historial: list[str] = []
    for turno_usuario, turno_asistente in historial_chat[-2:]:
        lineas_historial.append(f'Usuario: {turno_usuario}')
        lineas_historial.append(f'Asistente: {turno_asistente}')

    historial_texto = '\n'.join(lineas_historial) if lineas_historial else 'Sin historial previo.'
    historial_texto = _recortar(historial_texto, 900)
    contexto = _recortar(resumen_negocio.a_texto_contexto(), 4200)

    mensaje = f"""CONTEXTO
{contexto}

HISTORIAL
{historial_texto}

PREGUNTA
{mensaje_usuario}

Responde en español mexicano, con una respuesta breve, concreta y basada en datos.
Si preguntan por peores meses o periodos, menciona solo los más relevantes y por qué.
Si preguntan por causa principal, di la causa más probable y la evidencia principal.
"""
    return [
        {'role': 'system', 'content': MENSAJE_SISTEMA},
        {'role': 'user', 'content': mensaje},
    ]



def construir_mensajes_resumen(resumen_negocio: ResumenNegocio, historial_chat: list[tuple[str, str]]) -> list[dict[str, str]]:
    lineas_historial: list[str] = []
    for turno_usuario, turno_asistente in historial_chat[-8:]:
        lineas_historial.append(f'Usuario: {turno_usuario}')
        lineas_historial.append(f'Asistente: {turno_asistente}')

    historial_texto = '\n'.join(lineas_historial) if lineas_historial else 'Sin historial previo.'
    historial_texto = _recortar(historial_texto, 1600)
    contexto = _recortar(resumen_negocio.a_texto_contexto(), 3500)

    mensaje = f"""CONTEXTO
{contexto}

HISTORIAL DE LA CONVERSACIÓN
{historial_texto}

Haz un resumen ejecutivo breve, sin JSON, con este formato:

Puntos clave para decidir:
- ...
- ...
- ...

Prioridades inmediatas:
- ...
- ...

Riesgos a vigilar:
- ...
- ...
"""
    return [
        {
            'role': 'system',
            'content': 'Eres un analista de negocio. Resume para toma de decisiones con lenguaje claro, breve y accionable.'
        },
        {'role': 'user', 'content': mensaje},
    ]
