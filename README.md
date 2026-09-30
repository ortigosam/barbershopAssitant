# Barbershop Assistant

Asistente conversacional para una barbería construido con LangChain, FastAPI,
PostgreSQL y un modelo Qwen ejecutado localmente mediante Ollama.

## Descripción del producto

El usuario puede interactuar con el agente en lenguaje natural para:

- crear y consultar clientes;
- consultar huecos disponibles durante la semana actual o la siguiente;
- reservar una cita para un cliente;
- cancelar una reserva;
- editar la fecha, hora o cliente de una reserva.

El agente no accede directamente a la base de datos. Utiliza tools de
LangChain que llaman a la API de FastAPI. La API contiene las reglas de
negocio y es la fuente única de verdad para clientes y reservas.

La arquitectura local es:

```text
Usuario -> agente LangChain + Qwen/Ollama -> tools HTTP -> API FastAPI -> PostgreSQL
```

Las citas tienen una duración de 30 minutos y, por defecto, sólo se permiten
de lunes a sábado, de 10:00 a 14:00 y de 16:00 a 20:00.

## Instalación y configuración

### Requisitos

- Python 3.12 o superior, pero inferior a 3.14.
- `uv` para instalar y ejecutar el proyecto.
- Docker y Docker Compose.
- Ollama.
- Un modelo Qwen instalado en Ollama.

Instala las dependencias del proyecto desde la raíz:

```bash
uv sync
```

### Archivos de configuración

Cada componente tiene su propia configuración:

- `database/.env`: credenciales que Docker utiliza para crear PostgreSQL.
- `api/.env`: credenciales y host/puerto que FastAPI usa para conectarse a PostgreSQL.
- `agent/.env`: URL y nombre del modelo local de Ollama.

No subas los archivos `.env` reales al repositorio.

Ejemplo de `database/.env`:

```env
POSTGRES_USER=barbershop
POSTGRES_PASSWORD=barbershop
POSTGRES_DB=barbershop
```

Ejemplo de `api/.env`:

```env
POSTGRES_USER=barbershop
POSTGRES_PASSWORD=barbershop
POSTGRES_DB=barbershop
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

Ejemplo de `agent/.env`:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:4b
```

## Ejecución local

Cada proceso debe mantenerse ejecutándose en una terminal independiente.

### 1. Levantar PostgreSQL con Docker

Abre Docker Desktop y arranca el proyecto o contenedor de PostgreSQL que
tengas configurado. Si Docker Desktop está configurado para iniciar ese
proyecto automáticamente, bastará con abrir la aplicación y esperar a que el
contenedor aparezca como `Running`.

Esto inicia el contenedor `barbershop-assistant-postgres` y publica
PostgreSQL en `localhost:5432`.

Como alternativa, puedes arrancarlo desde la terminal, desde la raíz del
proyecto:

```bash
cd database
docker compose --env-file .env up -d
```

Se necesita levantarlo porque la API guarda y consulta ahí los clientes y las
reservas. Sin PostgreSQL, los endpoints de FastAPI no pueden funcionar.

La primera vez hay que crear las tablas. Puedes hacerlo desde una terminal:

```bash
docker exec -i barbershop-assistant-postgres \
  psql -U barbershop -d barbershop < schema.sql
```

También puedes abrir una terminal dentro del contenedor desde Docker Desktop
y ejecutar allí el mismo comando adaptando la ruta a `schema.sql`.

Si has elegido otro usuario o base de datos, sustituye esos valores. Puedes
comprobar el contenedor con:

```bash
docker compose ps
```

### 2. Levantar el servidor API

En una segunda terminal, desde la raíz:

```bash
cd api
uv run fastapi dev api/src/main.py
```

La API queda disponible en `http://localhost:8000` y su documentación
interactiva en `http://localhost:8000/docs`.

Hay que mantener este servidor activo porque las tools del agente no llaman a
PostgreSQL directamente: llaman a endpoints como `POST /clients`,
`GET /bookings/availability?week=current|next`, `POST /bookings`,
`PUT /bookings/{booking_id}` y `DELETE /bookings/{booking_id}`.

### 3. Levantar Ollama y el modelo Qwen

En macOS puedes instalar Ollama mediante Homebrew. Si todavía no tienes
Homebrew, instálalo desde [brew.sh](https://brew.sh/). Después ejecuta:

```bash
brew install ollama
```

Este comando descarga e instala Ollama en tu equipo. Una vez instalado,
arranca el servidor local en una tercera terminal:

```bash
ollama serve
```

`ollama serve` deja disponible la API local de Ollama en
`http://localhost:11434`, que es la dirección utilizada por el agente.

En una cuarta terminal, descarga el modelo una sola vez:

```bash
ollama pull qwen3:4b
ollama list
```

Hay que mantener Ollama activo porque LangChain utiliza `ChatOllama` para
enviar el mensaje al modelo local y recibir sus decisiones sobre qué tool
ejecutar. No se necesita una API key de OpenAI ni un proveedor cloud.

### 4. Probar el agente

Con PostgreSQL, FastAPI y Ollama activos, ejecuta desde la raíz:

```bash
uv run python -m agent.cli
```

Prueba, por ejemplo:

```text
¿Qué huecos hay disponibles la próxima semana?
```

```text
Quiero reservar el lunes a las 10:00. Me llamo Carlos y mi teléfono es 600123456.
```

Escribe `salir` para terminar. También puedes verificar directamente la API:

```bash
curl "http://localhost:8000/bookings/availability?week=next"
```

## Parar los servicios

Para apagar PostgreSQL sin borrar sus datos:

```bash
cd database
docker compose stop
```

Para volver a arrancarlo usa `docker compose start`. Para detener y eliminar
el contenedor conservando el volumen de datos usa `docker compose down`.
`uvicorn` y `ollama serve` se detienen con `Ctrl+C` en sus terminales.
