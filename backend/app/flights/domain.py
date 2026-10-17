from datetime import date
from urllib.parse import urlencode

from app.legs.domain import normalize_place

# Cities with scheduled passenger flights; a city missing here has no airport to look up.
AIRPORTS = {
    "lima": "LIM",
    "cusco": "CUZ",
    "cuzco": "CUZ",
    "arequipa": "AQP",
    "trujillo": "TRU",
    "piura": "PIU",
    "chiclayo": "CIX",
    "iquitos": "IQT",
    "tarapoto": "TPP",
    "juliaca": "JUL",
    "tacna": "TCQ",
    "puerto maldonado": "PEM",
    "pucallpa": "PCL",
    "cajamarca": "CJA",
    "tumbes": "TBP",
    "ayacucho": "AYP",
    "jauja": "JAU",
    "talara": "TYL",
    "chachapoyas": "CHH",
}

SKY = "H2"
STAR_PERU = "2I"


def airport_of(place: str) -> str | None:
    return AIRPORTS.get(normalize_place(place))


def booking_url(airline: str | None, origin: str, destination: str, day: date) -> str:
    """The airline's own search for that route and day, or Google Flights for an airline without one."""
    if airline == SKY:
        query = {
            "origin": origin,
            "destination": destination,
            "departureDate": day.isoformat(),
            "arrivalDate": day.isoformat(),
            "flightType": "OW",
            "ADT": 1,
        }
        return f"https://initial-sale.skyairline.com/es/peru?{urlencode(query)}"
    if airline == STAR_PERU:
        # Their form rejects a one-way search without a return day, so both carry the same date.
        query = {
            "tipo_viaje": "O",
            "origen": origin,
            "destino": destination,
            "from": day.strftime("%d/%m/%Y"),
            "to": day.strftime("%d/%m/%Y"),
            "cant_adultos": 1,
            "cant_ninos": 0,
            "cant_infantes": 0,
            "codigo_desc": "",
        }
        return f"https://www.starperu.com/Booking1?{urlencode(query)}"
    return f"https://www.google.com/travel/flights?{urlencode({'q': f'Flights from {origin} to {destination} on {day.isoformat()} one way'})}"
