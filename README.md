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
