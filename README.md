# AvalonPharmapublic

Plateforme ERP **Avalon Pharma Senegal** (GestAvalon) — déploiement privé dockerisé avec site catalogue public.

## Stack

| Service | Description | Port |
|---------|-------------|------|
| `api` | Flask ERP (gunicorn) | interne 5000 |
| `web` | Site public React + nginx | `8080` (configurable) |
| `db` | MySQL 8 | interne uniquement |

## Déploiement rapide

### 1. Prérequis

- Docker & Docker Compose
- Git

### 2. Configuration sécurisée

```bash
cp .env.example .env
```

Éditez `.env` et **remplacez toutes les valeurs par défaut** :

```bash
# Clé secrète Flask (sessions, CSRF)
python -c "import secrets; print(secrets.token_hex(32))"

# Clé Fernet (données RH chiffrées)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Variables **obligatoires** en production :

- `SECRET_KEY`
- `SECURITY_PASSWORD_SALT`
- `ENCRYPTION_KEY` (recommandé pour le module RH)
- `MYSQL_ROOT_PASSWORD`, `MYSQL_USER`, `MYSQL_PASSWORD`

### 3. Lancer

```bash
docker compose up -d --build
```

- **ERP (connexion)** : http://localhost:5050/auth/login
- **Site public** : http://localhost:8080

### 4. Premier accès

Après le premier démarrage, créez un compte admin via la base ou connectez-vous avec un compte existant importé.

> Changez immédiatement les mots de passe par défaut (`passer123`) sur tous les comptes.

## Sécurité — checklist avant mise en production

- [ ] `.env` rempli avec des secrets forts (jamais commité)
- [ ] MySQL **non exposé** sur Internet (pas de port `3307` publié)
- [ ] `TALISMAN_FORCE_HTTPS=true` derrière un reverse proxy HTTPS
- [ ] `PUBLIC_CORS_ORIGINS` limité à votre domaine (pas `*`)
- [ ] Mots de passe utilisateurs changés
- [ ] Sauvegardes régulières du volume `mysql_data`
- [ ] SMTP configuré pour la réinitialisation de mot de passe

## Développement local (sans Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export FLASK_CONFIG=development
python run.py
```

## Structure

```
app/              # ERP Flask (modules ventes, stock, RH, etc.)
site-public/      # Catalogue React (Vite)
docker/           # Scripts d'entrée conteneur
config.py         # Configuration
run.py            # Point d'entrée WSGI / dev
```

## Licence

Usage privé — Avalon Pharma Senegal.
