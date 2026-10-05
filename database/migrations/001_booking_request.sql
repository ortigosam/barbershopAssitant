-- Apply once to an existing database before starting the updated API.
CREATE TABLE IF NOT EXISTS booking_request (
    request_id UUID PRIMARY KEY,
    booking_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    telephone VARCHAR(20) NOT NULL
);
