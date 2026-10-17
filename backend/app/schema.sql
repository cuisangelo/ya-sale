CREATE TABLE IF NOT EXISTS legs (
    id          BIGSERIAL PRIMARY KEY,
    origin      TEXT NOT NULL,
    destination TEXT NOT NULL,
    mode        TEXT NOT NULL,
    UNIQUE (origin, destination, mode)
);

CREATE TABLE IF NOT EXISTS leg_versions (
    id         BIGSERIAL PRIMARY KEY,
    leg_id     BIGINT NOT NULL REFERENCES legs (id) ON DELETE CASCADE,
    data       JSONB NOT NULL,
    source_url TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS leg_versions_leg_id ON leg_versions (leg_id, id);

CREATE TABLE IF NOT EXISTS confirmations (
    id           BIGSERIAL PRIMARY KEY,
    version_id   BIGINT NOT NULL REFERENCES leg_versions (id) ON DELETE CASCADE,
    fingerprint  TEXT NOT NULL,
    display_name TEXT,
    kind         TEXT NOT NULL CHECK (kind IN ('confirmation', 'correction')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (version_id, fingerprint)
);

CREATE TABLE IF NOT EXISTS trips (
    id          BIGSERIAL PRIMARY KEY,
    origin      TEXT NOT NULL,
    destination TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Every offer the last refresh found for a leg, each with its own source; replaced on each refresh.
ALTER TABLE legs ADD COLUMN IF NOT EXISTS options JSONB NOT NULL DEFAULT '[]';

CREATE TABLE IF NOT EXISTS places (
    key        TEXT PRIMARY KEY,
    lat        DOUBLE PRECISION,
    lng        DOUBLE PRECISION,
    fetched_at TIMESTAMPTZ NOT NULL
);
