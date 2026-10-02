# API de la barbería

Desde `api/`: `uv run fastapi dev src/main.py`.
Consulta el [README principal](../README.md) para configuración y pruebas.

## Canal del cliente

Requiere `Authorization: Bearer <AGENT_API_TOKEN>` y
`X-Customer-Phone: <remitente verificado>`; nunca extraigas este último del mensaje.

- `GET /clients/me`: consultar ficha.
- `POST /clients/me`: crear (`name`).
- `PUT /clients/me`: guardar nombre (`name`).
- `GET /bookings/availability?week=current|next&count=1`: huecos.
- `GET /bookings`: citas propias próximas.
- `POST /bookings`: `timestamp`, `count` (1–5), `request_id` (UUID).
- `GET /bookings/{id}`: cita propia.
- `PUT /bookings/{id}`: nuevo `timestamp`, mismo propietario.
- `DELETE /bookings/{id}`: borrar y liberar hueco/cupo.

Fechas ISO locales de Madrid sin offset, por ejemplo `2026-10-06T10:00:00`.
Errores de negocio: `code` estable y `detail` para presentación.

## Administración

Requiere `Authorization: Bearer <ADMIN_API_TOKEN>`, distinto del secreto de canal.

- `GET /admin/bookings?start=...&end=...`: agenda por rango.
- `POST /admin/bookings`: reserva más `telephone` y `name`.
- `PUT /admin/bookings/{id}` y `DELETE /admin/bookings/{id}`: gestionar.
- `GET /admin/settings`: horario y versión.
- `PUT /admin/settings`: `weekly`, `exceptions`, `version` recibida al leer.

`weekly` contiene claves `"0"` a `"6"` (lunes–domingo), con listas de pares
`["10:00","14:00"]`. `exceptions` usa fechas `YYYY-MM-DD`, con la misma estructura;
una lista vacía cierra ese día. Cambios incompatibles o versiones obsoletas
devuelven conflicto. La web se sirve en `/`.
