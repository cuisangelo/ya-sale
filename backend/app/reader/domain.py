import re
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Literal

from app.legs.domain import normalize_place

ANY_ROUTE = "*"
RecipeStatus = Literal["ready", "blocked"]
StepKind = Literal["click", "type", "key", "scroll", "wait"]
# A day, a year or a full date; never a long run of digits such as a document or card number.
_DATE_TEXT = re.compile(r"^(\d{1,2}|\d{4})([/.\-]\d{1,2}([/.\-]\d{2,4})?)?$")
# Words on controls that lead toward buying; a replay never presses a control labelled with one.
_PURCHASE_WORDS = ("compra", "comprar", "pagar", "pago", "asiento", "reserva", "continuar", "seleccionar", "login", "sesion")


@dataclass(frozen=True)
class Query:
    origin: str
    destination: str
    travel_date: date

    @property
    def route_key(self) -> str:
        return f"{normalize_place(self.origin)}>{normalize_place(self.destination)}"

    def values(self) -> dict[str, str]:
        """Every way a site may spell this query, in the order templatize tries them."""
        d = self.travel_date
        return {
            "date_dmy": d.strftime("%d/%m/%Y"),
            "date_dmy_dash": d.strftime("%d-%m-%Y"),
            "date": d.isoformat(),
            "origin_slug": _slug(self.origin),
            "destination_slug": _slug(self.destination),
            "origin": self.origin,
            "destination": self.destination,
        }


@dataclass(frozen=True)
class Step:
    """One recorded visitor action. A click keeps both a CSS path and the point, so a moved layout can still be hit."""

    kind: StepKind
    selector: str | None = None
    x: int | None = None
    y: int | None = None
    text: str | None = None
    label: str | None = None


@dataclass(frozen=True)
class OperatorSite:
    """A bus company whose terms and robots.txt were read and allow a visitor-paced read of its public search."""

    domain: str
    name: str
    start_url: str
    serves: frozenset[str]
    compliance_note: str

    def covers(self, query: Query) -> bool:
        return normalize_place(query.origin) in self.serves and normalize_place(query.destination) in self.serves


@dataclass(frozen=True)
class Recipe:
    domain: str
    route_key: str
    start_url: str
    status: RecipeStatus
    note: str
    url_template: str | None = None
    submit_label: str | None = None
    steps: tuple[Step, ...] = field(default_factory=tuple)


def may_type(text: str, query: Query) -> bool:
    """The agent may only type the trip itself, so it can never enter a name, an email or a card."""
    typed = normalize_place(text)
    if not typed.strip():
        return False
    if _DATE_TEXT.match(text.strip()):
        return True
    return any(typed in normalize_place(place) for place in (query.origin, query.destination))


def submit_label(steps: list[Step]) -> str | None:
    """The label of the last control clicked before the results showed: the search button a replay presses again."""
    clicks = [step for step in steps if step.kind == "click"]
    if not clicks or not clicks[-1].label:
        return None
    label = clicks[-1].label.strip()
    if len(label) > 30 or any(word in normalize_place(label) for word in _PURCHASE_WORDS):
        return None
    return label


def templatize(text: str, query: Query) -> str:
    # A slug only matches in its exact case, so a URL that says "Lima" keeps its capital on replay.
    for name, value in query.values().items():
        text = _replace(text, value, "{" + name + "}", ignore_case=not name.endswith("_slug"))
    return text


def fill(template: str, query: Query) -> str:
    values = query.values()
    return re.sub(r"\{(\w+)\}", lambda m: values[m.group(1)], template)


def url_template(results_url: str, query: Query) -> tuple[str, str] | None:
    """The results URL as a template and the routes it serves, or None when the URL doesn't carry the date."""
    template = templatize(results_url, query)
    if "{date" not in template:
        return None
    serves_any_route = ("{origin" in template) and ("{destination" in template)
    return template, ANY_ROUTE if serves_any_route else query.route_key


def recorded_steps(steps: list[Step], query: Query) -> tuple[Step, ...]:
    return tuple(replace(s, text=templatize(s.text, query)) if s.kind == "type" and s.text else s for s in steps)


def _slug(place: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalize_place(place)).strip("-")


def _replace(text: str, value: str, placeholder: str, ignore_case: bool) -> str:
    if not value:
        return text
    return re.sub(re.escape(value), placeholder, text, flags=re.IGNORECASE if ignore_case else 0)
