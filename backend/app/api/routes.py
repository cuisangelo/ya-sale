import json
from dataclasses import asdict, replace
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api import guards
from app.legs.domain import LegKey, LegVersion, display_version, leg_status
from app.legs.repository import AlreadyConfirmed, LegNotFound
from app.trips.events import LegRefreshed, LegStored, TripEvent

router = APIRouter(prefix="/api")

_EVENT_NAMES = {
    "TripStarted": "trip_started",
    "LegStored": "leg_stored",
    "LegRefreshed": "leg_refreshed",
    "LegError": "leg_error",
    "NoRoute": "no_route",
    "TripDone": "trip_done",
}


class TripRequest(BaseModel):
    origin: str = Field(min_length=2, max_length=120)
    destination: str = Field(min_length=2, max_length=120)
    date: str = Field(max_length=20)


class ConfirmationRequest(BaseModel):
    version_id: int
    display_name: str | None = Field(default=None, max_length=40)


class CorrectionRequest(BaseModel):
    departure_point: str | None = Field(default=None, max_length=200)
    price_min_pen: Decimal | None = Field(default=None, gt=0, le=5000)
    price_max_pen: Decimal | None = Field(default=None, gt=0, le=5000)
    duration_min: int | None = Field(default=None, ge=1, le=4320)
    display_name: str | None = Field(default=None, max_length=40)


def _version_json(version: LegVersion) -> dict:
    data = {k: str(v) if isinstance(v, Decimal) else v for k, v in asdict(version.data).items()}
    return {
        "id": version.id,
        **data,
        "source_url": version.source_url,
        "fetched_at": version.fetched_at.isoformat(),
        "confirmations": version.confirmations,
    }


def _summary(leg_id: int, key: LegKey, versions: list[LegVersion]) -> dict:
    return {
        "leg_id": leg_id,
        "mode": key.mode,
        "origin": key.origin,
        "destination": key.destination,
        "status": leg_status(versions),
        "version": _version_json(display_version(versions)),
    }


def _event_json(event: TripEvent) -> dict:
    if isinstance(event, (LegStored, LegRefreshed)):
        return {
            "index": event.index, "leg_id": event.leg_id, "mode": event.mode,
            "origin": event.origin, "destination": event.destination,
            "status": event.status, "version": _version_json(event.version),
        }
    return asdict(event)


def _services(request: Request):
    return request.app.state.services


def _settings(request: Request):
    return request.app.state.settings


@router.post("/trips")
async def create_trip(body: TripRequest, request: Request) -> StreamingResponse:
    services = _services(request)
    visitor = guards.fingerprint(request, _settings(request).fingerprint_salt)
    if not services.limiter.allow(visitor):
        raise HTTPException(429, "Demasiadas consultas seguidas. Espera un minuto.")
    trip_id = await services.usage.record_trip(body.origin, body.destination, visitor)

    async def stream():
        async for event in services.planner.plan(body.origin, body.destination, body.date, trip_id=trip_id):
            yield f"event: {_EVENT_NAMES[type(event).__name__]}\ndata: {json.dumps(_event_json(event))}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


async def _leg_or_404(request: Request, leg_id: int) -> tuple[LegKey, list[LegVersion]]:
    try:
        return await _services(request).legs.get(leg_id)
    except LegNotFound:
        raise HTTPException(404, "Tramo no encontrado.") from None


@router.get("/legs/{leg_id}")
async def get_leg(leg_id: int, request: Request) -> dict:
    key, versions = await _leg_or_404(request, leg_id)
    summary = _summary(leg_id, key, versions)
    return {k: v for k, v in summary.items() if k != "version"} | {"versions": [_version_json(v) for v in versions]}


@router.post("/legs/{leg_id}/confirmations", status_code=201)
async def confirm_leg(leg_id: int, body: ConfirmationRequest, request: Request) -> dict:
    _, versions = await _leg_or_404(request, leg_id)
    if body.version_id not in {v.id for v in versions}:
        raise HTTPException(404, "Versión no encontrada.")
    visitor = guards.fingerprint(request, _settings(request).fingerprint_salt)
    try:
        await _services(request).legs.confirm(body.version_id, visitor, body.display_name)
    except AlreadyConfirmed:
        raise HTTPException(409, "Ya confirmaste este tramo.") from None
    key, versions = await _leg_or_404(request, leg_id)
    return _summary(leg_id, key, versions)


@router.post("/legs/{leg_id}/corrections", status_code=201)
async def correct_leg(leg_id: int, body: CorrectionRequest, request: Request) -> dict:
    _, versions = await _leg_or_404(request, leg_id)
    changes = body.model_dump(exclude_none=True, exclude={"display_name"})
    corrected = replace(versions[-1].data, **changes)
    visitor = guards.fingerprint(request, _settings(request).fingerprint_salt)
    await _services(request).legs.correct(leg_id, corrected, visitor, body.display_name)
    key, versions = await _leg_or_404(request, leg_id)
    return _summary(leg_id, key, versions)


@router.get("/usage")
async def usage(request: Request) -> dict:
    return await _services(request).usage.summary()
