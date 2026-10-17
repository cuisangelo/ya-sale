from dataclasses import asdict
from decimal import Decimal

from app.legs.domain import LegStatus, LegVersion, Mode


def version_json(version: LegVersion) -> dict:
    data = {k: str(v) if isinstance(v, Decimal) else v for k, v in asdict(version.data).items()}
    return {
        "id": version.id,
        **data,
        "source_url": version.source_url,
        "fetched_at": version.fetched_at.isoformat(),
        "confirmations": version.confirmations,
    }


def leg_summary_json(leg_id: int, mode: Mode, origin: str, destination: str, status: LegStatus, version: LegVersion) -> dict:
    return {
        "leg_id": leg_id,
        "mode": mode,
        "origin": origin,
        "destination": destination,
        "status": status,
        "version": version_json(version),
    }
