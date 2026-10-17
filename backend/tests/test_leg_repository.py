from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.legs.domain import LegData, LegKey, leg_status
from app.legs.repository import AlreadyConfirmed, LegRepository

KEY = LegKey.of("Tarapoto", "Sauce", "colectivo")
T0 = datetime(2026, 10, 17, 12, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)


def data(price=(10, 15), point="Banda de Shilcayo") -> LegData:
    return LegData(
        departure_point=point,
        operator=None,
        price_min_pen=Decimal(price[0]),
        price_max_pen=Decimal(price[1]),
        duration_min=110,
        schedule_note=None,
        purchase_url=None,
    )


@pytest.fixture
def repo(pool):
    return LegRepository(pool)


async def test_same_data_does_not_create_new_version(repo):
    v1 = await repo.record_version(KEY, data(price=(10, 15)), "https://a.pe", T0)
    v2 = await repo.record_version(KEY, data(price=(12, 14)), "https://b.pe", T1)
    assert v2.id == v1.id
    assert v2.fetched_at == T1


async def test_confirmed_version_is_never_overwritten(repo):
    v1 = await repo.record_version(KEY, data(price=(10, 15)), "https://a.pe", T0)
    await repo.confirm(v1.id, "fp1", "Ana")
    await repo.record_version(KEY, data(price=(30, 40)), "https://b.pe", T1)
    versions = await repo.versions(KEY)
    assert [v.confirmations for v in versions] == [1, 0]
    assert versions[0].data.price_min_pen == Decimal("10")
    assert versions[0].source_url == "https://a.pe"
    assert leg_status(versions) == "disputed"


async def test_same_fingerprint_cannot_confirm_twice(repo):
    v1 = await repo.record_version(KEY, data(), "https://a.pe", T0)
    await repo.confirm(v1.id, "fp1", None)
    with pytest.raises(AlreadyConfirmed):
        await repo.confirm(v1.id, "fp1", None)


async def test_correction_creates_confirmed_version(repo):
    await repo.record_version(KEY, data(price=(10, 15)), "https://a.pe", T0)
    leg_id = await repo.leg_id_of(KEY)
    v2 = await repo.correct(leg_id, data(price=(20, 22)), "fp2", "Luis")
    assert v2.confirmations == 1
    assert v2.source_url == "ya-sale:confirmation"


async def test_get_returns_key_and_versions(repo):
    await repo.record_version(KEY, data(), "https://a.pe", T0)
    leg_id = await repo.leg_id_of(KEY)
    key, versions = await repo.get(leg_id)
    assert key == KEY
    assert len(versions) == 1


async def test_versions_of_unknown_leg_is_empty(repo):
    assert await repo.versions(LegKey.of("Nowhere", "Else", "bus")) == []
