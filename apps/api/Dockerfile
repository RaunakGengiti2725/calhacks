# DryRun — API gateway + agents image. Build context is the repo root.
FROM python:3.11-slim

# uv for dependency management
RUN pip install --no-cache-dir uv

WORKDIR /app
COPY . .

# Install with the agents extra so the same image can serve the API or run agents.
RUN uv sync --extra agents

ENV DRYRUN_MODE=mock
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
