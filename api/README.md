# Barbershop Assistant API

The API is the source of truth for customers and appointments. It exposes:

- `POST /clients` — create a customer.
- `GET /clients/{telephone}` — retrieve a customer.
- `GET /bookings/availability?week=current|next` — list free 30-minute slots.
- `POST /bookings` — create an appointment.
- `GET /bookings/{booking_id}` — retrieve an appointment.
- `PUT /bookings/{booking_id}` — change its time and/or customer.
- `DELETE /bookings/{booking_id}` — cancel it.

Appointments use local `Europe/Madrid` wall-clock time and must be on Monday
through Saturday, from 10:00 to 14:00 or 16:00 to 20:00, at 30-minute
intervals. The availability endpoint returns only unoccupied slots (and omits
past times from the current week).
