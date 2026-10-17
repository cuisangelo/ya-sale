from datetime import UTC, datetime
from decimal import Decimal

from app.legs.domain import LegData, LegVersion, leg_status, material_change, normalize_place

T0 = datetime(2026, 10, 17, tzinfo=UTC)


def data(price=None, duration=None, point=None) -> LegData:
    return LegData(
        departure_point=point,
        operator=None,
        price_min_pen=Decimal(price[0]) if price else None,
        price_max_pen=Decimal(price[1]) if price else None,
        duration_min=duration,
        schedule_note=None,
        purchase_url=None,
    )


def version(confirmations=0, price=None, duration=None, point=None, version_id=1) -> LegVersion:
    return LegVersion(
        id=version_id,
        data=data(price, duration, point),
        source_url="https://example.pe",
        fetched_at=T0,
        confirmations=confirmations,
    )


def test_overlapping_price_ranges_are_not_a_change():
    assert not material_change(data(price=(10, 15)), data(price=(12, 13)))


def test_disjoint_price_ranges_are_a_change():
    assert material_change(data(price=(10, 15)), data(price=(20, 25)))


def test_duration_within_25_percent_is_not_a_change():
    assert not material_change(data(duration=100), data(duration=120))
    assert material_change(data(duration=100), data(duration=130))


def test_different_departure_point_is_a_change():
    assert material_change(data(point="Banda de Shilcayo"), data(point="Cruce a Yurimaguas"))


def test_departure_point_compared_after_normalizing():
    assert not material_change(data(point="Banda de Shilcayo"), data(point="  banda de  shilcayo "))


def test_missing_field_on_one_side_is_not_a_change():
    assert not material_change(data(price=(10, 15)), data(duration=90))


def test_unconfirmed_is_extracted():
    assert leg_status([version(confirmations=0)]) == "extracted"


def test_confirmed_latest_is_confirmed():
    assert leg_status([version(confirmations=1)]) == "confirmed"


def test_newer_different_version_after_confirmed_is_disputed():
    versions = [version(confirmations=1, price=(10, 15)), version(confirmations=0, price=(30, 40), version_id=2)]
    assert leg_status(versions) == "disputed"


def test_newer_equivalent_version_keeps_confirmed():
    versions = [version(confirmations=1, price=(10, 15)), version(confirmations=0, price=(12, 14), version_id=2)]
    assert leg_status(versions) == "confirmed"


def test_normalize_place():
    assert normalize_place("  Aguas  Calientes ") == normalize_place("aguas calientes")
    assert normalize_place("Ñaña") == "nana"
