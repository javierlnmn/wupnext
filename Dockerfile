# syntax=docker/dockerfile:1

FROM python:3.13-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "poetry>=2.0,<3.0"

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main

COPY theme/static_src/package.json theme/static_src/package-lock.json ./theme/static_src/
RUN npm --prefix ./theme/static_src ci

COPY . .

ENV SECRET_KEY=build-time-only DEBUG=False
RUN python manage.py tailwind build \
    && python manage.py collectstatic --noinput --clear


FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY . .
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/staticfiles /app/staticfiles

RUN mkdir -p /app/db /app/media

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py schedule_due_reminders && { python manage.py createsuperuser --noinput || true; } && exec gunicorn wupnext.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --threads ${GUNICORN_THREADS:-2}"]
