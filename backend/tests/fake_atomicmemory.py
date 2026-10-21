"""Test fixture, not Atomic Memory: an in-memory stand-in for the four documented Core routes the
preference store calls (list, ingest/quick, delete), keyed strictly by `user_id`."""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

API_KEY = "fixture-key"


@dataclass
class FakeAtomicMemory:
    records: dict[str, list[dict]] = field(default_factory=dict)
    requests: list[dict] = field(default_factory=list)
    fail_status: int | None = None
    delay_s: float = 0.0
    malformed_ingest: bool = False
    malformed_delete: bool = False
    ingest_status: int = 200

    def contents(self, user_id: str) -> list[str]:
        return [record["content"] for record in self.records.get(user_id, [])]


def build_fake_app(state: FakeAtomicMemory) -> FastAPI:
    app = FastAPI(title="Atomic Memory fixture")

    async def guard(request: Request, authorization: str | None) -> None:
        state.requests.append({"method": request.method, "path": request.url.path, "params": dict(request.query_params)})
        if state.delay_s:
            await asyncio.sleep(state.delay_s)
        if authorization != f"Bearer {API_KEY}":
            raise HTTPException(401, "unauthorized")
        if state.fail_status:
            raise HTTPException(state.fail_status, "fixture failure")

    @app.get("/v1/memories/list")
    async def list_memories(request: Request, user_id: str, source_site: str | None = None, authorization: str | None = Header(None)):
        await guard(request, authorization)
        memories = [m for m in state.records.get(user_id, []) if source_site in (None, m["source_site"])]
        return {"memories": memories, "count": len(memories)}

    @app.post("/v1/memories/ingest/quick")
    async def ingest_quick(request: Request, authorization: str | None = Header(None)):
        await guard(request, authorization)
        body = await request.json()
        state.requests[-1]["json"] = body
        if state.malformed_ingest:
            return {}
        user = state.records.setdefault(body["user_id"], [])
        external_id = body.get("metadata", {}).get("externalId")
        existing = next((m for m in user if external_id and m.get("external_id") == external_id), None)
        if existing:
            existing["content"] = body["conversation"]
            return JSONResponse({"stored_memory_ids": [], "updated_memory_ids": [existing["id"]]}, status_code=state.ingest_status)
        if any(m["content"] == body["conversation"] for m in user):
            stored = []
        else:
            record = {
                "id": str(uuid.uuid4()),
                "external_id": external_id,
                "user_id": body["user_id"],
                "content": body["conversation"],
                "source_site": body["source_site"],
                "created_at": datetime.now(UTC).isoformat(),
            }
            user.append(record)
            stored = [record["id"]]
        return {
            "episode_id": str(uuid.uuid4()),
            "facts_extracted": 0,
            "memories_stored": len(stored),
            "memories_updated": 0,
            "memories_deleted": 0,
            "memories_skipped": 1 - len(stored),
            "stored_memory_ids": stored,
            "updated_memory_ids": [],
            "links_created": 0,
            "composites_created": 0,
        }

    @app.delete("/v1/memories/{memory_id}")
    async def delete_memory(memory_id: str, request: Request, user_id: str, authorization: str | None = Header(None)):
        await guard(request, authorization)
        if state.malformed_delete:
            return {}
        user = state.records.get(user_id, [])
        if not any(m["id"] == memory_id for m in user):
            raise HTTPException(404, "Memory not found")
        state.records[user_id] = [m for m in user if m["id"] != memory_id]
        return {"success": True}

    return app
