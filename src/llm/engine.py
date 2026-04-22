from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from src.data.business_snapshot import ResumenNegocio
from src.data.schema_mapper import normalizar_texto
from src.llm.prompts import construir_mensajes, construir_mensajes_resumen
from src.llm.response_parser import RespuestaModelo, interpretar_respuesta

registrador = logging.getLogger(__name__)


@dataclass
class ConfiguracionModelo:
    modo: str
    ruta_modelo: str
    contexto: int = 4096
    hilos: int = 6
    lote: int = 256
    temperatura: float = 0.25
    maximo_tokens: int = 120
    top_p: float = 0.9
    penalizacion_repeticion: float = 1.08
    url_servidor: str = 'http://127.0.0.1:8080/v1/chat/completions'
    nombre_modelo_servidor: str = 'local-model'
    timeout_segundos: int = 300


class ModeloLocal:
    conectores_incompletos = {
        'de', 'del', 'con', 'para', 'por', 'y', 'o', 'que', 'como', 'cómo', 'cual', 'cuál', 'en', 'a', 'sobre', 'principal'
    }

    def __init__(self, configuracion: ConfiguracionModelo, raiz_proyecto: Path) -> None:
        self.configuracion = configuracion
        self.raiz_proyecto = raiz_proyecto
        self._instancia_llama = None

    @property
    def modo(self) -> str:
        return self.configuracion.modo

    def calentar(self) -> str:
        if self.modo in {'pruebas', 'reglas'}:
            return 'Modo de pruebas activo. La app no debería usarlo para respuestas reales.'
        if self.modo == 'llama_cpp':
            self._asegurar_carga_llama()
            return 'Modelo llama_cpp cargado.'
        if self.modo == 'servidor_local':
            return self._verificar_servidor_local()
        raise ValueError(f'Modo no soportado: {self.modo}')

    def generar(self, resumen_negocio: ResumenNegocio, mensaje_usuario: str, historial_chat: list[tuple[str, str]]) -> RespuestaModelo:
        if self.modo in {'pruebas', 'reglas'}:
            return self._resolver_por_reglas(resumen_negocio, mensaje_usuario, historial_chat)

        mensajes = construir_mensajes(resumen_negocio, mensaje_usuario, historial_chat)
        texto = self._generar_texto(mensajes)
        respuesta = interpretar_respuesta(texto)
        if not respuesta.respuesta.strip():
            raise RuntimeError('El modelo respondió vacío.')
        return respuesta

    def resumir_conversacion(self, resumen_negocio: ResumenNegocio, historial_chat: list[tuple[str, str]]) -> str:
        if not historial_chat:
            return 'No hubo preguntas durante la conversación.'
        if self.modo in {'pruebas', 'reglas'}:
            lineas = ['Puntos clave para decidir:']
            lineas.extend(f'- {texto}' for texto in resumen_negocio.observaciones[:3])
            temas = [turno_usuario for turno_usuario, _ in historial_chat if turno_usuario.strip()]
            if temas:
                lineas.append('- Temas tratados: ' + '; '.join(temas[-4:]))
            acciones = self._acciones_base(resumen_negocio, limite=4)
            if acciones:
                lineas.append('- Prioridades inmediatas:')
                lineas.extend(f'  - {texto}' for texto in acciones[:4])
            peor_sucursal = resumen_negocio.contexto_avanzado.get('peor_sucursal')
            if peor_sucursal:
                lineas.append(
                    f"- Sucursal a vigilar primero: {peor_sucursal['segmento']} con cambio de ingresos de {peor_sucursal['cambio_ingresos_pct']:.1f}%."
                )
            return '\n'.join(lineas)

        mensajes = construir_mensajes_resumen(resumen_negocio, historial_chat)
        return self._generar_texto(mensajes).strip()

    def _generar_texto(self, mensajes: list[dict[str, str]]) -> str:
        if self.modo == 'llama_cpp':
            return self._generar_con_llama_cpp(mensajes)
        if self.modo == 'servidor_local':
            return self._generar_con_servidor(mensajes)
        raise ValueError(f'Modo no soportado: {self.modo}')

    def _verificar_servidor_local(self) -> str:
        carga = {
            'model': self._nombre_modelo_servidor(),
            'messages': [{'role': 'user', 'content': 'Responde solo: listo'}],
            'temperature': 0.0,
            'max_tokens': 8,
            'top_p': 1.0,
            'stream': False,
        }
        try:
            respuesta = requests.post(
                self.configuracion.url_servidor,
                json=carga,
                timeout=min(30, self.configuracion.timeout_segundos),
            )
            if not respuesta.ok:
                raise RuntimeError(f'LLM local devolvió {respuesta.status_code}: {self._detalle_error(respuesta)}')
        except requests.RequestException as error:
            raise RuntimeError(
                'No pude conectar con el servidor LLM local. Inícialo antes de abrir la app. '
                'Ejemplo: python -m llama_cpp.server --model .\\models\\llm\\model.gguf --host 127.0.0.1 --port 8080'
            ) from error
        return f'Servidor LLM listo en {self.configuracion.url_servidor}.'

    def _asegurar_carga_llama(self) -> None:
        if self._instancia_llama is not None:
            return
        try:
            from llama_cpp import Llama
        except Exception as error:
            raise RuntimeError('No se pudo importar llama_cpp. Instala requirements-llama-cpp.txt.') from error

        ruta_modelo = Path(self.configuracion.ruta_modelo)
        if not ruta_modelo.is_absolute():
            ruta_modelo = (self.raiz_proyecto / ruta_modelo).resolve()
        if not ruta_modelo.exists():
            raise FileNotFoundError(f'No se encontró el archivo del modelo en {ruta_modelo}.')

        registrador.info('Cargando modelo desde %s', ruta_modelo)
        self._instancia_llama = Llama(
            model_path=str(ruta_modelo),
            n_ctx=self.configuracion.contexto,
            n_threads=self.configuracion.hilos,
            n_batch=self.configuracion.lote,
            verbose=False,
        )

    def _generar_con_llama_cpp(self, mensajes: list[dict[str, str]]) -> str:
        self._asegurar_carga_llama()
        respuesta = self._instancia_llama.create_chat_completion(
            messages=mensajes,
            temperature=self.configuracion.temperatura,
            max_tokens=self.configuracion.maximo_tokens,
            top_p=self.configuracion.top_p,
            repeat_penalty=self.configuracion.penalizacion_repeticion,
        )
        return str(respuesta['choices'][0]['message']['content'])

    def _generar_con_servidor(self, mensajes: list[dict[str, str]]) -> str:
        mensajes_normales = self._normalizar_mensajes_servidor(mensajes)
        carga = self._construir_carga_servidor(mensajes_normales)

        try:
            respuesta = requests.post(
                self.configuracion.url_servidor,
                json=carga,
                timeout=self.configuracion.timeout_segundos,
            )
        except requests.RequestException as error:
            raise RuntimeError(
                'No pude consultar el LLM local. Verifica que el servidor siga encendido y que la URL sea correcta.'
            ) from error

        if respuesta.status_code == 400:
            mensajes_reducidos = self._compactar_mensajes_servidor(mensajes_normales)
            carga_reducida = self._construir_carga_servidor(mensajes_reducidos)
            try:
                respuesta = requests.post(
                    self.configuracion.url_servidor,
                    json=carga_reducida,
                    timeout=self.configuracion.timeout_segundos,
                )
            except requests.RequestException as error:
                raise RuntimeError(
                    'No pude consultar el LLM local. Verifica que el servidor siga encendido y que la URL sea correcta.'
                ) from error

        if not respuesta.ok:
            raise RuntimeError(f'LLM local devolvió {respuesta.status_code}: {self._detalle_error(respuesta)}')

        try:
            datos = respuesta.json()
        except Exception as error:
            raise RuntimeError(f'El servidor LLM respondió algo no válido: {respuesta.text[:800]}') from error

        elecciones = datos.get('choices') or []
        if not elecciones:
            raise RuntimeError(f'El servidor LLM no devolvió choices: {json.dumps(datos, ensure_ascii=False)[:800]}')

        mensaje = elecciones[0].get('message') or {}
        contenido = mensaje.get('content', '')
        if isinstance(contenido, str):
            return contenido
        if isinstance(contenido, list):
            partes: list[str] = []
            for elemento in contenido:
                if isinstance(elemento, dict):
                    texto = elemento.get('text')
                    if texto:
                        partes.append(str(texto))
                elif elemento is not None:
                    partes.append(str(elemento))
            return '\n'.join(partes).strip()
        return str(contenido).strip()

    def _construir_carga_servidor(self, mensajes: list[dict[str, str]]) -> dict[str, Any]:
        return {
            'model': self._nombre_modelo_servidor(),
            'messages': mensajes,
            'temperature': self.configuracion.temperatura,
            'max_tokens': self.configuracion.maximo_tokens,
            'top_p': self.configuracion.top_p,
            'stream': False,
        }

    def _nombre_modelo_servidor(self) -> str:
        nombre = (self.configuracion.nombre_modelo_servidor or '').strip()
        return nombre or 'local-model'

    def _normalizar_mensajes_servidor(self, mensajes: list[dict[str, Any]]) -> list[dict[str, str]]:
        salida: list[dict[str, str]] = []
        for mensaje in mensajes:
            rol = str(mensaje.get('role', 'user')).strip().lower()
            if rol not in {'system', 'user', 'assistant'}:
                rol = 'user'
            contenido = self._contenido_a_texto(mensaje.get('content', ''))
            if not contenido.strip():
                continue
            salida.append({'role': rol, 'content': contenido})
        if not salida:
            salida.append({'role': 'user', 'content': 'Resume el problema principal en una frase.'})
        return salida

    def _compactar_mensajes_servidor(self, mensajes: list[dict[str, str]]) -> list[dict[str, str]]:
        if not mensajes:
            return [{'role': 'user', 'content': 'Resume el problema principal en una frase.'}]

        compactados: list[dict[str, str]] = []
        for indice, mensaje in enumerate(mensajes):
            rol = mensaje['role']
            contenido = mensaje['content']
            if indice == 0 and rol == 'system':
                compactados.append({'role': 'system', 'content': contenido[:1400]})
                continue
            if rol == 'assistant':
                compactados.append({'role': 'assistant', 'content': contenido[:700]})
                continue
            compactados.append({'role': rol, 'content': contenido[:2400]})

        if len(compactados) > 3:
            primero = compactados[0]
            ultimos = compactados[-2:]
            return [primero] + ultimos
        return compactados

    def _contenido_a_texto(self, valor: Any) -> str:
        if valor is None:
            return ''
        if isinstance(valor, str):
            return valor
        if isinstance(valor, (int, float, bool)):
            return str(valor)
        try:
            return json.dumps(valor, ensure_ascii=False)
        except Exception:
            return str(valor)

    def _detalle_error(self, respuesta: requests.Response) -> str:
        try:
            datos = respuesta.json()
            if isinstance(datos, dict):
                if 'error' in datos:
                    return str(datos['error'])
                return json.dumps(datos, ensure_ascii=False)[:800]
        except Exception:
            pass
        return respuesta.text[:800]

    def _resolver_por_reglas(self, resumen_negocio: ResumenNegocio, mensaje_usuario: str, historial_chat: list[tuple[str, str]]) -> RespuestaModelo:
        mensaje = normalizar_texto(mensaje_usuario)
        if not mensaje:
            return self._respuesta_general(resumen_negocio)
        if self._mensaje_parece_incompleto(mensaje_usuario):
            return self._respuesta_aclaracion(resumen_negocio)
        if self._contiene(mensaje, ('30_dias', 'treinta_dias', 'plan', 'plan_accion')):
            return self._respuesta_plan_30_dias(resumen_negocio)
        if self._contiene(mensaje, ('por_que', 'causa', 'motivo', 'razon', 'explica', 'principal')) and self._contiene(mensaje, ('ingres', 'venta', 'caida', 'baja')):
            return self._respuesta_causas_ingresos(resumen_negocio, enfasis_principal=True)
        if self._contiene(mensaje, ('margen', 'rentabilidad', 'utilidad_operativa')):
            return self._respuesta_margen(resumen_negocio)
        if self._contiene(mensaje, ('primero', 'prioridad', 'revisar', 'enfocar', 'urgente')):
            return self._respuesta_prioridades(resumen_negocio)
        if self._contiene(mensaje, ('sucursal', 'tienda', 'local', 'cumbres', 'centro', 'tec')):
            return self._respuesta_sucursales(resumen_negocio)
        if self._contiene(mensaje, ('canal', 'delivery', 'salon', 'retiro', 'app')):
            return self._respuesta_canales(resumen_negocio)
        if self._contiene(mensaje, ('resumen', 'conclusion', 'sintesis', 'decision')):
            return self._respuesta_general(resumen_negocio)
        if self._contiene(mensaje, ('que_harias', 'recomend', 'mejorar', 'estrategia')):
            return self._respuesta_prioridades(resumen_negocio)
        if self._contiene(mensaje, ('causa', 'principal', 'caida', 'baja')):
            return self._respuesta_causas_ingresos(resumen_negocio, enfasis_principal=True)
        return self._respuesta_general(resumen_negocio, mensaje_usuario=mensaje_usuario)

    def _respuesta_aclaracion(self, resumen_negocio: ResumenNegocio) -> RespuestaModelo:
        return RespuestaModelo(
            respuesta='Te escuché incompleto. Termina la idea y la tomo como una sola pregunta.',
            pregunta='Puedes decir, por ejemplo: “¿Cuál es la causa principal de la baja de ventas?”',
            riesgos=self._riesgos_base(resumen_negocio),
            acciones=self._acciones_base(resumen_negocio, limite=2),
            metricas=self._metricas_base(resumen_negocio),
        )

    def _respuesta_causas_ingresos(self, resumen_negocio: ResumenNegocio, enfasis_principal: bool = False) -> RespuestaModelo:
        contexto = resumen_negocio.contexto_avanzado
        causas = contexto.get('causas_ingresos', [])
        momento = contexto.get('momento_critico', {})
        if causas:
            cabecera = 'La caída de ingresos luce explicada por una combinación operativa-comercial, no por una sola variable aislada.' if enfasis_principal else 'La caída de ingresos parece venir principalmente de estas palancas:'
            texto = cabecera + '\n' + '\n'.join(f'- {causa}' for causa in causas[:3])
        else:
            texto = 'Veo una caída de ingresos, pero con este archivo no queda aislada una sola causa. Lo más probable es una combinación de menor volumen y presión operativa.'
        if momento:
            detalle = momento.get('detalle', [])
            if detalle:
                texto += f"\n\nLa ruptura más clara aparece en {momento.get('periodo')}:\n" + '\n'.join(f'- {elemento}' for elemento in detalle[:3])
        return RespuestaModelo(
            respuesta=texto,
            pregunta='¿Quieres que lo separe entre volumen, ticket y fricción operativa?',
            riesgos=self._riesgos_base(resumen_negocio),
            acciones=self._acciones_base(resumen_negocio, limite=4),
            metricas=self._metricas_base(resumen_negocio),
        )

    def _respuesta_margen(self, resumen_negocio: ResumenNegocio) -> RespuestaModelo:
        resumen = resumen_negocio.resumen
        partes: list[str] = []
        margen_bruto = resumen.get('ultimo_margen_bruto_pct')
        margen_operativo = resumen.get('ultimo_margen_operativo_pct')
        gasto = resumen.get('ultimo_gasto_operativo_pct')
        if margen_bruto is not None:
            partes.append(f'El margen bruto actual está en {margen_bruto:.1f}%.')
        if gasto is not None:
            partes.append(f'El gasto operativo sobre ingresos está en {gasto:.1f}%.')
        if margen_operativo is not None:
            partes.append(f'El margen operativo cerró en {margen_operativo:.1f}%.')
        if not partes:
            partes.append('No tengo suficientes columnas para explicar el margen con precisión.')
        if resumen_negocio.contexto_avanzado.get('causas_ingresos'):
            partes.append('Además, varias señales apuntan a una mezcla menos favorable y más fricción operativa.')
        return RespuestaModelo(
            respuesta=' '.join(partes),
            pregunta='¿Quieres que priorice entre margen bruto y gasto operativo?',
            riesgos=self._riesgos_base(resumen_negocio),
            acciones=self._acciones_base(resumen_negocio, limite=4),
            metricas=self._metricas_base(resumen_negocio),
        )

    def _respuesta_prioridades(self, resumen_negocio: ResumenNegocio) -> RespuestaModelo:
        acciones = self._acciones_base(resumen_negocio, limite=5)
        peor_sucursal = resumen_negocio.contexto_avanzado.get('peor_sucursal')
        texto = 'Yo empezaría por tres frentes concretos:'
        if acciones:
            texto += '\n' + '\n'.join(f'- {accion}' for accion in acciones[:3])
        if peor_sucursal:
            texto += f"\n\nPondría foco inmediato en {peor_sucursal['segmento']}, porque combina tendencia débil y menor margen."
        return RespuestaModelo(
            respuesta=texto,
            pregunta='¿Quieres que arme un plan de 30 días o prefieres profundizar en la causa principal?',
            riesgos=self._riesgos_base(resumen_negocio),
            acciones=acciones,
            metricas=self._metricas_base(resumen_negocio),
        )

    def _respuesta_plan_30_dias(self, resumen_negocio: ResumenNegocio) -> RespuestaModelo:
        contexto = resumen_negocio.contexto_avanzado
        peor_sucursal = contexto.get('peor_sucursal')
        causas = contexto.get('causas_ingresos', [])
        lineas = ['Te propongo un plan de 30 días, corto y ejecutable:']
        lineas.append('- Semana 1: validar datos diarios, confirmar caída por volumen, ticket y cancelaciones.')
        if peor_sucursal:
            lineas.append(f"- Semana 2: auditar {peor_sucursal['segmento']} en mix, horarios, dotación y tiempos de servicio.")
        else:
            lineas.append('- Semana 2: auditar la operación con peor margen y revisar quiebres, descuentos y tiempos de atención.')
        if causas:
            lineas.append(f'- Semana 3: atacar la principal palanca detectada: {causas[0]}')
        else:
            lineas.append('- Semana 3: corregir la principal fuga de ventas y ajustar gasto operativo variable.')
        lineas.append('- Semana 4: medir impacto, decidir si escalar cambios de precio, surtido y staffing.')
        acciones = self._acciones_base(resumen_negocio, limite=5)
        if peor_sucursal:
            acciones = [f"Abrir tablero diario de {peor_sucursal['segmento']} con ventas, órdenes, ticket, faltantes y quejas."] + acciones
        return RespuestaModelo(
            respuesta='\n'.join(lineas),
            pregunta='¿Quieres que lo convierta en plan de 4 semanas con responsables?',
            riesgos=self._riesgos_base(resumen_negocio),
            acciones=acciones[:5],
            metricas=self._metricas_base(resumen_negocio),
        )

    def _respuesta_sucursales(self, resumen_negocio: ResumenNegocio) -> RespuestaModelo:
        sucursales = resumen_negocio.contexto_avanzado.get('sucursales', [])
        if not sucursales:
            return RespuestaModelo(
                respuesta='No tengo una columna de sucursal suficiente para comparar locales en este archivo.',
                pregunta='¿Quieres revisar el total del negocio o cargar un archivo con detalle por local?',
                riesgos=self._riesgos_base(resumen_negocio),
                acciones=self._acciones_base(resumen_negocio, limite=3),
                metricas=self._metricas_base(resumen_negocio),
            )
        ordenadas = sorted(sucursales, key=lambda fila: fila.get('cambio_ingresos_pct', 0))
        peor = ordenadas[0]
        mejor = ordenadas[-1]
        texto = (
            f"La sucursal más comprometida es {peor['segmento']}, con cambio de ingresos de {peor['cambio_ingresos_pct']:.1f}% "
            f"y margen operativo de {peor['margen_operativo_pct']:.1f}%. "
            f"La mejor parada es {mejor['segmento']}, con cambio de ingresos de {mejor['cambio_ingresos_pct']:.1f}%."
        )
        acciones = self._acciones_base(resumen_negocio, limite=4)
        acciones.insert(0, f"Comparar el mix comercial y la dotación de {peor['segmento']} contra {mejor['segmento']}.")
        return RespuestaModelo(
            respuesta=texto,
            pregunta=f"¿Quieres que el próximo corte lo centremos solo en {peor['segmento']}?",
            riesgos=self._riesgos_base(resumen_negocio),
            acciones=acciones[:4],
            metricas=self._metricas_base(resumen_negocio),
        )

    def _respuesta_canales(self, resumen_negocio: ResumenNegocio) -> RespuestaModelo:
        canales = resumen_negocio.contexto_avanzado.get('canales', [])
        causas = resumen_negocio.contexto_avanzado.get('causas_ingresos', [])
        if not canales:
            texto = 'No tengo una apertura clara por canal en este archivo. Sí veo señales que afectan delivery y operación.'
            if causas:
                texto += '\n' + '\n'.join(f'- {causa}' for causa in causas[:2])
        else:
            principal = canales[0]
            texto = (
                f"El canal principal por ingresos es {principal['segmento']}, con {principal['ultimo_ingresos']:.0f} en el último periodo. "
                f"Su variación de ingresos fue {principal['cambio_ingresos_pct']:.1f}%."
            )
        return RespuestaModelo(
            respuesta=texto,
            pregunta='¿Quieres que compare canal principal contra el resto del negocio?',
            riesgos=self._riesgos_base(resumen_negocio),
            acciones=self._acciones_base(resumen_negocio, limite=4),
            metricas=self._metricas_base(resumen_negocio),
        )

    def _respuesta_general(self, resumen_negocio: ResumenNegocio, mensaje_usuario: str = '') -> RespuestaModelo:
        observaciones = resumen_negocio.observaciones[:3]
        texto = 'Esto es lo más relevante que veo:\n' + '\n'.join(f'- {observacion}' for observacion in observaciones)
        if mensaje_usuario:
            texto += f'\n\nSobre "{mensaje_usuario}", mi lectura es que hoy conviene separar el problema entre ventas, margen y disciplina operativa antes de decidir.'
        return RespuestaModelo(
            respuesta=texto,
            pregunta=resumen_negocio.preguntas[0] if resumen_negocio.preguntas else '¿Qué parte quieres abrir primero?',
            riesgos=self._riesgos_base(resumen_negocio),
            acciones=self._acciones_base(resumen_negocio, limite=4),
            metricas=self._metricas_base(resumen_negocio),
        )

    def _acciones_base(self, resumen_negocio: ResumenNegocio, limite: int) -> list[str]:
        return [accion for accion in resumen_negocio.acciones if accion][:limite]

    def _riesgos_base(self, resumen_negocio: ResumenNegocio) -> list[str]:
        riesgos: list[str] = []
        resumen = resumen_negocio.resumen
        margen = resumen.get('ultimo_margen_operativo_pct')
        if margen is not None and margen < 8:
            riesgos.append('La rentabilidad operativa quedó estrecha y un desvío pequeño puede dejar sin colchón al negocio.')
        anomalia = resumen_negocio.contexto_avanzado.get('anomalia_principal')
        if anomalia:
            riesgos.append(f"El periodo más sensible fue {anomalia.get('periodo')} por {anomalia.get('etiqueta_metrica')}.")
        return riesgos[:3]

    def _metricas_base(self, resumen_negocio: ResumenNegocio) -> list[str]:
        resumen = resumen_negocio.resumen
        metricas: list[str] = []
        if resumen.get('ultimos_ingresos') is not None:
            metricas.append(f"Ingresos último periodo: {resumen['ultimos_ingresos']:.2f}")
        if resumen.get('ultimas_ordenes') is not None:
            metricas.append(f"Órdenes último periodo: {resumen['ultimas_ordenes']:.0f}")
        if resumen.get('ultimo_ticket_promedio') is not None:
            metricas.append(f"Ticket promedio último periodo: {resumen['ultimo_ticket_promedio']:.2f}")
        if resumen.get('ultimo_margen_operativo_pct') is not None:
            metricas.append(f"Margen operativo: {resumen['ultimo_margen_operativo_pct']:.1f}%")
        return metricas[:4]

    def _mensaje_parece_incompleto(self, mensaje_usuario: str) -> bool:
        texto = mensaje_usuario.strip()
        if not texto:
            return True
        palabras = [p for p in texto.replace('¿', ' ').replace('?', ' ').replace('¡', ' ').replace('!', ' ').split() if p]
        if len(palabras) <= 2:
            return True
        ultima = normalizar_texto(palabras[-1])
        return ultima in self.conectores_incompletos

    @staticmethod
    def _contiene(texto_normalizado: str, fragmentos: tuple[str, ...]) -> bool:
        return any(fragmento in texto_normalizado for fragmento in fragmentos)
