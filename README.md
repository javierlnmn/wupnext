# Wupnext

A focused task list built with Django. Add tasks whenever you want, work through them, and check them off — pending and completed tasks always live on the same page, no daily reset.

## Development

Development runs directly on the host (no Docker) — Poetry for the Python side, npm for Tailwind.

### Prerequisites

- Python 3.11–3.13
- [Poetry](https://python-poetry.org/)
- Node.js and npm (for Tailwind CSS)

### Environment

Copy the example env file:

```bash
cp .env.example .env
```

The defaults in `.env.example` (`DEBUG=True`, `localhost`/`127.0.0.1`) are already suitable for local development.

### Setup

```bash
poetry install
poetry run python manage.py tailwind install
poetry run python manage.py migrate
```

### Tailwind

Styles are built with [django-tailwind](https://django-tailwind.readthedocs.io/), which manages a Tailwind CLI project under `theme/static_src/`. `tailwind install` (above) installs its npm dependencies the first time you set up the project — rerun it if `theme/static_src/package.json` changes.

While developing, run the Tailwind watcher in its own terminal so template class changes are picked up and rebuilt into `theme/static/css/dist/styles.css` on save:

```bash
poetry run python manage.py tailwind start
```

### Run the app

In another terminal:

```bash
poetry run python manage.py runserver
```

The app is then available at http://127.0.0.1:8000.

## Deploy

Production is Docker-only, built from `Dockerfile`. Build the image, then run with an env file and named volumes for the SQLite DB and static files:

```bash
docker build -t wupnext .

docker run --rm -p 8000:8000 --env-file .env \
  -v wupnext_db:/data/app/db \
  -v wupnext_static:/data/app/staticfiles \
  wupnext
```

Create migrations locally (`poetry run python manage.py makemigrations`) before building; the container only runs `migrate`. Before deploying, make sure `.env` has production values set: `DEBUG=False`, a real `SECRET_KEY`, `ALLOWED_HOSTS`, and `CSRF_TRUSTED_ORIGINS`.
