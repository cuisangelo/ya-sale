import asyncio
import logging

from app.reader.domain import OperatorSite
from app.reader.repository import RequestQueue
from app.reader.service import ReaderService

logger = logging.getLogger(__name__)

IDLE_SECONDS = 3


async def drain_one(queue: RequestQueue, service: ReaderService, sites: dict[str, OperatorSite]) -> bool:
    claimed = await queue.claim()
    if claimed is None:
        return False
    domain, query = claimed
    try:
        await service.read(sites[domain], query)
    except Exception:
        # One operator failing must not stop the others; the request is dropped and the API asks again later.
        logger.exception("reader: reading %s %s %s failed", domain, query.route_key, query.travel_date)
    finally:
        await queue.done(domain, query)
    return True


async def run(queue: RequestQueue, service: ReaderService, sites: dict[str, OperatorSite]) -> None:
    logger.info("reader: worker started for %s", ", ".join(sorted(sites)))
    while True:
        if not await drain_one(queue, service, sites):
            await asyncio.sleep(IDLE_SECONDS)
