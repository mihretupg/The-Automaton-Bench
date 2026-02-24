FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml /app/
RUN pip install --no-cache-dir uv && uv sync --no-dev

COPY . /app

EXPOSE 8000

CMD ["uv", "run", "automaton-bench-api"]
