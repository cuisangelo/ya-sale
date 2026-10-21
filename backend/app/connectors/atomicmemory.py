import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from urllib.parse import quote
from typing import Literal

import httpx
from pydantic import BaseModel, ValidationError

from app.travelers.domain import PreferencesUnavailable, TravelerPreferences, memory_text, parse_memory_text

SOURCE_SITE = "ya-sale"
# Far above the one record a traveler keeps; leftovers from an interrupted save still fit in one page.
LIST_LIMIT = 100


class _Memory(BaseModel):
    id: str
    content: str
    created_at: datetime


class _MemoryList(BaseModel):
    memories: list[_Memory]


class _IngestResult(BaseModel):
    stored_memory_ids: list[str]
    updated_memory_ids: list[str]


class _DeleteResult(BaseModel):
    success: Literal[True]


class AtomicMemoryPreferenceStore:
    """Traveler preferences in Atomic Memory, one verbatim record per traveler.

    Only `user_id` scopes a call: it is the server-derived subject, and no thread, agent or
    workspace is sent, so a record is never shared between travelers.
    """

    def __init__(self, client: httpx.AsyncClient, timeout_s: float):
        self._client = client
        self._timeout_s = timeout_s

    async def load(self, subject: str) -> TravelerPreferences | None:
        async with self._bounded():
            memories = await self._list(subject)
        for memory in sorted(memories, key=lambda m: m.created_at, reverse=True):
            preferences = parse_memory_text(memory.content)
            if preferences is not None:
                return preferences
        return None

    async def save(self, subject: str, preferences: TravelerPreferences) -> None:
        async with self._bounded():
            previous = await self._list(subject)
            same = next((m for m in previous if parse_memory_text(m.content) == preferences), None)
            if same is not None:
                # A verbatim re-ingest of identical text may be skipped, so the record is reused instead.
                keep = {same.id}
            else:
                # Writing before deleting means a failed cleanup still leaves the newest choice readable.
                ingested = await self._ingest(subject, memory_text(preferences))
                keep = set(ingested.stored_memory_ids) | set(ingested.updated_memory_ids)
                if not keep or any(not value.strip() for value in keep):
                    raise PreferencesUnavailable("ingest stored no memory")
            for memory in previous:
                if memory.id not in keep:
                    await self._delete(subject, memory.id)

    async def clear(self, subject: str) -> None:
        async with self._bounded():
            for _ in range(4):
                memories = await self._list(subject)
                if not memories:
                    return
                for memory in memories:
                    await self._delete(subject, memory.id)
            if await self._list(subject):
                raise PreferencesUnavailable("memories remain after cleanup")

    @asynccontextmanager
    async def _bounded(self):
        try:
            async with asyncio.timeout(self._timeout_s):
                yield
        except TimeoutError:
            raise PreferencesUnavailable("timed out") from None

    async def _list(self, subject: str) -> list[_Memory]:
        params = {"user_id": subject, "source_site": SOURCE_SITE, "limit": str(LIST_LIMIT)}
        body = await self._call("GET", "/v1/memories/list", params=params)
        return self._parse(_MemoryList, body).memories

    async def _ingest(self, subject: str, text: str) -> _IngestResult:
        payload = {
            "user_id": subject,
            "conversation": text,
            "source_site": SOURCE_SITE,
            "skip_extraction": True,
            "content_class": "summary",
            "metadata": {"externalId": "traveler-preferences"},
        }
        return self._parse(_IngestResult, await self._call("POST", "/v1/memories/ingest/quick", json=payload))

    async def _delete(self, subject: str, memory_id: str) -> None:
        body = await self._call("DELETE", f"/v1/memories/{quote(memory_id, safe='')}", params={"user_id": subject})
        self._parse(_DeleteResult, body)

    async def _call(self, method: str, path: str, **kwargs) -> object:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise PreferencesUnavailable(type(exc).__name__) from None
        if response.status_code not in (200, 201):
            raise PreferencesUnavailable(f"{method} {path} HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError:
            raise PreferencesUnavailable(f"{method} {path} returned invalid JSON") from None

    @staticmethod
    def _parse[T: BaseModel](model: type[T], body: object) -> T:
        try:
            return model.model_validate(body)
        except ValidationError:
            raise PreferencesUnavailable(f"unexpected {model.__name__} response") from None


def atomicmemory_client(api_url: str, api_key: str, timeout_s: float) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=api_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=timeout_s, follow_redirects=False)
