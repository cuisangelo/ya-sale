import httpx

from app.main import create_app


async def test_static_web_is_served_without_hiding_the_api(settings, tmp_path):
    (tmp_path / "index.html").write_text("<h1>Ya Sale</h1>")
    (tmp_path / "viaje").mkdir()
    (tmp_path / "viaje" / "index.html").write_text("<h1>Viaje</h1>")
    app = create_app(settings, web_dir=tmp_path)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert "Ya Sale" in (await client.get("/")).text
        assert "Viaje" in (await client.get("/viaje/")).text
        assert (await client.get("/api/health")).json() == {"ok": True}
