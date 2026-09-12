CREATE TABLE client (
    telephone VARCHAR(20) PRIMARY KEY,
    name VARCHAR(59) NOT NULL
);

CREATE TABLE booking (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL UNIQUE,
    telephone VARCHAR(20) NOT NULL,

    CONSTRAINT fk_booking_client
        FOREIGN KEY (telephone)
        REFERENCES client(telephone)
);