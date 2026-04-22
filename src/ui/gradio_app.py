from __future__ import annotations

import logging
from typing import Any

import gradio as gr
import pandas as pd

from src.audio.asr import ConfiguracionASR, ServicioASR
from src.audio.tts import ConfiguracionTTS, ServicioTTS
from src.config import Configuracion
from src.data.business_snapshot import ConstructorResumenNegocio
from src.data.kpi_engine import MotorIndicadores
from src.data.loader import CargadorCSV
from src.data.schema_mapper import MapeadorEsquema
from src.llm.engine import ConfiguracionModelo, ModeloLocal
from src.orchestration.dialogue_manager import GestorDialogo
from src.orchestration.session_manager import SesionAplicacion, SesionConjunto

registrador = logging.getLogger(__name__)


def construir_aplicacion(configuracion: Configuracion) -> gr.Blocks:
    cargador = CargadorCSV()
    mapeador = MapeadorEsquema()
    motor_indicadores = MotorIndicadores(umbral_z=float(configuracion.negocio.get('umbral_z', 1.5)))
    constructor_resumen = ConstructorResumenNegocio()
    modelo = ModeloLocal(
        configuracion=ConfiguracionModelo(
            modo=str(configuracion.modelo.get('modo', 'servidor_local')),
            ruta_modelo=str(configuracion.modelo.get('ruta_modelo', 'models/llm/model.gguf')),
            contexto=int(configuracion.modelo.get('contexto', 4096)),
            hilos=int(configuracion.modelo.get('hilos', 6)),
            lote=int(configuracion.modelo.get('lote', 256)),
            temperatura=float(configuracion.modelo.get('temperatura', 0.3)),
            maximo_tokens=int(configuracion.modelo.get('maximo_tokens', 140)),
            top_p=float(configuracion.modelo.get('top_p', 0.9)),
            penalizacion_repeticion=float(configuracion.modelo.get('penalizacion_repeticion', 1.08)),
            url_servidor=str(configuracion.modelo.get('url_servidor', 'http://127.0.0.1:8080/v1/chat/completions')),
            nombre_modelo_servidor=str(configuracion.modelo.get('nombre_modelo_servidor', 'modelo-local')),
            timeout_segundos=int(configuracion.modelo.get('timeout_segundos', 300)),
        ),
        raiz_proyecto=configuracion.raiz_proyecto,
    )
    gestor_dialogo = GestorDialogo(modelo=modelo)
    servicio_asr = ServicioASR(
        configuracion=ConfiguracionASR(
            habilitar_asr=bool(configuracion.audio.get('habilitar_asr', True)),
            modelo_asr=str(configuracion.audio.get('modelo_asr', 'base')),
            dispositivo_asr=str(configuracion.audio.get('dispositivo_asr', 'cpu')),
            tipo_calculo_asr=str(configuracion.audio.get('tipo_calculo_asr', 'int8')),
            idioma_asr=configuracion.audio.get('idioma_asr', 'es'),
        ),
        raiz_proyecto=configuracion.raiz_proyecto,
    )
    servicio_tts = ServicioTTS(
        configuracion=ConfiguracionTTS(
            habilitar_tts=bool(configuracion.audio.get('habilitar_tts', True)),
            ruta_voz_tts=str(configuracion.audio.get('ruta_voz_tts', 'models/tts/voz.onnx')),
            ruta_configuracion_voz_tts=str(configuracion.audio.get('ruta_configuracion_voz_tts', 'models/tts/voz.onnx.json')),
            hablante_tts=int(configuracion.audio.get('hablante_tts', 0)),
            escala_longitud_tts=float(configuracion.audio.get('escala_longitud_tts', 1.0)),
            escala_ruido_tts=float(configuracion.audio.get('escala_ruido_tts', 0.667)),
            escala_ruido_w_tts=float(configuracion.audio.get('escala_ruido_w_tts', 0.8)),
        ),
        raiz_proyecto=configuracion.raiz_proyecto,
        directorio_temporal=configuracion.resolver_ruta(configuracion.rutas.get('directorio_temporal', 'temp')),
    )

    maximo_filas = int(configuracion.negocio.get('maximo_filas_vista', 10))
    maximo_archivos = int(configuracion.negocio.get('maximo_archivos', 1))

    def nueva_sesion() -> SesionAplicacion:
        return SesionAplicacion()

    def estado(mensaje: str, tipo: str = 'normal') -> str:
        if tipo == 'error':
            return f"<div class='estado estado-error'>{mensaje}</div>"
        if tipo == 'ok':
            return f"<div class='estado estado-ok'>{mensaje}</div>"
        return f"<div class='estado'>{mensaje}</div>"

    def diagnostico_conjunto(sesion: SesionAplicacion) -> str:
        activo = sesion.conjunto_activo()
        if activo is None:
            return 'Carga un CSV y procésalo. Después podrás preguntar por voz y recibir respuesta con voz.'
        resumen = activo.resumen_negocio
        contexto = resumen.contexto_avanzado
        lineas = [f"## Diagnóstico de {activo.nombre}", '### Lo más relevante']
        lineas.extend(f'- {texto}' for texto in resumen.observaciones[:5] or ['Sin hallazgos todavía.'])
        if resumen.preguntas:
            lineas.append('\n### Preguntas sugeridas')
            lineas.extend(f'- {texto}' for texto in resumen.preguntas[:3])
        if resumen.acciones:
            lineas.append('\n### Acciones sugeridas')
            lineas.extend(f'- {texto}' for texto in resumen.acciones[:4])
        peor_sucursal = contexto.get('peor_sucursal')
        if peor_sucursal:
            lineas.append('\n### Foco inmediato')
            lineas.append(
                f"- {peor_sucursal['segmento']} | cambio ingresos {peor_sucursal['cambio_ingresos_pct']:.1f}% | margen operativo {peor_sucursal['margen_operativo_pct']:.1f}%"
            )
        causas = contexto.get('causas_ingresos', [])
        if causas:
            lineas.append('\n### Posibles causas de la baja')
            lineas.extend(f'- {texto}' for texto in causas[:3])
        momento = contexto.get('momento_critico', {})
        if momento:
            lineas.append(f"\n### Momento crítico: {momento.get('periodo')}")
            lineas.extend(f"- {texto}" for texto in momento.get('detalle', [])[:3])
        if resumen.observaciones_calidad:
            lineas.append('\n### Calidad de datos')
            lineas.extend(f'- {texto}' for texto in resumen.observaciones_calidad)
        return '\n'.join(lineas)

    def tablas_conjunto(sesion: SesionAplicacion):
        activo = sesion.conjunto_activo()
        if activo is None:
            return pd.DataFrame(), pd.DataFrame(), {}, diagnostico_conjunto(sesion)
        return (
            pd.DataFrame(activo.vista_previa_cruda),
            pd.DataFrame(activo.vista_previa_indicadores),
            activo.mapa_esquema,
            diagnostico_conjunto(sesion),
        )

    def sintetizar_respuesta(texto: str) -> str | None:
        if not texto.strip() or not bool(configuracion.audio.get('habilitar_tts', True)):
            return None
        try:
            return servicio_tts.sintetizar_a_archivo(texto)
        except Exception as error:
            registrador.exception('Fallo de audio de salida')
            raise RuntimeError(f'No se pudo generar el audio de salida: {error}') from error

    def procesar_archivos(archivo_entrada: Any, sesion: SesionAplicacion):
        if not archivo_entrada:
            tabla_cruda, tabla_indicadores, mapa, detalle = tablas_conjunto(sesion)
            return sesion, gr.Dropdown(choices=[], value=None), tabla_cruda, tabla_indicadores, mapa, detalle, [], None, estado('Selecciona un archivo CSV.', 'error'), ''

        ruta = archivo_entrada.name if hasattr(archivo_entrada, 'name') else str(archivo_entrada)
        conjuntos = cargador.cargar_varios([ruta][:maximo_archivos])
        sesion.conjuntos.clear()
        sesion.historial_chat.clear()

        for conjunto in conjuntos:
            mapa_esquema = mapeador.mapear_dataframe(conjunto.tabla)
            if mapa_esquema.faltantes_obligatorias:
                raise ValueError(f"El archivo '{conjunto.nombre_origen}' no tiene las columnas mínimas detectables: {mapa_esquema.faltantes_obligatorias}")
            resultado = motor_indicadores.ejecutar(conjunto.tabla, mapa_esquema)
            resumen = constructor_resumen.construir(conjunto.nombre_origen, mapa_esquema, resultado)
            sesion.conjuntos.append(
                SesionConjunto(
                    nombre=conjunto.nombre_origen,
                    vista_previa_cruda=conjunto.tabla.head(maximo_filas).to_dict(orient='records'),
                    mapa_esquema=mapa_esquema.a_diccionario_mostrable(),
                    vista_previa_indicadores=resultado.tabla_indicadores.head(maximo_filas).round(4).to_dict(orient='records'),
                    resumen_negocio=resumen,
                )
            )

        sesion.indice_conjunto_activo = 0
        opciones = [conjunto.nombre for conjunto in sesion.conjuntos]
        tabla_cruda, tabla_indicadores, mapa, detalle = tablas_conjunto(sesion)
        return (
            sesion,
            gr.Dropdown(choices=opciones, value=opciones[0]),
            tabla_cruda,
            tabla_indicadores,
            mapa,
            detalle,
            [],
            None,
            estado('Archivo listo. Ahora habla o escribe tu pregunta y te responderé también con voz.', 'ok'),
            '',
        )

    def cambiar_conjunto(eleccion: str | None, sesion: SesionAplicacion):
        if not eleccion or not sesion.conjuntos:
            tabla_cruda, tabla_indicadores, mapa, detalle = tablas_conjunto(sesion)
            return sesion, tabla_cruda, tabla_indicadores, mapa, detalle, estado('No hay un archivo activo.', 'error'), None
        for indice, conjunto in enumerate(sesion.conjuntos):
            if conjunto.nombre == eleccion:
                sesion.indice_conjunto_activo = indice
                break
        tabla_cruda, tabla_indicadores, mapa, detalle = tablas_conjunto(sesion)
        return sesion, tabla_cruda, tabla_indicadores, mapa, detalle, estado(f'Archivo activo: {eleccion}', 'ok'), None

    def enviar_texto(mensaje: str, sesion: SesionAplicacion):
        if not mensaje or not mensaje.strip():
            return sesion, sesion.a_historial_chatbot(), None, estado('Escribe una pregunta o usa el bloque de voz.', 'error'), ''
        try:
            resultado = gestor_dialogo.responder(sesion, mensaje.strip())
        except Exception as error:
            registrador.exception('Fallo al responder texto')
            return sesion, sesion.a_historial_chatbot(), None, estado(str(error), 'error'), ''
        ruta_audio = None
        try:
            ruta_audio = sintetizar_respuesta(resultado.respuesta.respuesta)
        except Exception as error:
            return sesion, sesion.a_historial_chatbot(), None, estado(str(error), 'error'), ''
        return sesion, sesion.a_historial_chatbot(), ruta_audio, estado('Respuesta lista.', 'ok'), ''

    def responder_por_voz(ruta_audio: str | None, sesion: SesionAplicacion):
        if not ruta_audio:
            return sesion, sesion.a_historial_chatbot(), None, '', estado('Primero graba tu pregunta.', 'error')
        try:
            texto = servicio_asr.transcribir(ruta_audio)
        except Exception as error:
            registrador.exception('Fallo de transcripción')
            return sesion, sesion.a_historial_chatbot(), None, '', estado(f'No se pudo transcribir el audio: {error}', 'error')
        if not texto.strip():
            return sesion, sesion.a_historial_chatbot(), None, '', estado('No pude entender el audio. Habla un poco más cerca del micrófono.', 'error')
        try:
            resultado = gestor_dialogo.responder(sesion, texto)
        except Exception as error:
            registrador.exception('Fallo al responder voz')
            mensaje_error = str(error)
            if 'No pude consultar el LLM local' in mensaje_error:
                mensaje_error = 'La respuesta tardó demasiado. Haz preguntas más cortas o vuelve a intentar en texto.'
            return sesion, sesion.a_historial_chatbot(), None, texto, estado(mensaje_error, 'error')
        ruta_audio_respuesta = None
        try:
            ruta_audio_respuesta = sintetizar_respuesta(resultado.respuesta.respuesta)
        except Exception as error:
            mensaje_error = str(error)
            if 'No pude consultar el LLM local' in mensaje_error:
                mensaje_error = 'La respuesta tardó demasiado. Haz preguntas más cortas o vuelve a intentar en texto.'
            return sesion, sesion.a_historial_chatbot(), None, texto, estado(mensaje_error, 'error')
        return sesion, sesion.a_historial_chatbot(), ruta_audio_respuesta, texto, estado('Respuesta lista.', 'ok')

    def resumir_conversacion(sesion: SesionAplicacion):
        try:
            texto = gestor_dialogo.resumir_conversacion(sesion)
        except Exception as error:
            registrador.exception('Fallo al resumir conversación')
            return '', None, estado(str(error), 'error')
        ruta_audio = None
        try:
            ruta_audio = sintetizar_respuesta(texto)
        except Exception as error:
            return texto, None, estado(str(error), 'error')
        return texto, ruta_audio, estado('Resumen listo.', 'ok')

    def limpiar_chat(sesion: SesionAplicacion):
        sesion.limpiar_chat()
        return sesion, [], None, '', '', estado('Conversación limpia.', 'ok')

    css = """
    footer {display: none !important;}
    .footer {display: none !important;}
    [data-testid="footer"] {display: none !important;}

    .gradio-container {max-width: 1600px !important;}
    .panel-principal, .panel-lateral {
        border: 1px solid #2f3136;
        border-radius: 18px;
        padding: 18px;
        background: #111318;
    }
    .estado {
        background: #171b22;
        border: 1px solid #2a2f39;
        border-radius: 12px;
        padding: 10px 12px;
        font-size: 14px;
    }
    .estado-ok {
        background: #13261b;
        border: 1px solid #295e3d;
        color: #d7f5df;
    }
    .estado-error {
        background: #2a1618;
        border: 1px solid #6f343a;
        color: #ffd9dd;
    }
    .titulo-voz {
        font-size: 15px;
        text-transform: uppercase;
        letter-spacing: .08em;
        color: #a9b0bc;
        margin-bottom: 6px;
    }
    .sub-voz {
        font-size: 28px;
        font-weight: 700;
        line-height: 1.2;
        margin-bottom: 10px;
    }
    .pasos {
        color: #d1d7e0;
        font-size: 15px;
        margin-bottom: 8px;
    }
    """

    with gr.Blocks(title=configuracion.aplicacion.get('titulo', 'Asistente de voz basado en datos'), css=css) as aplicacion:
        estado_sesion = gr.State(nueva_sesion())

        gr.HTML(
            "<div class='titulo-voz'>Análisis inteligente</div>"
            f"<div class='sub-voz'>{configuracion.aplicacion.get('titulo', 'Análisis inteligente')}</div>"
            "<div class='pasos'>Carga un CSV, procesa el diagnóstico y luego pregúntame tus dudas.</div>"
        )

        with gr.Row(equal_height=False):
            with gr.Column(scale=3, elem_classes='panel-principal'):
                with gr.Row():
                    archivo_csv = gr.File(file_count='single', file_types=['.csv'], label='Archivo CSV')
                    boton_procesar = gr.Button('Procesar archivo', variant='primary')
                selector_conjunto = gr.Dropdown(choices=[], value=None, label='Archivo activo')
                caja_estado = gr.HTML(value=estado(configuracion.interfaz.get('estado_inicial', 'Carga un CSV y procésalo.')))

                chat = gr.Chatbot(label='Conversación', height=430, type='messages')
                with gr.Row():
                    with gr.Column(scale=2):
                        entrada_audio = gr.Audio(sources=['microphone'], type='filepath', label='Pregunta por voz')
                    with gr.Column(scale=1):
                        transcripcion = gr.Textbox(label='Entendido', lines=4, interactive=False)
                with gr.Row():
                    boton_responder_voz = gr.Button('Responder por voz', variant='primary', size='lg')
                    boton_resumen = gr.Button('Resumen de decisiones')
                    boton_limpiar = gr.Button('Limpiar conversación')

                entrada_texto = gr.Textbox(
                    label='Pregunta escrita',
                    placeholder='Ej. ¿Cuál es la causa principal de la caída? / ¿Qué plan de 30 días propones?',
                    lines=3,
                )
                boton_enviar = gr.Button('Enviar texto')
                audio_salida = gr.Audio(label='Respuesta en voz', type='filepath', autoplay=True)
                resumen_final = gr.Markdown('')

            with gr.Column(scale=2, elem_classes='panel-lateral'):
                diagnostico = gr.Markdown('Carga un CSV y procésalo. Después podrás preguntar por voz y recibir una respuesta hablada.')
                with gr.Tabs():
                    with gr.TabItem('Indicadores'):
                        tabla_indicadores = gr.Dataframe(label='Indicadores consolidados', interactive=False)
                    with gr.TabItem('Archivo'):
                        tabla_cruda = gr.Dataframe(label='Vista previa del archivo', interactive=False)
                    with gr.TabItem('Columnas'):
                        json_mapa = gr.JSON(label='Columnas detectadas')

        boton_procesar.click(
            fn=procesar_archivos,
            inputs=[archivo_csv, estado_sesion],
            outputs=[estado_sesion, selector_conjunto, tabla_cruda, tabla_indicadores, json_mapa, diagnostico, chat, audio_salida, caja_estado, resumen_final],
        )
        selector_conjunto.change(
            fn=cambiar_conjunto,
            inputs=[selector_conjunto, estado_sesion],
            outputs=[estado_sesion, tabla_cruda, tabla_indicadores, json_mapa, diagnostico, caja_estado, audio_salida],
        )
        boton_enviar.click(
            fn=enviar_texto,
            inputs=[entrada_texto, estado_sesion],
            outputs=[estado_sesion, chat, audio_salida, caja_estado, entrada_texto],
        ).then(lambda: '', None, resumen_final)
        boton_responder_voz.click(
            fn=responder_por_voz,
            inputs=[entrada_audio, estado_sesion],
            outputs=[estado_sesion, chat, audio_salida, transcripcion, caja_estado],
        ).then(lambda: '', None, resumen_final)
        boton_resumen.click(
            fn=resumir_conversacion,
            inputs=[estado_sesion],
            outputs=[resumen_final, audio_salida, caja_estado],
        )
        boton_limpiar.click(
            fn=limpiar_chat,
            inputs=[estado_sesion],
            outputs=[estado_sesion, chat, audio_salida, transcripcion, resumen_final, caja_estado],
        )

    return aplicacion
