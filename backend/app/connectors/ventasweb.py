import re
from collections.abc import Callable
from datetime import date, datetime, timedelta
from decimal import Decimal

import httpx
from pydantic import BaseModel

from app.departures.domain import LIMA, Departure
from app.legs.domain import Mode, normalize_place

_DISTRICT = re.compile(r"\s*\(.*\)$")


class VentasWebSearchFailed(RuntimeError):
    pass


class _Office(BaseModel):
    codigo: int
    descripcion: str  # "TARAPOTO (MORALES)"


class _Trip(BaseModel):
    fechaViaje: str  # "20/10/2026"
    horaPartida: str  # "03:00PM"
    duracion_Viaje: str  # "15:00", or "00:00" when the operator leaves it out
    nomServicio: str
    precio_N1: Decimal
    precio_N2: Decimal
    asientosDisponibles: int


class _Search(BaseModel):
    datos: list[_Trip]
    success: bool
    message: str


class VentasWebSource:
    """The "Sistema de Ventas Web" that GH Bus and Flores run on their sales sites. A search runs in the session its
    route-and-date page opens, so that page is the link."""

    mode: Mode = "bus"

    def __init__(self, site_url: str, seller: str, brand: str, new_session: Callable[[], httpx.AsyncClient]):
        self.seller = seller
        self._site_url = site_url
        self._brand = brand
        self._new_session = new_session
        self._offices: dict[str, int] | None = None

    async def departures(self, origin: str, destination: str, travel_date: date) -> list[Departure]:
        async with self._new_session() as session:
            if self._offices is None:
                self._offices = await self._fetch_offices(session)
            origin_code = self._offices.get(normalize_place(origin))
            destination_code = self._offices.get(normalize_place(destination))
            if origin_code is None or destination_code is None:
                return []
            day = travel_date.strftime("%d/%m/%Y")
            day_page = f"{self._site_url}/?idorigen={origin_code}&iddestino={destination_code}&fechaida={day}"
            (await session.get(day_page)).raise_for_status()
            body = {"CodiOrigen": origin_code, "CodiDestino": destination_code, "FechaViaje": day, "SoloProgramados": False}
            response = await session.post(f"{self._site_url}/busqueda-turnos", json=body)
            response.raise_for_status()
        search = _Search.model_validate(response.json())
        if not search.success:
            raise VentasWebSearchFailed(f"{self.seller}: {search.message}")
        return [self._departure(trip, day_page) for trip in search.datos if trip.fechaViaje == day]

    async def _fetch_offices(self, session: httpx.AsyncClient) -> dict[str, int]:
        response = await session.get(f"{self._site_url}/api/base/lista-oficinas")
        response.raise_for_status()
        offices = [_Office.model_validate(o) for o in response.json()["datos"]]
        return {normalize_place(_DISTRICT.sub("", o.descripcion)): o.codigo for o in offices}

    def _departure(self, trip: _Trip, day_page: str) -> Departure:
        departs_at = datetime.strptime(f"{trip.fechaViaje} {trip.horaPartida}", "%d/%m/%Y %I:%M%p").replace(tzinfo=LIMA)
        hours, minutes = map(int, trip.duracion_Viaje.split(":"))
        # A floor priced at 0 is sold out or missing on that bus, not free.
        prices = [p for p in (trip.precio_N1, trip.precio_N2) if p > 0]
        return Departure(
            operator=f"{self._brand} · {trip.nomServicio}",
            departs_at=departs_at,
            # Without a duration their arrival just repeats the departure clock, so it says nothing.
            arrives_at=departs_at + timedelta(hours=hours, minutes=minutes) if hours or minutes else None,
            price_pen=min(prices, default=None),
            seats_available=trip.asientosDisponibles,
            booking_url=day_page,
            seller=self.seller,
        )
