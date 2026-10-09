# Reservas por WhatsApp

El webhook recibe mensajes firmados de Meta y utiliza la API de la barbería.
Un saludo muestra «¿Qué necesitas hacer?»:

- **Reservar Cita**: días libres de esta semana y la siguiente → horas libres →
  comprobar ficha y preguntar nombre si no existe → reservar una cita de 20 minutos.
  La API vuelve a comprobar disponibilidad y cupo al guardar. Sólo tras confirmarlo:
  «Reserva aceptada. Nos vemos el miércoles 7 de octubre a las 10:00.».
- **Cancelar Cita**: consultar citas propias → elegir cita → cancelar mediante
  la API → «Cita cancelada con éxito.».
Escribe **menú** para volver al inicio. Las listas largas tienen ocho opciones
por página y navegación Anterior/Más opciones. Sin huecos o citas se informa al cliente.
Horarios, cierres, límites y zona Europe/Madrid siguen siendo responsabilidad de la API.
El modelo de lenguaje no interviene.

## Arquitectura

| Archivo | Responsabilidad |
| --- | --- |
| main.py | Firma HMAC, extracción de mensajes y composición de dependencias |
| contracts.py | Protocols de API y mensajería |
| workflow.py | Recorridos deterministas, opciones y respuestas |
| booking_api.py | Adaptador HTTP de la API existente |
| meta_client.py | Envío a Meta |

El teléfono procede del evento firmado, se normaliza con + y se envía como
X-Customer-Phone con AGENT_API_TOKEN. La API comprueba la propiedad de cada cita.
Sólo se procesan eventos del META_PHONE_NUMBER_ID configurado. No se aceptan
selecciones de otro teléfono ni de un menú sustituido. META_APP_SECRET es obligatorio.

El webhook no utiliza una base de datos propia. Conserva temporalmente en memoria
la selección de cada teléfono y los eventos recientes, con caducidad de una hora.
Al reiniciar se pierden los menús en curso: basta escribir menú de nuevo. Los datos
de clientes y citas permanecen en PostgreSQL a través de la API existente.

Las reservas incluyen request_id estable para los reintentos de un mismo hueco
ofrecido. Ante timeout se informa de que no puede confirmarse, sin inventar una
confirmación.
Los duplicados de un evento se omiten mientras están en memoria. Esta versión
utiliza un único worker; antes de desplegar varias instancias habrá que compartir
el estado de los menús. No garantiza entrega exactamente una vez de mensajes.

### Llamadas directas a la API existente

| Selección recibida en el webhook | Petición a api/ |
| --- | --- |
| Reservar Cita | GET /bookings/availability para esta semana y la siguiente |
| Día | GET /bookings/availability y filtrar el día seleccionado |
| Hora | GET /clients/me y POST /bookings |
| Nombre de cliente nuevo | POST /clients/me, después POST /bookings |
| Cancelar Cita | GET /bookings |
| Cita elegida para cancelar | DELETE /bookings/{id} |

El cliente HTTP adjunta siempre Authorization: Bearer AGENT_API_TOKEN y
X-Customer-Phone con el remitente del evento. Nunca llama a los endpoints /admin.
El webhook presenta menús; api/ calcula los huecos y guarda o elimina las citas.

## Configuración

Si ya tienes un .env configurado, consérvalo. Para una instalación nueva:

```bash
test -f whatsapp/.env || cp whatsapp/.env.example whatsapp/.env
```

Variables de whatsapp/.env:

```dotenv
META_ACCESS_TOKEN=token_de_meta
META_PHONE_NUMBER_ID=id_del_numero_business
META_APP_SECRET=secreto_de_la_aplicacion_meta
WEBHOOK_VERIFY_TOKEN=token_elegido_por_ti
META_API_VERSION=v23.0
BARBERSHOP_API_URL=http://127.0.0.1:8000
AGENT_API_TOKEN=mismo_valor_que_en_api
```

Para facilitar la configuración local, se carga primero api/.env y después
whatsapp/.env: así AGENT_API_TOKEN se reutiliza si no lo defines en el segundo.
Las variables del proceso tienen prioridad. No se usa ADMIN_API_TOKEN para
gestionar citas de clientes. En un despliegue separado, configura explícitamente
AGENT_API_TOKEN y BARBERSHOP_API_URL en el servicio WhatsApp. Reinicia después
de cambiar .env. No publiques credenciales ni archivos de estado.

En Meta Developers, dentro de tu aplicación:

- WhatsApp / API Setup: token de acceso y Phone Number ID (no el teléfono literal).
- Configuración básica: App Secret.
- WEBHOOK_VERIFY_TOKEN lo generas tú, por ejemplo con openssl rand -hex 32.
  Debe coincidir en .env y en el formulario de verificación de Meta.

El token temporal de Meta debe renovarse cuando caduque. Consulta su expiración
en el panel. Para uso continuo configura credenciales de sistema apropiadas.

## Prueba local paso a paso

1. Abre Docker Desktop y comprueba que PostgreSQL está activo.
2. Desde la raíz, arranca la API principal si no está ya levantada:

```bash
uv run fastapi dev api/src/main.py
```

3. En otra terminal, desde la raíz, arranca el webhook:

```bash
uv run fastapi dev whatsapp/main.py --port 8010
```

Las dependencias del módulo figuran en whatsapp/requirements.txt. La instalación
actual del proyecto ya dispone de ellas. Para un entorno separado, instálalas
allí con uv pip install -r whatsapp/requirements.txt.

4. En otra terminal, publica el webhook:

```bash
ngrok http 8010
```

Si falta ngrok, instala con brew install ngrok. Registra una vez tu authtoken
con ngrok config add-authtoken TU_AUTHTOKEN, obtenido desde el panel de tu cuenta.

5. En Meta, configura Callback URL con la URL HTTPS mostrada por ngrok más
   /webhook. Ejemplo: https://tu-dominio.ngrok-free.dev/webhook.
   En Verify token pega WEBHOOK_VERIFY_TOKEN. Pulsa Verify and Save y suscribe messages.
   Si esto ya está hecho y la URL sigue siendo la misma, no hay que repetirlo.
6. Para comprobar manualmente la verificación local, desde otra terminal:

```bash
curl "http://localhost:8010/webhook?hub.mode=subscribe&hub.verify_token=TU_TOKEN&hub.challenge=12345"
```

Debe devolver 12345. GET valida la configuración; los mensajes llegan por POST.

7. Si usas el número de prueba de Meta, autoriza tu teléfono en su panel.
8. Envía Hola desde ese teléfono. Pulsa Reservar Cita. Selecciona directamente
   un día disponible y después una hora. Si es nuevo, escribe tu nombre.
   Recibirás confirmación y aparecerá en la agenda.
9. Escribe menú, elige Cancelar Cita y selecciona esa cita. Comprueba la
    confirmación y que el hueco vuelve a estar disponible.

### Diagnóstico mediante logs

El webhook registra cada etapa en la terminal donde se ejecuta: mensaje recibido,
teléfono enmascarado, llamada a `api/`, código HTTP, tiempo de respuesta y envío
a Meta. Los tokens nunca se imprimen y el teléfono sólo muestra sus cuatro últimos
dígitos.

Para obtener más detalle:

```bash
LOG_LEVEL=DEBUG uv run fastapi dev whatsapp/main.py --port 8010
```

Mensajes útiles:

- `message_received`: Meta entregó un mensaje válido y qué selección recibió.
- `api_request` / `api_response`: petición a la API principal y su resultado.
- `api_request_network_error`: la API no está accesible o agotó el timeout.
- `meta_send_failed`: Meta rechazó el mensaje o no respondió; revisa el `status`
  y el fragmento de error mostrado.
- `workflow_api_error`: la API respondió un error de negocio, como cliente
  inexistente o hueco ocupado.

Después de cambiar `.env`, reinicia el webhook para cargar la configuración.

Estos pasos crean y cancelan citas reales en tu base. Ollama no es necesario.
Mantén activos API, PostgreSQL, webhook y ngrok. El inspector de ngrok está
normalmente en http://127.0.0.1:4040. Si cambia la URL pública al reiniciar,
actualiza el callback en Meta; si se mantiene, no necesitas reconfigurarlo.

## Errores habituales

- 403 en GET: verify token no coincide.
- 403 en POST: firma incorrecta o App Secret equivocado.
- Mensajes ignorados: comprueba suscripción messages y Phone Number ID.
- No se cargan huecos: comprueba API en 8000, PostgreSQL y AGENT_API_TOKEN.
- 503 al responder: Meta no aceptó/confirmó el envío; comprueba token y destinatario.
  El evento puede reintentarse; mientras siga en memoria reutiliza la respuesta.
- Menú caducado: escribe menú para iniciar de nuevo.

## Pruebas automatizadas sin mensajes reales

Desde la raíz:

```bash
PYTHONPATH=api:api/tests:. uv run pytest -q whatsapp/tests
```

Cubren reserva, paginación, alta de cliente, consulta, cancelación, propiedad,
duplicados, menús antiguos, timeout, reintento del envío, firma,
destinatario Business y contratos con las rutas reales de API usando almacenamiento
de prueba. No realizan envíos reales a Meta ni alteran PostgreSQL.
