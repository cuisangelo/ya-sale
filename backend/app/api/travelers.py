import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, model_validator

from app.api import guards
from app.config import TravelerMemorySettings
from app.travelers.domain import PreferencesUnavailable, PreferenceStore, Schedule, TravelerPreferences
from app.travelers.identity import COOKIE_MAX_AGE_S, COOKIE_NAME, new_cookie, subject_of

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/travelers/me")


class PreferencesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schedule: Schedule | None = None
    cheapest: bool = False
    # Saving is the consent: without this box ticked nothing is stored and no cookie is set.
    consent: Literal[True]

    @model_validator(mode="after")
    def _chooses_something(self):
        if self.schedule is None and not self.cheapest:
            raise ValueError("choose at least one preference")
        return self


def _body(preferences: TravelerPreferences | None) -> dict:
    saved = None if preferences is None else {"schedule": preferences.schedule, "cheapest": preferences.cheapest}
    return {"enabled": True, "preferences": saved}


def _feature(request: Request) -> tuple[PreferenceStore, TravelerMemorySettings] | None:
    store = request.app.state.services.preferences
    settings = request.app.state.settings.traveler_memory
    return None if store is None or settings is None else (store, settings)


def _enabled_or_404(request: Request) -> tuple[PreferenceStore, TravelerMemorySettings]:
    feature = _feature(request)
    if feature is None:
        raise HTTPException(404, "Las preferencias guardadas no están activadas.")
    return feature


def _same_origin_or_403(request: Request, settings: TravelerMemorySettings) -> None:
    if not guards.same_origin(request, settings.public_origin):
        raise HTTPException(403, "Solicitud rechazada: solo se aceptan cambios desde Ya Sale.")


@router.get("/preferences")
async def get_preferences(request: Request, response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    feature = _feature(request)
    if feature is None:
        return {"enabled": False, "preferences": None}
    store, settings = feature
    subject = subject_of(request.cookies.get(COOKIE_NAME), settings.cookie_secret)
    if subject is None:
        return _body(None)
    try:
        return _body(await store.load(subject))
    except PreferencesUnavailable as exc:
        logger.warning("loading traveler preferences failed: %s", exc)
        raise HTTPException(503, "No pudimos leer tus preferencias guardadas. Tu viaje se muestra igual.") from None


@router.put("/preferences")
async def save_preferences(body: PreferencesRequest, request: Request, response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    store, settings = _enabled_or_404(request)
    _same_origin_or_403(request, settings)
    services = request.app.state.services
    if not await services.limiter.allow(guards.fingerprint(request, request.app.state.settings.fingerprint_salt)):
        raise HTTPException(429, "Demasiadas consultas seguidas. Espera un minuto.")
    cookie = request.cookies.get(COOKIE_NAME)
    subject = subject_of(cookie, settings.cookie_secret)
    if subject is None:
        cookie = new_cookie(settings.cookie_secret)
        subject = subject_of(cookie, settings.cookie_secret)
    response.set_cookie(
        COOKIE_NAME, cookie, max_age=COOKIE_MAX_AGE_S, path="/", secure=True, httponly=True, samesite="lax"
    )
    preferences = TravelerPreferences(body.schedule, body.cheapest)
    try:
        await store.save(subject, preferences)
    except PreferencesUnavailable as exc:
        logger.warning("saving traveler preferences failed: %s", exc)
        raise HTTPException(503, "No pudimos confirmar tus preferencias guardadas. Inténtalo de nuevo.",
                            headers={"Set-Cookie": response.headers["set-cookie"], "Cache-Control": "no-store"}) from None
    return _body(preferences)


@router.delete("/preferences")
async def clear_preferences(request: Request, response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    store, settings = _enabled_or_404(request)
    _same_origin_or_403(request, settings)
    subject = subject_of(request.cookies.get(COOKIE_NAME), settings.cookie_secret)
    if subject is not None:
        try:
            await store.clear(subject)
        except PreferencesUnavailable as exc:
            # The cookie stays, so the traveler can retry and reach the same record.
            logger.warning("clearing traveler preferences failed: %s", exc)
            raise HTTPException(503, "No se pudieron borrar tus preferencias. Inténtalo de nuevo.") from None
    response.delete_cookie(COOKIE_NAME, path="/", secure=True, httponly=True, samesite="lax")
    return _body(None)
