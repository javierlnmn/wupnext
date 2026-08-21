# WupNext

A dynamic and focused task list:

- Tasks with weights, deadlines and subtasks
- Groups to organise and filter the board
- Drag and drop ordering
- An archive for finished work
- A built-in pomodoro timer
- Email reminders
- MCP server

## Built with

- **Django 5.2** on SQLite, with Poetry for dependency management
- **HTMX** and **Alpine.js** for interactivity, so the app stays server-rendered rather than an SPA
- **SortableJS** for drag and drop
- **Tailwind CSS**, via [django-tailwind](https://django-tailwind.readthedocs.io/)
- **Django Q2** for scheduled jobs, using the database itself as the queue, so there's no Redis to run
- **Anymail** with **Resend** for outgoing email
- **django-mcp-server** and **django-oauth-toolkit** for the MCP endpoint and the OAuth 2.1 flow behind it
- **Gunicorn** and **whitenoise** in production, packaged as a Docker image

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


## MCP server

The app publishes an MCP server at `/mcp`, so an AI client can work the board directly. Clients authenticate with OAuth 2.1 and register themselves through Dynamic Client Registration.

Preferences → **MCP server** shows the endpoint to paste into a client, the tools currently published, and every client holding a token, each with a Revoke button. Set `MCP_BASE_URL` to the public origin — that is what the server advertises to clients during discovery.

The server can be used both within *dev* and *prod* envs.