from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

REQUIRED_VARS = (
    "ANTHROPIC_API_KEY",
    "TAVILY_API_KEY",
    "EXA_API_KEY",
    "DATABASE_URL",
    "FINGERPRINT_SALT",
    "TEAM_FINGERPRINTS",
    "GOOGLE_MAPS_API_KEY",
)

# Saved traveler preferences are optional: all of these enable them, none leaves them off.
TRAVELER_MEMORY_VARS = (
    "ATOMICMEMORY_API_URL",
    "ATOMICMEMORY_API_KEY",
    "TRAVELER_COOKIE_SECRET",
    "PUBLIC_ORIGIN",
)
MIN_COOKIE_SECRET_LENGTH = 32


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class TravelerMemorySettings:
    api_url: str
    api_key: str
    cookie_secret: str
    public_origin: str


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    tavily_api_key: str
    exa_api_key: str
    database_url: str
    fingerprint_salt: str
    team_fingerprints: frozenset[str]
    google_maps_api_key: str
    traveler_memory: TravelerMemorySettings | None = None


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
        traveler_memory=_traveler_memory(env),
    )


def _traveler_memory(env: Mapping[str, str]) -> TravelerMemorySettings | None:
    present = [name for name in TRAVELER_MEMORY_VARS if env.get(name)]
    if not present:
        return None
    # Half a configuration would silently run without saved preferences, so it is an error.
    missing = [name for name in TRAVELER_MEMORY_VARS if name not in present]
    if missing:
        raise ConfigError(f"Saved preferences need all of {', '.join(TRAVELER_MEMORY_VARS)}; missing: {', '.join(missing)}")
    if len(env["TRAVELER_COOKIE_SECRET"]) < MIN_COOKIE_SECRET_LENGTH:
        raise ConfigError(f"TRAVELER_COOKIE_SECRET must be at least {MIN_COOKIE_SECRET_LENGTH} characters")
    for name in ("ATOMICMEMORY_API_URL", "PUBLIC_ORIGIN"):
        url = urlsplit(env[name])
        local = url.hostname in ("localhost", "127.0.0.1", "::1")
        if (not url.hostname or url.username or url.password or url.query or url.fragment
                or (url.scheme != "https" and not (url.scheme == "http" and local))):
            raise ConfigError(f"{name} must use HTTPS or loopback HTTP without credentials, query or fragment")
        if name == "PUBLIC_ORIGIN" and url.path not in ("", "/"):
            raise ConfigError("PUBLIC_ORIGIN must contain only scheme, host and port")
    return TravelerMemorySettings(
        api_url=env["ATOMICMEMORY_API_URL"].rstrip("/"),
        api_key=env["ATOMICMEMORY_API_KEY"],
        cookie_secret=env["TRAVELER_COOKIE_SECRET"],
        public_origin=env["PUBLIC_ORIGIN"].rstrip("/"),
    )
