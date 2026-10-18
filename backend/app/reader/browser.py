from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from playwright.async_api import Browser, Page, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeout

BOT_ID = "YaSaleBot/0.1 (+https://yasale.cuisangelo.com)"
WIDTH, HEIGHT = 1280, 800
NAVIGATION_TIMEOUT_MS = 45_000
SETTLE_MS = 2_500
# xdotool key names, which the computer toolset speaks, mapped to Playwright's.
_KEYS = {
    "return": "Enter", "enter": "Enter", "backspace": "Backspace", "escape": "Escape", "esc": "Escape",
    "tab": "Tab", "space": " ", "delete": "Delete", "home": "Home", "end": "End",
    "page_down": "PageDown", "page_up": "PageUp", "pagedown": "PageDown", "pageup": "PageUp",
    "down": "ArrowDown", "up": "ArrowUp", "left": "ArrowLeft", "right": "ArrowRight",
    "ctrl": "Control", "control": "Control", "alt": "Alt", "shift": "Shift", "super": "Meta", "cmd": "Meta",
}
# Climbs to the control a visitor meant to hit and names it by a CSS path, so a replay can hit it again.
_ELEMENT_AT = """([x, y]) => {
  let el = document.elementFromPoint(x, y);
  if (!el) return null;
  const hit = el.closest('a,button,input,select,textarea,label,li,[role=option],[role=button],td') || el;
  const path = [];
  for (let node = hit; node && node.nodeType === 1 && node !== document.body; node = node.parentElement) {
    if (node.id && /^[A-Za-z][\\w-]*$/.test(node.id) && document.querySelectorAll('#' + node.id).length === 1) {
      path.unshift('#' + node.id); break;
    }
    const same = Array.from(node.parentElement ? node.parentElement.children : []).filter(c => c.tagName === node.tagName);
    path.unshift(node.tagName.toLowerCase() + (same.length > 1 ? `:nth-of-type(${same.indexOf(node) + 1})` : ''));
  }
  return {selector: path.join(' > '), label: (hit.innerText || hit.value || '').trim().slice(0, 80)};
}"""


def playwright_key(combo: str) -> str:
    return "+".join(_KEYS.get(part.lower(), part) for part in combo.split("+"))


class Screen:
    """One browser tab seen as a screen: the computer toolset's actions mapped onto Playwright input."""

    def __init__(self, page: Page):
        self._page = page

    @property
    def url(self) -> str:
        return self._page.url

    async def open(self, url: str) -> None:
        await self._page.goto(url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
        await self.settle()

    async def settle(self) -> None:
        try:
            await self._page.wait_for_load_state("networkidle", timeout=SETTLE_MS * 4)
        except PlaywrightTimeout:
            pass  # Sites that poll forever never go idle; the fixed pause below still lets them render.
        await self._page.wait_for_timeout(SETTLE_MS)

    async def screenshot(self) -> bytes:
        return await self._page.screenshot(type="png")

    async def element_at(self, x: int, y: int) -> tuple[str | None, str | None]:
        found = await self._page.evaluate(_ELEMENT_AT, [x, y])
        return (found["selector"], found["label"] or None) if found else (None, None)

    async def click(self, x: int, y: int, count: int = 1) -> None:
        await self._page.mouse.click(x, y, click_count=count)

    async def click_selector(self, selector: str) -> bool:
        target = self._page.locator(selector)
        if await target.count() != 1:
            return False
        try:
            await target.click(timeout=5_000)
        except PlaywrightTimeout:
            return False  # Present but hidden or covered: the recorded point is the better bet.
        return True

    async def click_label(self, label: str) -> bool:
        """Presses the one visible button with exactly this label; anything ambiguous is left alone."""
        target = self._page.get_by_role("button", name=label, exact=True)
        if await target.count() != 1 or not await target.is_visible():
            return False
        await target.click(timeout=5_000)
        return True

    async def move(self, x: int, y: int) -> None:
        await self._page.mouse.move(x, y)

    async def type(self, text: str) -> None:
        await self._page.keyboard.type(text, delay=60)

    async def key(self, combo: str, repeat: int = 1) -> None:
        for _ in range(repeat):
            await self._page.keyboard.press(playwright_key(combo))

    async def scroll(self, direction: str, amount: int, x: int | None, y: int | None) -> None:
        if x is not None and y is not None:
            await self._page.mouse.move(x, y)
        dx, dy = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}[direction]
        await self._page.mouse.wheel(dx * 100 * amount, dy * 100 * amount)

    async def wait(self, seconds: float) -> None:
        await self._page.wait_for_timeout(int(seconds * 1000))

    async def text(self) -> str:
        return await self._page.evaluate("() => document.body ? document.body.innerText : ''")


class VisitorBrowser:
    """Opens a fresh visitor per tab: no cookies or storage carried from one search to the next."""

    def __init__(self, browser: Browser):
        self._browser = browser
        # The real Chromium version plus who we are and how to reach us: honest and identifiable.
        self.user_agent = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{browser.version} Safari/537.36 {BOT_ID}"
        )

    @asynccontextmanager
    async def tab(self) -> AsyncIterator[Screen]:
        context = await self._browser.new_context(
            user_agent=self.user_agent,
            viewport={"width": WIDTH, "height": HEIGHT},
            locale="es-PE",
            timezone_id="America/Lima",
        )
        try:
            yield Screen(await context.new_page())
        finally:
            await context.close()


@asynccontextmanager
async def chromium(headless: bool) -> AsyncIterator[VisitorBrowser]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        try:
            yield VisitorBrowser(browser)
        finally:
            await browser.close()
