#!/usr/bin/env bash
# Enregistre les secrets GitHub pour le déploiement automatique PA.
# Usage : PA_PASSWORD=... MYSQL_PASSWORD=... PA_API_TOKEN=... ./deploy/register_github_secrets.sh

set -euo pipefail

PA_USERNAME="${PA_USERNAME:-DMS07}"
PA_PASSWORD="${PA_PASSWORD:?PA_PASSWORD requis}"
PA_API_TOKEN="${PA_API_TOKEN:?PA_API_TOKEN requis}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:?MYSQL_PASSWORD requis}"
PUBLIC_CORS_ORIGINS="${PUBLIC_CORS_ORIGINS:-https://avalon-pharma.vercel.app}"

command -v gh >/dev/null || { echo "Installez gh : brew install gh"; exit 1; }
gh auth status >/dev/null || { echo "Connectez gh : gh auth login"; exit 1; }

gh secret set PA_USERNAME -b"$PA_USERNAME"
gh secret set PA_PASSWORD -b"$PA_PASSWORD"
gh secret set PA_API_TOKEN -b"$PA_API_TOKEN"
gh secret set MYSQL_PASSWORD -b"$MYSQL_PASSWORD"
gh secret set PUBLIC_CORS_ORIGINS -b"$PUBLIC_CORS_ORIGINS"

if [ -z "${SECRET_KEY:-}" ]; then
  SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
fi
if [ -z "${SECURITY_PASSWORD_SALT:-}" ]; then
  SECURITY_PASSWORD_SALT=$(python3 -c "import secrets; print(secrets.token_hex(16))")
fi
if [ -z "${ENCRYPTION_KEY:-}" ]; then
  ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
fi

gh secret set SECRET_KEY -b"$SECRET_KEY"
gh secret set SECURITY_PASSWORD_SALT -b"$SECURITY_PASSWORD_SALT"
gh secret set ENCRYPTION_KEY -b"$ENCRYPTION_KEY"

echo "Secrets GitHub enregistrés pour $PA_USERNAME."
echo "Lancez : gh workflow run deploy-pythonanywhere.yml"
