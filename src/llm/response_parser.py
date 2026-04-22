from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RespuestaModelo:
    respuesta: str
    pregunta: str = ''
    riesgos: list[str] = field(default_factory=list)
    acciones: list[str] = field(default_factory=list)
    metricas: list[str] = field(default_factory=list)

    def a_markdown(self) -> str:
        lineas = [self.respuesta.strip()]
        if self.riesgos:
            lineas.append('\n**Riesgos**')
            lineas.extend(f'- {elemento}' for elemento in self.riesgos)
        if self.acciones:
            lineas.append('\n**Acciones**')
            lineas.extend(f'- {elemento}' for elemento in self.acciones)
        if self.pregunta:
            lineas.append(f'\n**Pregunta**: {self.pregunta}')
        if self.metricas:
            lineas.append('\n**Métricas**: ' + ', '.join(self.metricas))
        return '\n'.join(lineas)

    def a_diccionario(self) -> dict[str, Any]:
        return {
            'respuesta': self.respuesta,
            'pregunta': self.pregunta,
            'riesgos': self.riesgos,
            'acciones': self.acciones,
            'metricas': self.metricas,
        }


def _limpiar_texto(texto: str) -> str:
    return ' '.join(texto.replace('\r', ' ').replace('\n', ' ').split()).strip()


def _valor_a_texto(valor: Any) -> str:
    if valor is None:
        return ''
    if isinstance(valor, str):
        return _limpiar_texto(valor)
    if isinstance(valor, (int, float)):
        return str(valor)
    if isinstance(valor, dict):
        if 'riesgo' in valor and 'causa' in valor:
            return _limpiar_texto(f"{valor['riesgo']}: {valor['causa']}")
        if {'periodo', 'etiqueta_metrica', 'valor'} <= set(valor.keys()):
            metrica = str(valor.get('etiqueta_metrica', 'métrica')).strip()
            periodo = str(valor.get('periodo', 'periodo')).strip()
            valor_num = valor.get('valor')
            sufijo = ''
            if isinstance(valor_num, (int, float)):
                sufijo = f' ({valor_num:+.1f})'
            return _limpiar_texto(f'{periodo}: {metrica}{sufijo}')
        pares = []
        for clave, contenido in valor.items():
            texto = _valor_a_texto(contenido)
            if texto:
                pares.append(f'{clave}: {texto}')
        return _limpiar_texto('; '.join(pares))
    if isinstance(valor, list):
        elementos = [_valor_a_texto(elemento) for elemento in valor]
        elementos = [elemento for elemento in elementos if elemento]
        return _limpiar_texto('; '.join(elementos))
    return _limpiar_texto(str(valor))


def _lista_a_strings(valor: Any) -> list[str]:
    if valor is None:
        return []
    if isinstance(valor, list):
        salida: list[str] = []
        for elemento in valor:
            texto = _valor_a_texto(elemento)
            if texto:
                salida.append(texto)
        return salida
    texto = _valor_a_texto(valor)
    return [texto] if texto else []


def _respuesta_natural(valor: Any) -> str:
    if isinstance(valor, str):
        return _limpiar_texto(valor)
    if isinstance(valor, list):
        if valor and all(isinstance(elemento, dict) and {'periodo', 'etiqueta_metrica'} <= set(elemento.keys()) for elemento in valor):
            partes = []
            for elemento in valor[:4]:
                periodo = str(elemento.get('periodo', '')).strip()
                metrica = str(elemento.get('etiqueta_metrica', 'métrica')).strip().lower()
                valor_num = elemento.get('valor')
                if isinstance(valor_num, (int, float)):
                    partes.append(f"{periodo} por {metrica} ({valor_num:+.1f})")
                else:
                    partes.append(f"{periodo} por {metrica}")
            if not partes:
                return ''
            if len(partes) == 1:
                return f'El periodo más delicado parece ser {partes[0]}.'
            return 'Los periodos más delicados parecen ser ' + '; '.join(partes) + '.'
        partes = _lista_a_strings(valor)
        if not partes:
            return ''
        if len(partes) == 1:
            return partes[0]
        if len(partes) == 2:
            return f'{partes[0]}. Además, {partes[1].lower()}.'
        primeras = '. '.join(partes[:2])
        restante = '; '.join(partes[2:4])
        if restante:
            return f'{primeras}. Además, {restante.lower()}.'
        return primeras
    if isinstance(valor, dict):
        return _valor_a_texto(valor)
    return _valor_a_texto(valor)


def _quitar_bloques_codigo(texto: str) -> str:
    limpio = texto.strip()
    if limpio.startswith('```'):
        limpio = re.sub(r'^```[a-zA-Z0-9_+-]*\n?', '', limpio)
        limpio = re.sub(r'\n?```$', '', limpio)
    return limpio.strip()


def _intentar_json(candidato: str) -> dict[str, Any] | None:
    try:
        valor = json.loads(candidato)
        return valor if isinstance(valor, dict) else None
    except Exception:
        pass
    try:
        reparado = candidato.replace('null', 'None').replace('true', 'True').replace('false', 'False')
        valor = ast.literal_eval(reparado)
        return valor if isinstance(valor, dict) else None
    except Exception:
        return None


def _extraer_fragmento(texto: str, clave: str, siguientes: list[str]) -> str:
    if siguientes:
        patrones = '|'.join(re.escape(siguiente) for siguiente in siguientes)
        patron = rf'"{re.escape(clave)}"\s*:\s*(.+?)(?=,\s*"(?:{patrones})"|\s*}}\s*$)'
    else:
        patron = rf'"{re.escape(clave)}"\s*:\s*(.+?)(?=\s*}}\s*$)'
    coincidencia = re.search(patron, texto, flags=re.DOTALL)
    return coincidencia.group(1).strip() if coincidencia else ''


def _parsear_fragmento(fragmento: str) -> Any:
    if not fragmento:
        return None
    try:
        return json.loads(fragmento)
    except Exception:
        pass
    try:
        reparado = fragmento.replace('null', 'None').replace('true', 'True').replace('false', 'False')
        return ast.literal_eval(reparado)
    except Exception:
        return fragmento.strip(' \n\t,')


def _intentar_por_campos(texto: str) -> dict[str, Any] | None:
    if '"respuesta"' not in texto:
        return None
    return {
        'respuesta': _parsear_fragmento(_extraer_fragmento(texto, 'respuesta', ['pregunta', 'riesgos', 'acciones', 'metricas'])),
        'pregunta': _parsear_fragmento(_extraer_fragmento(texto, 'pregunta', ['riesgos', 'acciones', 'metricas'])),
        'riesgos': _parsear_fragmento(_extraer_fragmento(texto, 'riesgos', ['acciones', 'metricas'])),
        'acciones': _parsear_fragmento(_extraer_fragmento(texto, 'acciones', ['metricas'])),
        'metricas': _parsear_fragmento(_extraer_fragmento(texto, 'metricas', [])),
    }


def interpretar_respuesta(texto_crudo: str) -> RespuestaModelo:
    texto_limpio = _quitar_bloques_codigo(texto_crudo)
    candidato = texto_limpio
    inicio = candidato.find('{')
    fin = candidato.rfind('}')
    if inicio != -1 and fin != -1 and fin > inicio:
        candidato = candidato[inicio:fin + 1]

    datos = _intentar_json(candidato)
    if datos is None:
        datos = _intentar_por_campos(texto_limpio)

    if isinstance(datos, dict):
        respuesta = _respuesta_natural(datos.get('respuesta', ''))
        if not respuesta:
            respuesta = _respuesta_natural(datos.get('respuesta_texto', ''))
        if not respuesta:
            respuesta = 'No se pudo generar una respuesta útil.'
        return RespuestaModelo(
            respuesta=respuesta,
            pregunta=_valor_a_texto(datos.get('pregunta', '')),
            riesgos=_lista_a_strings(datos.get('riesgos', [])),
            acciones=_lista_a_strings(datos.get('acciones', [])),
            metricas=_lista_a_strings(datos.get('metricas', [])),
        )

    return RespuestaModelo(respuesta=_limpiar_texto(texto_limpio) or 'No se pudo interpretar la salida del modelo.')
