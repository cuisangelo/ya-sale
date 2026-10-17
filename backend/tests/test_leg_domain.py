from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from app.legs.domain import (
    LegData, LegOption, LegVersion, completeness, distinct_options, display_version, has_price, is_new_version, leg_status, material_change, normalize_place,
)

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


def test_display_version_prefers_confirmed_over_equivalent_newer():
    versions = [version(confirmations=1, price=(10, 15)), version(confirmations=0, price=(12, 14), version_id=2)]
    assert display_version(versions).id == 1


def test_display_version_shows_newest_when_disputed():
    versions = [version(confirmations=1, price=(10, 15)), version(confirmations=0, price=(30, 40), version_id=2)]
    assert display_version(versions).id == 2


def test_normalize_place():
    assert normalize_place("  Aguas  Calientes ") == normalize_place("aguas calientes")
    assert normalize_place("Ñaña") == "nana"


def test_a_price_on_either_bound_counts_as_priced():
    assert has_price(replace(data(), price_min_pen=Decimal("35")))
    assert not has_price(data(duration=90, point="Terminal"))


def test_a_priced_leg_ranks_above_an_unpriced_one_with_more_fields():
    assert completeness(data(price=(10, 15))) > completeness(data(duration=90, point="Terminal"))


def test_among_priced_legs_more_filled_fields_rank_higher():
    assert completeness(data(price=(10, 15), duration=90)) > completeness(data(price=(10, 15)))


def test_a_price_found_for_an_unpriced_leg_is_a_new_version():
    assert is_new_version(data(duration=90), data(price=(10, 15), duration=90))


def test_losing_the_price_is_not_a_new_version():
    assert not is_new_version(data(price=(10, 15), duration=90), data(duration=90))


def option(price=None, source="https://a.pe") -> LegOption:
    return LegOption(data(price=price), source, T0)


def test_options_drop_exact_duplicates_and_put_the_cheapest_priced_first():
    found = [option(), option(price=(30, 35)), option(price=(12, 15)), option(price=(30, 35))]
    assert [o.data.price_min_pen for o in distinct_options(found)] == [Decimal(12), Decimal(30), None]


def test_the_same_offer_from_two_sources_stays_twice():
    assert len(distinct_options([option(price=(10, 10)), option(price=(10, 10), source="https://b.pe")])) == 2


def test_options_are_capped():
    found = [option(price=(p, p)) for p in range(1, 30)]
    assert len(distinct_options(found)) == 10
