FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/app ./app
EXPOSE 8080
# Access logs are off: they would record client IPs, which we never keep.
CMD ["/app/.venv/bin/uvicorn", "--factory", "app.main:build_app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log", "--proxy-headers", "--forwarded-allow-ips", "*"]
