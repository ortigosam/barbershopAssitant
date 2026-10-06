# Webhook inicial de WhatsApp

Este módulo es independiente de la API y del agente actuales. Recibe mensajes
de WhatsApp Cloud API de Meta y responde siempre con esta encuesta:

> ¿Qué necesitas hacer?

- Reservar Cita
- Cancelar Cita
- Ver mis próximas Citas

Las opciones sólo se muestran; todavía no ejecutan ninguna acción. Se envían
como una lista interactiva para conservar el texto completo de cada opción.

## 1. Crear las credenciales en Meta

En [Meta for Developers](https://developers.facebook.com/):

1. Crea una aplicación de tipo Business.
2. Añade el producto **WhatsApp** y crea o vincula un número de prueba.
3. Copia el `Temporary access token` para la primera prueba y el `Phone number ID`.
4. En la configuración básica de la aplicación copia el `App Secret`.
5. Genera un valor largo y aleatorio para `WEBHOOK_VERIFY_TOKEN`. Este valor lo
   escribirás también en el panel de Meta para verificar el webhook.

Para producción, sustituye el token temporal por un token permanente asociado a
un usuario del sistema con los permisos mínimos de WhatsApp Business.

## 2. Configuración local

Desde la raíz del proyecto:

```bash
cp whatsapp/.env.example whatsapp/.env
```

Rellena `whatsapp/.env`:

```dotenv
META_ACCESS_TOKEN=...
META_PHONE_NUMBER_ID=...
META_APP_SECRET=...
WEBHOOK_VERIFY_TOKEN=...
META_API_VERSION=v23.0
```

El archivo `.env` no debe subirse a Git.

## 3. Instalar y levantar el webhook

La forma aislada es instalar sus dependencias y levantar sólo este módulo:

```bash
uv pip install -r whatsapp/requirements.txt
uv run fastapi dev whatsapp/main.py --port 8010
```

El endpoint local será `http://localhost:8010/webhook`.

Meta necesita una URL HTTPS pública. Para desarrollo puedes publicar el puerto
con un túnel como ngrok:

```bash
ngrok http 8010
```

Usa la URL HTTPS que te dé el túnel seguida de `/webhook`, por ejemplo:
`https://tu-subdominio.ngrok-free.app/webhook`.

## 4. Configurar el webhook en Meta

En WhatsApp > Configuration > Webhook:

- Callback URL: URL HTTPS pública más `/webhook`.
- Verify token: exactamente el valor de `WEBHOOK_VERIFY_TOKEN`.
- Suscribe el campo `messages`.

Meta hará una petición `GET` con `hub.mode`, `hub.verify_token` y
`hub.challenge`. El módulo responde el challenge sólo si el token coincide.

Cuando llegue un mensaje, Meta hará un `POST`. El módulo valida
`X-Hub-Signature-256` si `META_APP_SECRET` está configurado, extrae el número
remitente y llama a Graph API para enviar la encuesta. Los eventos de estado que
no contienen `messages` se aceptan sin enviar nada.

## 5. Prueba completa paso a paso

Necesitas tres terminales abiertas. La API principal y Ollama no son necesarios
para esta prueba, porque este webhook todavía no consulta la base de datos ni el
agente.

### Terminal 1: levantar el webhook

Desde la raíz del proyecto:

```bash
uv run fastapi dev whatsapp/main.py --port 8010
```

Comprueba que aparece:

```text
Uvicorn running on http://127.0.0.1:8010
```

### Terminal 2: publicar el puerto con ngrok

Si aún no lo tienes instalado en macOS:

```bash
brew install ngrok
```

Configura una sola vez el authtoken de tu cuenta de ngrok:

```bash
ngrok config add-authtoken TU_AUTHTOKEN
```

Después inicia el túnel:

```bash
ngrok http 8010
```

Busca la línea `Forwarding`. Tendrás una URL parecida a:

```text
https://abc123.ngrok-free.dev -> http://localhost:8010
```

La URL pública del webhook será esa dirección seguida de `/webhook`:

```text
https://abc123.ngrok-free.dev/webhook
```

### Configurar la URL en Meta

En Meta Developers abre tu aplicación y entra en:

```text
WhatsApp → Configuration → Webhooks
```

Introduce:

- **Callback URL**: la URL pública de ngrok terminada en `/webhook`.
- **Verify token**: exactamente el valor de `WEBHOOK_VERIFY_TOKEN` que tienes en
  `whatsapp/.env`.

Pulsa **Verify and Save** y suscribe el campo `messages`.

Meta hará un `GET /webhook` para validar la URL. Si el token coincide, el
servidor devuelve el `hub.challenge` y Meta confirma la configuración.

### Terminal 3: comprobar la verificación manualmente

También puedes probar el endpoint local con:

```bash
curl "http://localhost:8010/webhook?hub.mode=subscribe&hub.verify_token=TU_TOKEN&hub.challenge=12345"
```

La respuesta correcta es:

```text
12345
```

### Enviar el primer mensaje

1. En Meta añade tu número personal como destinatario de prueba si usas el
   número de prueba de WhatsApp.
2. Desde ese teléfono, escribe `Hola` al número de WhatsApp Business.
3. Meta enviará un `POST /webhook` al túnel de ngrok.
4. El servidor extraerá el número del remitente y llamará a la Graph API de
   Meta.
5. Recibirás una lista con `Reservar Cita`, `Cancelar Cita` y `Ver mis próximas
   Citas`.

Puedes ver las peticiones recibidas en el inspector de ngrok:

```text
http://127.0.0.1:4040
```

En la terminal del webhook deberías ver una petición parecida a:

```text
POST /webhook 200 OK
```

### Si reinicias ngrok

En el plan gratuito la URL puede cambiar al reiniciar el túnel. Si cambia,
actualiza la Callback URL en Meta y vuelve a pulsar **Verify and Save**. El
`WEBHOOK_VERIFY_TOKEN` no cambia mientras mantengas el mismo valor en
`whatsapp/.env`.

## 6. Prueba rápida del endpoint

Verifica el endpoint con la misma forma que usa el panel de Meta:

```bash
curl "http://localhost:8010/webhook?hub.mode=subscribe&hub.verify_token=TU_TOKEN&hub.challenge=12345"
```

La respuesta correcta es `12345`. Después escribe al número de prueba desde un
número autorizado en Meta. Cada mensaje debe recibir la encuesta.

Para probar sólo la extracción sin llamar a Meta, importa `incoming_senders` en
una prueba Python. Para probar el envío real se necesita un token válido y un
número de WhatsApp configurado en Meta.

## 7. Límites actuales

Este módulo no llama al agente, no consulta PostgreSQL, no crea clientes y no
reserva, cancela ni consulta citas. Es sólo el canal inicial. La siguiente fase
puede mapear los `reply.id` (`reserve_booking`, `cancel_booking` y
`list_bookings`) a la API existente, validando siempre el negocio y el teléfono
antes de ejecutar una operación.
