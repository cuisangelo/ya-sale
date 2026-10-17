import json
from dataclasses import dataclass

import anthropic

from app.legs.serialization import leg_summary_json
from app.trips.events import LegRefreshed, LegStored

MODEL = "claude-opus-5-5"
MAX_TOOL_ROUNDS = 3

_SYSTEM = "Eres un asistente de viajes en el Perú. Responde en español, breve y concreto."

PLAN_TRIP_TOOL = {
    "name": "plan_trip",
    "description": (
        "Arma un viaje en el Perú de un origen a un destino, tramo por tramo y en cualquier medio de "
        "transporte. Devuelve cada tramo con precio, duración, paradero, la fuente del dato, la fecha "
        "de consulta y si alguien que hace la ruta lo confirmó."
    ),
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "origin": {"type": "string", "description": "Ciudad o lugar de salida."},
            "destination": {"type": "string", "description": "Ciudad, pueblo o lugar de llegada."},
            "date": {"type": "string", "description": "Fecha de salida, YYYY-MM-DD."},
        },
        "required": ["origin", "destination", "date"],
        "additionalProperties": False,
    },
}


@dataclass(frozen=True)
class Answer:
    text: str
    sources: int
    dated: int
    confirmed: int


@dataclass(frozen=True)
class CompareResult:
    plain: Answer
    with_tools: Answer
    legs: list[dict]


def _text_of(response) -> str:
    return "".join(block.text for block in response.content if block.type == "text").strip()


class CompareService:
    def __init__(self, client: anthropic.AsyncAnthropic, planner):
        self._client = client
        self._planner = planner

    async def _ask(self, messages: list, tools: list | None = None):
        kwargs = {"model": MODEL, "max_tokens": 4000, "system": _SYSTEM, "output_config": {"effort": "low"}, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        return await self._client.messages.create(**kwargs)

    async def _plan_trip(self, origin: str, destination: str, date: str) -> list[dict]:
        latest: dict[tuple[int, str], dict] = {}
        async for event in self._planner.plan(origin, destination, date, trip_id=0):
            if isinstance(event, (LegStored, LegRefreshed)):
                latest[(event.index, event.mode)] = leg_summary_json(event.leg_id, event.mode, event.origin, event.destination, event.status, event.version)
        return [latest[i] for i in sorted(latest)]

    async def _with_tools(self, question: str) -> tuple[str, list[dict]]:
        messages = [{"role": "user", "content": question}]
        legs: list[dict] = []
        response = await self._ask(messages, [PLAN_TRIP_TOOL])
        for _ in range(MAX_TOOL_ROUNDS):
            if response.stop_reason != "tool_use":
                break
            results = []
            for block in response.content:
                if block.type == "tool_use" and block.name == "plan_trip":
                    trip_legs = await self._plan_trip(**block.input)
                    legs.extend(trip_legs)
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(trip_legs, ensure_ascii=False)})
            messages = [*messages, {"role": "assistant", "content": response.content}, {"role": "user", "content": results}]
            response = await self._ask(messages, [PLAN_TRIP_TOOL])
        return _text_of(response), legs

    async def compare(self, question: str) -> CompareResult:
        plain_text = _text_of(await self._ask([{"role": "user", "content": question}]))
        tools_text, legs = await self._with_tools(question)
        with_tools = Answer(
            text=tools_text,
            sources=sum(1 for leg in legs if leg["version"]["source_url"]),
            dated=sum(1 for leg in legs if leg["version"]["fetched_at"]),
            confirmed=sum(1 for leg in legs if leg["status"] == "confirmed"),
        )
        return CompareResult(plain=Answer(plain_text, 0, 0, 0), with_tools=with_tools, legs=legs)
