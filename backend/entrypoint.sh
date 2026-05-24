#!/bin/sh
set -e

python - <<'PY'
import os
import socket
import time

host = os.getenv('DB_HOST')
port = int(os.getenv('DB_PORT', 5432))
if host:
    for _ in range(60):
        try:
            with socket.create_connection((host, port), timeout=1):
                break
        except OSError:
            time.sleep(1)
    else:
        raise SystemExit('Database is not available')
PY

python manage.py migrate
python manage.py load_tags
python manage.py load_ingredients /app/data/ingredients.csv
python manage.py load_demo_data
python manage.py collectstatic --noinput
gunicorn foodgram.wsgi:application --bind 0.0.0.0:8000
