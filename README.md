# Barbershop Assistant

## Probar el agente con Qwen y Ollama

Instala Ollama, descarga un modelo Qwen y comprueba el nombre exacto:

```bash
ollama serve
ollama pull qwen3:8b
ollama list
```

Configura `OLLAMA_MODEL` en `.env` si has descargado otro modelo. Arranca la
API de la barbería y ejecuta:

```bash
uv run python -m agent.cli
```

Después escribe mensajes como `¿Qué huecos hay la próxima semana?`.
