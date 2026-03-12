FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=1.8.5 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_CREATE=false \
    PATH="/opt/poetry/bin:$PATH" \
    PORT=8050

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app

COPY pyproject.toml README.md ./
RUN poetry install --no-interaction --no-ansi --no-root

COPY . .

EXPOSE 8050

CMD ["poetry", "run", "gunicorn", "app:server", "--bind", "0.0.0.0:8050", "--workers", "1", "--threads", "4", "--timeout", "120"]
