FROM python:3.14.4-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
COPY uv.lock* ./

RUN uv sync --frozen || uv sync

COPY . .

EXPOSE 8000

CMD ["uv", "run", "vvt-api"]