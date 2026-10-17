import asyncio

from app.api.guards import RateLimiter


async def test_the_limit_holds_across_instances_sharing_the_database(pool):
    first, second = RateLimiter(pool, per_minute=6), RateLimiter(pool, per_minute=6)
    allowed = [await (first if i % 2 else second).allow("fp") for i in range(7)]
    assert allowed == [True] * 6 + [False]


async def test_a_concurrent_burst_lets_exactly_the_limit_through(pool):
    limiters = [RateLimiter(pool, per_minute=6) for _ in range(3)]
    allowed = await asyncio.gather(*(limiters[i % 3].allow("fp") for i in range(30)))
    assert sum(allowed) == 6


async def test_hits_older_than_a_minute_do_not_count(pool):
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO rate_events (fingerprint, created_at) SELECT 'fp', now() - interval '61 seconds' FROM generate_series(1, 6)"
        )
    assert await RateLimiter(pool, per_minute=6).allow("fp")


async def test_each_visitor_has_its_own_budget(pool):
    limiter = RateLimiter(pool, per_minute=1)
    assert await limiter.allow("a")
    assert await limiter.allow("b")
    assert not await limiter.allow("a")
