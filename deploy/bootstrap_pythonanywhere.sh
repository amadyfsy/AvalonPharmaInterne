#!/bin/bash
# Configuration initiale unique sur PythonAnywhere (console Bash).
# Usage : bash deploy/bootstrap_pythonanywhere.sh VOTRE_USER

set -euo pipefail

PA_USER="${1:-}"
if [ -z "$PA_USER" ]; then
  echo "Usage: bash deploy/bootstrap_pythonanywhere.sh VOTRE_USER"
  exit 1
fi

PROJECT_DIR="$HOME/AvalonPharmaInterne"
VENV_DIR="$HOME/.virtualenvs/avalon-interne"
PYTHON_BIN="/usr/bin/python3.10"

echo "=== Bootstrap AvalonPharmaInterne pour $PA_USER ==="

if [ ! -d "$PROJECT_DIR/.git" ]; then
  git clone https://github.com/amadyfsy/AvalonPharmaInterne.git "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "IMPORTANT : éditez .env avant le premier déploiement auto :"
  echo "  nano $PROJECT_DIR/.env"
  echo ""
fi

if [ ! -d "$VENV_DIR/bin" ]; then
  mkdir -p "$(dirname "$VENV_DIR")"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

WSGI_FILE="/var/www/${PA_USER}_pythonanywhere_com_wsgi.py"
echo ""
echo "=== Collez ceci dans $WSGI_FILE (onglet Web → WSGI) ==="
cat <<EOF
import sys
project_home = '/home/${PA_USER}/AvalonPharmaInterne'
if project_home not in sys.path:
    sys.path.insert(0, project_home)
from wsgi import application
EOF

echo ""
echo "=== Onglet Web ==="
echo "Virtualenv : $VENV_DIR"
echo "Static     : /static/ -> $PROJECT_DIR/app/static"
echo ""
echo "Ensuite : configurez les secrets GitHub (voir deploy/GITHUB_ACTIONS.md)"
echo "et poussez sur main pour déployer automatiquement."
