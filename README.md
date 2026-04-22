# Asistente de voz local para análisis de negocio con CSV

Este proyecto implementa un asistente de voz local orientado al análisis conversacional de negocio sobre archivos CSV. Permite cargar información operativa o financiera, preparar el archivo para análisis, construir un contexto analítico del negocio y responder preguntas por texto o por voz desde una sola interfaz web.

Python se encarga de cargar, limpiar, normalizar, agregar y consolidar el CSV. Las respuestas al usuario deben provenir de un LLM local, no de un servicio remoto. La salida puede mostrarse en pantalla y reproducirse también como audio.

## Propósito

La app está pensada para convertir un archivo tabular en un entorno consultable por lenguaje natural. En lugar de revisar manualmente columnas y métricas, el usuario puede cargar un CSV, obtener un diagnóstico inicial y luego formular preguntas sobre desempeño, periodos críticos, márgenes, reclamos, sucursales, canales o prioridades de acción.

No sustituye un ERP, una plataforma BI ni un data warehouse. Su valor está en combinar preparación tabular, contexto analítico, conversación y respuesta por voz en un flujo local y autocontenido.

## Qué hace

- carga archivos CSV desde una interfaz web
- limpia y normaliza columnas relevantes de negocio
- consolida archivos heterogéneos en una vista analítica comparable
- calcula métricas y variaciones clave
- genera un diagnóstico inicial
- permite preguntas por texto o por voz
- responde en lenguaje natural usando un LLM local
- sintetiza la respuesta en audio
- genera un resumen ejecutivo de la conversación

## Tipos de archivos compatibles

El asistente está preparado para dos perfiles principales de archivo.

### 1. Archivos mensuales de resultados

Ejemplos de columnas compatibles:

- `periodo`
- `ingresos`
- `costo_ventas`
- `gasto_operativo`
- `utilidad_bruta`
- `utilidad_operativa`
- `ordenes`
- `ticket_promedio`
- `reclamos`
- `cancelaciones_pct`
- `faltantes`

### 2. Archivos operativos granulares

También puede trabajar con archivos diarios o transaccionales con varias filas por fecha, sucursal o canal. En ese caso, el sistema agrega y recompone una vista analítica más estable antes de construir el contexto conversacional.

## Modos de ejecución del LLM

La app admite tres modos:

- `servidor_local`: recomendado. Usa un servidor local compatible con OpenAI.
- `llama_cpp`: carga un archivo `.gguf` directamente desde Python si instalas `requirements-llama-cpp.txt`.
- `pruebas`: solo para tests y `scripts/smoke_test.py`.

## Arquitectura general

La solución está organizada en cinco capas funcionales.

### Interfaz

La interfaz está construida con Gradio y concentra en una sola ventana:

- carga del archivo
- panel de diagnóstico
- conversación por texto
- grabación de pregunta por voz
- reproducción de la respuesta en audio
- resumen de decisiones

### Preparación de datos

La lógica tabular está implementada en Python con `pandas` y `numpy`. Esta capa resuelve:

- lectura del CSV
- limpieza y tipado
- normalización de nombres de columnas
- mapeo semántico de campos equivalentes
- agregación por periodo
- cálculo de KPIs y variaciones
- consolidación del contexto del negocio

### Contexto analítico

A partir del dataframe consolidado, el sistema construye una representación resumida del negocio con:

- métricas principales
- cambios relevantes entre periodos
- anomalías o señales atípicas
- causas probables del deterioro
- prioridades y riesgos operativos
- contexto por sucursal o canal cuando aplica

El modelo de lenguaje no trabaja sobre el CSV crudo, sino sobre esta representación procesada.

### Modelo de lenguaje

La generación de respuestas se apoya en un modelo local en formato GGUF, normalmente servido con `llama.cpp` mediante un endpoint compatible con `/v1/chat/completions`.

Python resuelve el cálculo y la consolidación. El LLM local se usa para redactar respuestas, explicar hallazgos, priorizar acciones y mantener la continuidad conversacional.

### Voz

La capa de voz está compuesta por:

- `Faster-Whisper` para reconocimiento de voz
- `Piper TTS` para síntesis de voz

La pregunta hablada se transcribe a texto, entra al mismo flujo que una pregunta escrita y la respuesta final puede sintetizarse nuevamente a audio.

## Estructura del proyecto

```text
fix_voice/
├─ app.py
├─ config/
│  └─ settings.yaml
├─ examples/
│  ├─ estado_resultados_demo.csv
│  ├─ comida_mensual_realista.csv
│  └─ comida_operacion_compleja.csv
├─ models/
│  ├─ asr/
│  ├─ llm/
│  └─ tts/
├─ scripts/
│  ├─ smoke_test.py
│  └─ warmup.py
├─ src/
│  ├─ audio/
│  ├─ data/
│  ├─ llm/
│  ├─ orchestration/
│  ├─ ui/
│  └─ utils/
├─ tests/
├─ requirements.txt
└─ requirements-llama-cpp.txt
```

## Responsabilidades por módulo

- `src/ui`: interfaz y eventos de Gradio
- `src/audio`: reconocimiento y síntesis de voz
- `src/data`: carga, limpieza, mapeo y construcción del contexto tabular
- `src/llm`: prompts, cliente del modelo local y parseo de respuestas
- `src/orchestration`: sesión, historial y flujo conversacional
- `src/utils`: utilidades de soporte y logging

## Dependencias principales

- Python 3.11
- Gradio
- pandas
- numpy
- Faster-Whisper
- Piper TTS
- llama-cpp-python
- requests
- PyYAML

## Requisitos de ejecución

Para el funcionamiento completo necesitas lo siguiente.

### 1. Un modelo GGUF para el LLM

Colócalo en:

```text
models/llm/model.gguf
```

### 2. Una voz Piper válida

Coloca los archivos de voz en:

```text
models/tts/
```

Ejemplo:

```text
models/tts/es_MX-claude-high.onnx
models/tts/es_MX-claude-high.onnx.json
```

### 3. Un entorno virtual de Python

Se recomienda ejecutar el proyecto dentro de un entorno aislado.

## Instalación

### 1. Crear y activar el entorno virtual

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Actualizar herramientas base

```powershell
python -m pip install --upgrade pip setuptools wheel
```

### 3. Instalar dependencias principales

```powershell
pip install -r requirements.txt
```

### 4. Instalar el backend opcional para `llama.cpp`

Opción simple:

```powershell
pip install "llama-cpp-python[server]"
```

O, si el proyecto ya separa este backend en archivo propio:

```powershell
pip install -r requirements-llama-cpp.txt
```

## Configuración

La configuración principal se encuentra en:

```text
config/settings.yaml
```

Entre los parámetros relevantes se incluyen:

- modo de ejecución del LLM
- URL del servidor local
- tamaño del modelo ASR
- rutas de la voz Piper
- límites de generación
- parámetros de UI y audio

Ejemplo:

```yaml
ruta_voz_tts: 'models/tts/es_MX-claude-high.onnx'
ruta_configuracion_voz_tts: 'models/tts/es_MX-claude-high.onnx.json'
modelo_asr: 'tiny'
```

## Arranque recomendado con servidor local

### 1. Inicia el servidor del LLM

En una terminal, con el entorno activado:

```powershell
python -m llama_cpp.server --model .\models\llm\model.gguf --host 127.0.0.1 --port 8080 --n_ctx 1024 --n_threads 4 --n_threads_batch 4
```

### 2. Inicia la aplicación web

En otra terminal, también con el entorno activado:

```powershell
python app.py
```

### 3. Abre la interfaz

```text
http://127.0.0.1:7860
```

## Cómo cargar un CSV y usar la app

1. abre la interfaz web en el navegador  
2. en el panel principal, carga un archivo CSV desde tu equipo  
3. espera a que el sistema procese el archivo  
4. revisa el diagnóstico inicial generado a partir de los datos  
5. escribe una pregunta o grábala por voz  
6. recibe la respuesta en texto  
7. reproduce el audio de la respuesta si la voz Piper está configurada  
8. continúa la conversación sobre el mismo archivo  
9. genera un resumen final orientado a decisión cuando termines

Para probar rápidamente, puedes usar cualquiera de los archivos de `examples/`.

## Flujo técnico de extremo a extremo

1. el usuario carga un CSV
2. Python lo lee con `pandas`
3. se detectan y normalizan columnas relevantes
4. si el archivo es granular, se agregan registros y se recompone una vista analítica
5. se calculan métricas, variaciones y señales relevantes
6. la pregunta entra por texto o por ASR
7. se construye un prompt con contexto de negocio e historial reciente
8. el prompt se envía al LLM local
9. la respuesta se transforma a una estructura uniforme
10. el texto se muestra en la UI
11. el mismo texto puede sintetizarse a audio con Piper
12. la interfaz reproduce el audio resultante

## Archivos de ejemplo

La carpeta `examples/` incluye archivos listos para validar la app:

- `estado_resultados_demo.csv`
- `comida_mensual_realista.csv`
- `comida_operacion_compleja.csv`

Estos ejemplos permiten probar tanto un flujo mensual simple como uno operativo más rico.

## Pruebas y validación

### Tests

```powershell
python -m unittest
```

### Smoke test

```powershell
python scripts\smoke_test.py
```

## Notas importantes

- si no hay un servidor LLM encendido y el modo configurado lo requiere, la app puede abrir, pero fallará al intentar responder
- el CSV mensual y el CSV complejo vienen en `examples/`
- la salida de voz depende de que exista una voz Piper válida en `models/tts/`

## Consideraciones de rendimiento

En CPU, la latencia total depende principalmente de tres etapas:

- transcripción de voz
- generación del LLM local
- síntesis de voz

Para hardware modesto conviene:

- usar un modelo ASR pequeño como `tiny`
- limitar contexto y longitud de salida del LLM
- mantener respuestas breves
- precargar modelos si se busca una experiencia más estable

## Limitaciones conocidas

- depende de la calidad estructural del CSV cargado
- no reemplaza análisis causal formal ni modelado estadístico profundo
- la latencia del modelo local puede ser perceptible en CPU
- la precisión de la transcripción depende del micrófono y del entorno acústico
- la calidad final de voz depende de la voz Piper instalada

## Casos de uso recomendados

- revisión rápida de resultados mensuales
- análisis operativo de sucursales o canales
- diagnóstico inicial de deterioro en ingresos o márgenes
- discusión ejecutiva apoyada en datos exportados a CSV
- prototipado de asistentes locales para análisis de negocio

## Resultado esperado

El resultado esperado es una herramienta local que permite pasar de un archivo CSV a una conversación analítica guiada por texto o voz, con respuestas comprensibles, contexto de negocio y apoyo concreto para la toma de decisiones.
