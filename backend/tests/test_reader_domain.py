from datetime import date
from decimal import Decimal

from app.reader.domain import ANY_ROUTE, Query, Step, fill, may_type, submit_label, url_template
from app.reader.extraction import DepartureOut, PageOut, to_departures

QUERY = Query("Lima", "Cajamarca", date(2026, 10, 20))
RESULTS = "https://www.turismodias.com.pe/es/pasajes-bus/lima/cajamarca?date_onward=20-10-2026"


def test_the_agent_may_type_only_the_trip():
    assert may_type("Lim", QUERY)
    assert may_type("cajamarca", QUERY)
    assert may_type("20/10/2026", QUERY)
    assert not may_type("juan.perez@gmail.com", QUERY)
    assert not may_type("Juan Pérez", QUERY)
    assert may_type("2026-10-20", QUERY)
    assert may_type("20", QUERY)
    assert not may_type("4111111111111111", QUERY)
    assert not may_type("45678912", QUERY)
    assert not may_type("   ", QUERY)


def test_a_results_url_carrying_route_and_date_serves_every_route():
    template, route = url_template(RESULTS, QUERY)
    assert template == "https://www.turismodias.com.pe/es/pasajes-bus/{origin_slug}/{destination_slug}?date_onward={date_dmy_dash}"
    assert route == ANY_ROUTE
    assert fill(template, Query("Chiclayo", "Jaén", date(2026, 11, 2))) == (
        "https://www.turismodias.com.pe/es/pasajes-bus/chiclayo/jaen?date_onward=02-11-2026"
    )


def test_a_results_url_with_route_ids_only_serves_its_own_route():
    template, route = url_template("https://bus.example/search?from=12&to=40&date=2026-10-20", QUERY)
    assert template == "https://bus.example/search?from=12&to=40&date={date}"
    assert route == "lima>cajamarca"


def test_a_results_url_without_the_date_is_not_a_template():
    assert url_template("https://bus.example/resultados", QUERY) is None


def test_the_search_button_is_kept_but_never_a_purchase_control():
    assert submit_label([Step("type", text="Lima"), Step("click", label=" Buscar ")]) == "Buscar"
    assert submit_label([Step("click", label="Comprar")]) is None
    assert submit_label([Step("click", label="Seleccionar asiento")]) is None
    assert submit_label([Step("type", text="Lima")]) is None


def _page(**overrides) -> PageOut:
    row = DepartureOut(service="Ejecutivo", departs="16:00", arrives="08:55", arrives_next_day=True, price_min_pen=70, seats_available=12)
    return PageOut(**{"page": "departures", "origin_shown": "Lima", "destination_shown": "Cajamarca", "date_shown": "2026-10-20", "departures": [row], **overrides})


def test_rows_become_departures_linked_to_the_results_page():
    [departure] = to_departures(_page(), "Turismo Días", "turismodias.com.pe", QUERY.travel_date, RESULTS)
    assert departure.operator == "Turismo Días · Ejecutivo"
    assert departure.departs_at.isoformat() == "2026-10-20T16:00:00-05:00"
    assert departure.arrives_at.isoformat() == "2026-10-21T08:55:00-05:00"
    assert departure.price_pen == Decimal("70")
    assert departure.booking_url == RESULTS


def test_a_page_for_another_day_yields_nothing():
    assert to_departures(_page(date_shown="2026-10-21"), "T", "t.pe", QUERY.travel_date, RESULTS) == ()


def test_impossible_values_are_dropped_not_guessed():
    row = DepartureOut(service=None, departs="16:00", arrives="15:00", arrives_next_day=False, price_min_pen=0, seats_available=-1)
    bad_time = DepartureOut(service=None, departs="soon", arrives=None, arrives_next_day=False, price_min_pen=50, seats_available=None)
    [departure] = to_departures(_page(departures=[row, bad_time]), "T", "t.pe", QUERY.travel_date, RESULTS)
    assert (departure.price_pen, departure.arrives_at, departure.seats_available) == (None, None, None)
