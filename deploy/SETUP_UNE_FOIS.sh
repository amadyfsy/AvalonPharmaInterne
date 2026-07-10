#!/usr/bin/env bash
# Configuration en 1 commande — après avoir rempli les 3 valeurs ci-dessous.
set -euo pipefail

# ═══ REMPLISSEZ ICI (une seule fois) ═══
# ⚠️  N'utilisez PAS DMS07 si DMS-Shoper tourne déjà sur dms07.pythonanywhere.com
#     Créez un NOUVEAU compte PythonAnywhere pour Avalon (voir deploy/HOSTING.md)
PA_USERNAME='avalonpharmasn'
PA_DOMAIN='avalonpharmasn.pythonanywhere.com'
PA_PASSWORD='VOTRE_MOT_DE_PASSE_CONNEXION_PYTHONANYWHERE'
PA_API_TOKEN='VOTRE_TOKEN_API_PYTHONANYWHERE'
MYSQL_PASSWORD='VOTRE_MOT_DE_PASSE_MYSQL_DATABASES'
# ═══════════════════════════════════════

REPO="amadyfsy/AvalonPharmaInterne"

if ! command -v gh >/dev/null 2>&1; then
  echo "Installation de GitHub CLI…"
  if command -v brew >/dev/null 2>&1; then
    brew install gh
  else
    echo "Installez gh : https://cli.github.com/"
    exit 1
  fi
fi

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
gh secret set PUBLIC_CORS_ORIGINS -R "$REPO" -b"https://avalon-pharma.vercel.app"

echo ""
echo "✓ Secrets enregistrés sur GitHub."
echo "→ Lancement du déploiement automatique…"
gh workflow run deploy-pythonanywhere.yml -R "$REPO" --ref main
echo ""
echo "Suivez : https://github.com/$REPO/actions"
echo "ERP    : https://${PA_DOMAIN}/auth/login"
