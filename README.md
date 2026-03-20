# Daychron

A focused task queue app built with Django. Add tasks to your daily queue, work through them one at a time with timer, and track your progress throughout the day.

## Setup

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/)
- Node.js and npm (for Tailwind CSS)

### Environment

Copy the example env file and adjust as needed:

```
cp .env.example .env
```

Then set these in your `.env` file:

- `DEBUG=False`
- `SECRET_KEY` — a random secret key
- `ALLOWED_HOSTS` — comma-separated list of hosts
- `CSRF_TRUSTED_ORIGINS` — comma-separated list of origins

### Local

```bash
poetry install
poetry run python manage.py tailwind install
poetry run python manage.py migrate
```

Run these two commands in separate terminals:

```bash
poetry run python manage.py tailwind start
```

```bash
poetry run python manage.py runserver
```

### Docker (dev)

```bash
docker compose -f docker-compose.dev.yaml up
```

### Docker (prod)

Build the image, then run with env file and named volumes for the SQLite DB and static files:

```bash
docker build -f Dockerfile.prod -t daychron .

docker run --rm -p 8000:8000 --env-file .env \
  -v daychron_db:/data/app/db \
  -v daychron_static:/data/app/staticfiles \
  daychron
```

Create migrations locally (`poetry run python manage.py makemigrations`) before building; the container only runs `migrate`.
