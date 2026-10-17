from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SearchHit:
    url: str
    title: str
    content: str


class Connector(Protocol):
    async def search(self, query: str, max_results: int) -> list[SearchHit]: ...
