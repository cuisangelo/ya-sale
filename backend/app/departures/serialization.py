from app.departures.domain import Departure


def departure_json(departure: Departure) -> dict:
    return {
        "operator": departure.operator,
        "departs_at": departure.departs_at.isoformat(),
        "arrives_at": departure.arrives_at.isoformat() if departure.arrives_at else None,
        "price_pen": str(departure.price_pen) if departure.price_pen is not None else None,
        "seats_available": departure.seats_available,
        "booking_url": departure.booking_url,
        "seller": departure.seller,
    }
