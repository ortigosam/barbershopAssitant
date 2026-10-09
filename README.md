# Barbershop Assistant

## Descripción del producto

Asistente de citas con LangChain, **Qwen3:4b local mediante Ollama**, FastAPI,
PostgreSQL y una agenda web privada para el barbero. No necesita OpenAI.

El cliente puede consultar/crear su ficha, actualizar su nombre, consultar sus
citas, buscar huecos, reservar y cancelar. La web muestra una agenda semanal:
pulsa una cita para cancelarla o un espacio para crear otra. Permite configurar
horarios, festivos y vacaciones sin volver a desplegar.

### Reglas de negocio

- Un barbero, cortes de 20 minutos sin margen. Lunes–viernes 10:00–14:00 y
  17:00–21:00; sábado 10:00–14:00; domingo cerrado. Son horarios modificables.
- Las citas pueden terminar exactamente al cierre. Una excepción sustituye el
  horario completo de una fecha; sin intervalos significa cerrado.
- Sólo esta semana y la siguiente (lunes–domingo), hora local `Europe/Madrid`.
  Reservar y cancelar exige `ahora < inicio`.
- Máximo cinco citas por cliente y mes de la cita, incluyendo realizadas y futuras.
  Cancelar borra la cita y libera el hueco y el cupo.
- Los cortes consecutivos son citas independientes reservadas atómicamente:
  si algún hueco falla, no se crea ninguna.
- El estado `completed` se calcula al consultar cuando han pasado los 20 minutos.
  No necesita un proceso programado ni demuestra asistencia.
- Se bloquean cambios de horario incompatibles con citas futuras o en curso.
- Los teléfonos internacionales conservan el prefijo para evitar colisiones.
  Se normalizan espacios, guiones y `00`. Nueve dígitos españoles usan `+34`;
  para otros países indica el prefijo internacional.

## Instalación y configuración

Necesitas Python 3.12/3.13, uv, Docker Desktop y Ollama. Desde la raíz:

```bash
uv sync --all-packages
```

Cada componente lee su propio archivo. `.env.example` sólo es una plantilla;
en una instalación nueva cópiala a `.env` y sustituye los valores de ejemplo.

| Archivo | Variables |
| --- | --- |
| `database/.env` | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` |
| `api/.env` | Las mismas credenciales, `POSTGRES_HOST=localhost`, `POSTGRES_PORT=5432`, `ADMIN_API_TOKEN`, `AGENT_API_TOKEN` |
| `agent/.env` | `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `BARBERSHOP_API_URL`, `AGENT_API_TOKEN` |

Las variables del proceso tienen prioridad. Los `.env` reales están ignorados
por Git. Genera dos claves distintas ejecutando dos veces:

```bash
uv run python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Una será `ADMIN_API_TOKEN` (web) y otra `AGENT_API_TOKEN` (canal). La segunda
debe coincidir en API y agente. **En esta instalación local ya están configuradas.**
No las compartas. Reinicia API/agente después de cambiar variables de entorno.

### 1. Levantar PostgreSQL con Docker

Abre Docker Desktop. Si ya está configurado el arranque automático, basta con
esperar a que `barbershop-assistant-postgres` aparezca como **Running**.
La política `unless-stopped` no arranca un contenedor detenido expresamente;
en ese caso pulsa Start. Alternativa desde la raíz:

```bash
docker compose --env-file database/.env -f database/docker-compose.yml up -d
```

PostgreSQL queda en `localhost:5432`. Debe estar activo porque guarda clientes,
horarios y reservas; el volumen conserva los datos entre reinicios.

**Base nueva**, una sola vez desde la raíz:

```bash
docker exec -i barbershop-assistant-postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < database/schema.sql
```

**Base de una versión anterior**, aplica en su lugar:

```bash
docker exec -i barbershop-assistant-postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < database/migrations/002_calendar.sql
```

La migración 002 **ya está aplicada en esta instalación**. Crea `appointment`,
`calendar_settings` y `calendar_receipt`. Conserva clientes y tablas anteriores,
pero la nueva agenda **no utiliza ni importa las antiguas citas de prueba de
30 minutos**. No borra esos datos. La migración 001 es histórica y no hace falta
para la nueva agenda. No ejecutes `schema.sql` sobre una base existente.

### 2. Levantar la API y la web

En otra terminal, desde la raíz:

```bash
cd api
uv run fastapi dev api/src/main.py
```

Mantén la terminal abierta. La API aplica las reglas y las transacciones; el
agente y la web no acceden directamente a PostgreSQL.

- Agenda: [http://localhost:8000](http://localhost:8000). Introduce el valor
  `ADMIN_API_TOKEN` de `api/.env`; sólo se mantiene en memoria del navegador.
- Documentación HTTP: [http://localhost:8000/docs](http://localhost:8000/docs).

La web no necesita Node ni un servidor adicional. Pulsa una cita para cancelarla;
**Horarios y cierres** permite editar la configuración. La agenda
se refresca cada minuto y tiene actualización manual.

### 3. Instalar y levantar el modelo local

En macOS, con Homebrew instalado:

```bash
brew install ollama
ollama serve
```

El primer comando descarga e instala Ollama. El segundo mantiene su API local
en `http://localhost:11434`. Si ya está ejecutándose, no abras otra instancia.
En otra terminal descarga el modelo una sola vez:

```bash
ollama pull qwen3:4b
ollama list
```

Configuración de `agent/.env`:

```dotenv
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:4b
BARBERSHOP_API_URL=http://localhost:8000
AGENT_API_TOKEN=el_mismo_secreto_de_canal_que_en_api
```

Ollama interpreta los mensajes, FastAPI ejecuta las operaciones y Docker aloja
los datos. Los tres deben permanecer activos. No necesitas API key cloud.

### 4. Probar el agente

Desde la raíz:

```bash
uv run python -m agent.cli --phone +34600123456
```

Sin `--phone`, el CLI pide el número inicial. Este número **simula el remitente
autenticado**; Qwen no lo extrae del mensaje. Prueba:

```text
¿Existe mi ficha?
Crea mi ficha, me llamo Ana.
¿Qué huecos hay la próxima semana?
Quiero reservar el [fecha disponible] a las 10:00.
Consulta mis citas.
Cancela mi cita.
¿Cuál es la capital de Francia?
salir
```

Si tienes varias citas, muestra las tuyas y pregunta cuál gestionar. Una reserva
confirmada siempre usa este formato, con los datos devueltos por la API:
`Nos vemos el martes 6 de octubre a las 10:00.`
Un timeout produce resultado incierto y pide comprobar las citas antes de repetir.

## Arquitectura, seguridad y rendimiento

```text
CLI / futuro WhatsApp -> agente + tools HTTP ─┐
Web del barbero -----------------------------┤
                                            v
API -> aplicación -> dominio
            |
     puerto de persistencia -> PostgreSQL
```

- `api/src/domain`: reglas puras de calendario, teléfonos y límites temporales.
- `api/src/application`: casos de uso, cupos, propiedad y transacciones;
  depende de contratos `Protocol`, no de FastAPI ni PostgreSQL.
- `api/src/repositories`: adaptador PostgreSQL.
- `api/src/api`: adaptación HTTP/autenticación. `agent/` y `web/` son clientes.

Esto aplica responsabilidad única e inversión de dependencias sin jerarquías
innecesarias. Para un barbero, un bloqueo transaccional de agenda serializa
operaciones y protege cupos y cambios de horario. Una restricción de exclusión
PostgreSQL impide solapamientos incluso en SQL directo. Mover libera y ocupa
en la misma transacción. La respuesta de éxito sale después del commit.

Cada creación lleva un UUID: repetir la misma petición no duplica citas.
Cancelar borra la cita e invalida su recibo, conservando únicamente el identificador
y hash de la operación, no un historial de la cita. El reintento no la resucita.

El agente combina JSON estructurado, lista cerrada de operaciones, validación
Pydantic, estado conversacional y plantillas deterministas. No publica texto
libre de Qwen. Las cuestiones ajenas reciben una plantilla de alcance. Esto
reduce prompt injection, pero no garantiza clasificación perfecta: los permisos
y las reglas se comprueban siempre fuera del modelo.

Una llamada al modelo por mensaje, sin historial completo ni listas de huecos;
sin segunda llamada para redactar. Razonamiento desactivado, salida limitada,
modelo cargado durante 30 minutos y conexiones HTTP reutilizadas. Elegir una
cita por su número evita incluso la llamada al modelo.

**WhatsApp todavía no está conectado.** Al elegir proveedor, su adaptador debe
validar la firma del webhook, deduplicar mensajes, extraer el remitente verificado
y mantener una conversación por teléfono. La identidad se inyecta fuera del LLM.
La API exige secreto de canal y `X-Customer-Phone`; el modelo no puede elegir
ese header. El CLI no prueba posesión del teléfono: es una simulación local.

El secreto administrativo es una solución inicial local. Antes de publicar:
HTTPS, login/sesiones de administrador, limitación de peticiones y gestión de
secretos. No publiques la API de desarrollo ni expongas claves en JavaScript.

## Comprobaciones

Desde la raíz:

```bash
PYTHONPATH=api:api/tests:. uv run pytest -q tests api/tests
```

Con PostgreSQL y Ollama activos:

```bash
RUN_POSTGRES_TESTS=1 RUN_OLLAMA_TESTS=1 PYTHONPATH=api:api/tests:. uv run pytest -q tests api/tests
```

Las pruebas PostgreSQL utilizan un esquema temporal independiente y lo eliminan
al terminar. Las del modelo usan tools simuladas. Se comprueban propiedad,
límites, concurrencia, idempotencia, cancelación, cambios atómicos y Qwen real.
