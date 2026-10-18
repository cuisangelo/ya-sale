from dataclasses import dataclass
from typing import Protocol

from app.reader.domain import Query, Recipe, fill


class ReplayScreen(Protocol):
    url: str

    async def open(self, url: str) -> None: ...
    async def settle(self) -> None: ...
    async def click(self, x: int, y: int, count: int = 1) -> None: ...
    async def click_selector(self, selector: str) -> bool: ...
    async def click_label(self, label: str) -> bool: ...
    async def type(self, text: str) -> None: ...
    async def key(self, combo: str, repeat: int = 1) -> None: ...
    async def scroll(self, direction: str, amount: int, x: int | None, y: int | None) -> None: ...
    async def text(self) -> str: ...


@dataclass(frozen=True)
class Rendered:
    url: str
    text: str


async def replay(screen: ReplayScreen, recipe: Recipe, query: Query) -> Rendered:
    """Plays a recipe with plain browser input, no model per click, and returns the page it lands on."""
    if recipe.url_template is not None:
        url = fill(recipe.url_template, query)
        await screen.open(url)
        # Some sites only prefill their search from the URL; pressing the same search button shows the list.
        if recipe.submit_label is not None and await screen.click_label(recipe.submit_label):
            await screen.settle()
        return Rendered(url, await screen.text())
    await screen.open(recipe.start_url)
    for step in recipe.steps:
        match step.kind:
            case "click":
                if step.selector is None or not await screen.click_selector(step.selector):
                    await screen.click(step.x, step.y)
            case "type":
                await screen.type(fill(step.text, query))
            case "key":
                await screen.key(step.text)
            case "scroll":
                direction, amount = step.text.split(":")
                await screen.scroll(direction, int(amount), step.x, step.y)
        await screen.settle()
    return Rendered(screen.url, await screen.text())
