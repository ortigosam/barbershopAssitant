CREATE TABLE client (
    telephone VARCHAR(20) PRIMARY KEY,
    name VARCHAR(59) NOT NULL
);

CREATE TABLE booking_request (
    request_id UUID PRIMARY KEY,
    booking_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    telephone VARCHAR(20) NOT NULL
);

CREATE TABLE booking (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL UNIQUE,
    telephone VARCHAR(20) NOT NULL,

    CONSTRAINT fk_booking_client
        FOREIGN KEY (telephone)
        REFERENCES client(telephone)
);
