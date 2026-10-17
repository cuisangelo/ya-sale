from dataclasses import asdict
from decimal import Decimal

from app.legs.domain import LegData, LegOption, LegStatus, LegVersion, Mode


def _data_json(data: LegData) -> dict:
    return {k: str(v) if isinstance(v, Decimal) else v for k, v in asdict(data).items()}


def option_json(option: LegOption) -> dict:
    return {**_data_json(option.data), "source_url": option.source_url, "fetched_at": option.fetched_at.isoformat()}


def version_json(version: LegVersion) -> dict:
    data = _data_json(version.data)
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
