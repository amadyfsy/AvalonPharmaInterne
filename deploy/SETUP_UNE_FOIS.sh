#!/usr/bin/env bash
# Secrets GitHub pour Avalon sur avalonpharma.pythonanywhere.com (compte DMS07)
set -euo pipefail

# ═══ REMPLISSEZ ICI ═══
PA_PASSWORD='VOTRE_MOT_DE_PASSE_CONNEXION_PYTHONANYWHERE'
PA_API_TOKEN='VOTRE_TOKEN_API_PYTHONANYWHERE'
MYSQL_PASSWORD='VOTRE_MOT_DE_PASSE_MYSQL_DATABASES'
# ═══════════════════════

PA_USERNAME='DMS07'
PA_DOMAIN='avalonpharma.pythonanywhere.com'
REPO='amadyfsy/AvalonPharmaInterne'

command -v gh >/dev/null || { echo "Installez: brew install gh"; exit 1; }
gh auth status >/dev/null 2>&1 || gh auth login

SK=$(python3 -c "import secrets; print(secrets.token_hex(32))")
SALT=$(python3 -c "import secrets; print(secrets.token_hex(16))")
ENC=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

gh secret set PA_USERNAME -R "$REPO" -b"$PA_USERNAME"
gh secret set PA_DOMAIN -R "$REPO" -b"$PA_DOMAIN"
gh secret set PA_PASSWORD -R "$REPO" -b"$PA_PASSWORD"
gh secret set PA_API_TOKEN -R "$REPO" -b"$PA_API_TOKEN"
gh secret set MYSQL_PASSWORD -R "$REPO" -b"$MYSQL_PASSWORD"
gh secret set SECRET_KEY -R "$REPO" -b"$SK"
gh secret set SECURITY_PASSWORD_SALT -R "$REPO" -b"$SALT"
gh secret set ENCRYPTION_KEY -R "$REPO" -b"$ENC"

echo "✓ Secrets OK → déploiement…"
gh workflow run deploy-pythonanywhere.yml -R "$REPO" --ref main
echo "Actions: https://github.com/$REPO/actions"
echo "ERP:     https://${PA_DOMAIN}/auth/login"
