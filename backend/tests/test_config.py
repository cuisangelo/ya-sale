import pytest

from app.config import ConfigError, load_settings

FULL_ENV = {
    "ANTHROPIC_API_KEY": "a",
    "TAVILY_API_KEY": "t",
    "EXA_API_KEY": "e",
    "DATABASE_URL": "postgresql://x",
    "FINGERPRINT_SALT": "s",
    "TEAM_FINGERPRINTS": "fp1,fp2",
}


def test_missing_vars_are_all_named():
    with pytest.raises(ConfigError) as exc:
        load_settings({"ANTHROPIC_API_KEY": "x"})
    for name in ("TAVILY_API_KEY", "EXA_API_KEY", "DATABASE_URL", "FINGERPRINT_SALT", "TEAM_FINGERPRINTS"):
        assert name in str(exc.value)


def test_empty_team_fingerprints_is_allowed_but_must_be_set():
    settings = load_settings(FULL_ENV | {"TEAM_FINGERPRINTS": ""})
    assert settings.team_fingerprints == frozenset()


def test_team_fingerprints_are_parsed():
    assert load_settings(FULL_ENV).team_fingerprints == frozenset({"fp1", "fp2"})


async def test_health(client):
    response = await client.get("/api/health")
    assert response.json() == {"ok": True}


async def test_schema_bootstrap_creates_tables(pool):
    async with pool.connection() as conn:
        rows = await conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        tables = {row[0] for row in await rows.fetchall()}
    assert {"legs", "leg_versions", "confirmations", "trips"} <= tables
