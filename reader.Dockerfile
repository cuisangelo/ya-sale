# The browser reader: the backend code plus Chromium and a virtual display, run as a worker
# that drains reader_requests. The API image (Dockerfile) never carries a browser.
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --group reader
COPY backend/app ./app
# A real, headed Chromium on Xvfb: the same browser a visitor runs, identified as YaSaleBot.
# xvfb-run waits on a signal a bare PID 1 never delivers: run it with an init (docker --init, ECS initProcessEnabled).
ENTRYPOINT ["xvfb-run", "-a", "-s", "-screen 0 1280x800x24", "/opt/venv/bin/python", "-m", "app.reader"]
CMD ["worker"]
