from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone

from app.departures.domain import Departure
from app.legs.domain import Mode
from app.reader.domain import OperatorSite, Query
from app.reader.repository import RequestQueue, ResultRepository

FRESH_FOR = timedelta(minutes=15)


class BrowserOperatorSource:
    """Any registered operator's departures as the browser reader last saw them; never waits for a browser.

    On a miss it queues the search for the reader worker and returns nothing, so a later refresh shows the result.
    """

    mode: Mode = "bus"

    def __init__(
        self,
        site: OperatorSite,
        results: ResultRepository,
        queue: RequestQueue,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        self.seller = site.domain
        self._site = site
        self._results = results
        self._queue = queue
        self._clock = clock

    async def departures(self, origin: str, destination: str, travel_date: date) -> list[Departure]:
        query = Query(origin, destination, travel_date)
        if not self._site.covers(query):
            return []
        found = await self._results.fresh(self._site.domain, query, self._clock() - FRESH_FOR)
        if found is None:
            await self._queue.enqueue(self._site.domain, query)
            return []
        return list(found)
