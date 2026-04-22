# Asistente de voz basado en datos

La app usa Python para cargar, limpiar, normalizar y consolidar el CSV.
Las respuestas para el usuario deben venir del LLM local.

## Modos admitidos

- `servidor_local`: recomendado. Usa un servidor local compatible con OpenAI.
- `llama_cpp`: carga un `.gguf` directamente desde Python si instalas `requirements-llama-cpp.txt`.
- `pruebas`: solo para tests y `scripts/smoke_test.py`.

## Arranque recomendado con servidor local

1. Instala la app base.
2. Instala el backend opcional del servidor:

```powershell
pip install -r requirements-llama-cpp.txt
python -m llama_cpp.server --model .\models\llm\model.gguf --host 127.0.0.1 --port 8080 --n_ctx 1024 --n_threads 4 --n_threads_batch 4
```

3. En otra terminal:

```powershell
python app.py
```

## Notas

- Si no hay servidor LLM encendido, la app abrirá pero te avisará al intentar responder.
- El CSV mensual y el CSV complejo vienen en `examples/`.
- La salida de voz depende de que coloques una voz Piper válida en `models/tts/`.
