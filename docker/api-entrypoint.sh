#!/bin/bash
set -e

echo "Attente de MySQL…"
until python - <<'PY'
import os, sys
import pymysql

uri = os.environ.get("DATABASE_URL", "")
try:
    part = uri.split("://", 1)[1]
    auth, rest = part.split("@", 1)
    user, password = auth.split(":", 1)
    host_port, db_part = rest.split("/", 1)
    host, port = host_port.split(":", 1)
    database = db_part.split("?", 1)[0]
    pymysql.connect(host=host, port=int(port), user=user, password=password, database=database)
except Exception as exc:
    print(exc, file=sys.stderr)
    sys.exit(1)
PY
do
  sleep 2
done
echo "MySQL prêt."

python - <<'PY'
import os
from app import create_app
from app.extensions import db
import app.models  # noqa: F401

app = create_app(os.environ.get("FLASK_CONFIG", "production"))
with app.app_context():
    db.create_all()
    print("Schéma BDD initialisé.")
PY

exec "$@"
