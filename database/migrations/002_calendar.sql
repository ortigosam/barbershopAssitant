-- Additive migration. Legacy booking tables are retained as test archives.
CREATE TABLE IF NOT EXISTS calendar_settings (
    id INTEGER PRIMARY KEY CHECK (id=1),
    weekly JSONB NOT NULL,
    exceptions JSONB NOT NULL DEFAULT '{}',
    version INTEGER NOT NULL DEFAULT 1
);
INSERT INTO calendar_settings(id,weekly) VALUES (1,
'{"0":[["10:00","14:00"],["17:00","21:00"]],"1":[["10:00","14:00"],["17:00","21:00"]],"2":[["10:00","14:00"],["17:00","21:00"]],"3":[["10:00","14:00"],["17:00","21:00"]],"4":[["10:00","14:00"],["17:00","21:00"]],"5":[["10:00","14:00"]],"6":[]}')
ON CONFLICT(id) DO NOTHING;
CREATE TABLE IF NOT EXISTS appointment (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    telephone VARCHAR(20) NOT NULL REFERENCES client(telephone),
    CONSTRAINT appointment_no_overlap EXCLUDE USING gist (
        tsrange(timestamp, timestamp + interval '20 minutes', '[)') WITH &&
    )
);
CREATE INDEX IF NOT EXISTS appointment_customer ON appointment(telephone,timestamp);
CREATE TABLE IF NOT EXISTS calendar_receipt (
    request_id UUID PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    ids JSONB NOT NULL,
    invalidated BOOLEAN NOT NULL DEFAULT false
);
