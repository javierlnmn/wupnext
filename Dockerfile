FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libssl-dev \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/

COPY ./theme/static_src/package.json ./theme/static_src/package-lock.json /data/
WORKDIR /data/
RUN npm install
ENV PATH=/data/node_modules/.bin:$PATH

COPY . /data/app/
WORKDIR /data/app/

RUN mkdir -p db staticfiles && touch ./db/db.sqlite3

RUN pip install --no-cache-dir poetry \
    && poetry install --no-interaction --no-ansi

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD sh -c "\
    poetry run python manage.py migrate --noinput && \
    poetry run python manage.py tailwind build && \
    poetry run python manage.py collectstatic --noinput && \
    exec poetry run gunicorn daychron.wsgi:application \
    --bind 0.0.0.0:8000 --workers 1 --threads 2 \
    "
