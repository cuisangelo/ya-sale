from collections.abc import Mapping
from dataclasses import dataclass

REQUIRED_VARS = (
    "ANTHROPIC_API_KEY",
    "TAVILY_API_KEY",
    "EXA_API_KEY",
    "DATABASE_URL",
    "FINGERPRINT_SALT",
    "TEAM_FINGERPRINTS",
    "GOOGLE_MAPS_API_KEY",
)


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    tavily_api_key: str
    exa_api_key: str
    database_url: str
    fingerprint_salt: str
    team_fingerprints: frozenset[str]
    google_maps_api_key: str


def load_settings(env: Mapping[str, str]) -> Settings:
    # TEAM_FINGERPRINTS may be empty, but it must be set so excluding the team is a deliberate choice.
    missing = [name for name in REQUIRED_VARS if name not in env or (name != "TEAM_FINGERPRINTS" and not env[name])]
    if missing:
        raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")
    return Settings(
        anthropic_api_key=env["ANTHROPIC_API_KEY"],
        tavily_api_key=env["TAVILY_API_KEY"],
        exa_api_key=env["EXA_API_KEY"],
        database_url=env["DATABASE_URL"],
        fingerprint_salt=env["FINGERPRINT_SALT"],
        team_fingerprints=frozenset(fp.strip() for fp in env["TEAM_FINGERPRINTS"].split(",") if fp.strip()),
        google_maps_api_key=env["GOOGLE_MAPS_API_KEY"],
    )
