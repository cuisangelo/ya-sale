from dataclasses import dataclass
from decimal import Decimal

# claude-sonnet-5-5 list prices per million tokens; cache writes cost 1.25x input.
_INPUT, _OUTPUT, _CACHE_READ, _CACHE_WRITE = Decimal("2"), Decimal("10"), Decimal("0.20"), Decimal("2.50")


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    calls: int = 0

    @classmethod
    def of(cls, usage) -> "Usage":
        return cls(
            usage.input_tokens,
            usage.output_tokens,
            usage.cache_read_input_tokens or 0,
            usage.cache_creation_input_tokens or 0,
            1,
        )

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
            self.cache_read_tokens + other.cache_read_tokens,
            self.cache_write_tokens + other.cache_write_tokens,
            self.calls + other.calls,
        )

    @property
    def cost_usd(self) -> Decimal:
        tokens = (
            self.input_tokens * _INPUT
            + self.output_tokens * _OUTPUT
            + self.cache_read_tokens * _CACHE_READ
            + self.cache_write_tokens * _CACHE_WRITE
        )
        return (tokens / 1_000_000).quantize(Decimal("0.0001"))
