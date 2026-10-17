FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
# Lambda Web Adapter runs the same uvicorn server inside Lambda and streams the response (SSE).
# Outside Lambda the extension is never started, so the image still runs anywhere.
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 PYTHONDONTWRITEBYTECODE=1 \
    AWS_LWA_PORT=8080 AWS_LWA_INVOKE_MODE=response_stream AWS_LWA_READINESS_CHECK_PATH=/api/health
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/app ./app
EXPOSE 8080
# Access logs are off: they would record client IPs, which we never keep.
CMD ["/app/.venv/bin/uvicorn", "--factory", "app.main:build_app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log", "--proxy-headers", "--forwarded-allow-ips", "*"]
