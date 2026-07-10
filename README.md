# AvalonPharmaInterne

ERP privé **Avalon Pharma Senegal** (GestAvalon) — ventes, stock, RH, dépenses, sécurité.

> Le **site catalogue public** est dans le dépôt séparé [AvalonPharmapublic](https://github.com/amadyfsy/AvalonPharmapublic) et se déploie sur **Vercel**.

## Déploiement automatique (GitHub Actions)

Chaque push sur `main` déploie sur **PythonAnywhere** sans intervention manuelle.

**Configuration unique** : voir [deploy/GITHUB_ACTIONS.md](deploy/GITHUB_ACTIONS.md)

Secrets GitHub requis : `PA_USERNAME`, `PA_PASSWORD`, `PA_API_TOKEN`

Guide détaillé PA : [deploy/PYTHONANYWHERE.md](deploy/PYTHONANYWHERE.md)

## Déploiement cible

| Composant | Hébergement |
|-----------|-------------|
| ERP interne | **PythonAnywhere** (ou Docker local) |
| Site public | **Vercel** (autre dépôt) |

## PythonAnywhere — première installation

### 1. Cloner sur PythonAnywhere

Dans une console Bash PA :

```bash
cd ~
git clone https://github.com/amadyfsy/AvalonPharmaInterne.git
cd AvalonPharmaInterne
```

### 2. Environnement virtuel

```bash
mkvirtualenv --python=/usr/bin/python3.10 avalon-interne
pip install -r requirements.txt
```

### 3. Variables d'environnement

```bash
cp .env.example .env
nano .env
```

Renseignez au minimum :

- `SECRET_KEY`, `SECURITY_PASSWORD_SALT`, `ENCRYPTION_KEY`
- `DATABASE_URL` (MySQL PythonAnywhere : voir onglet Databases)
- `PUBLIC_CORS_ORIGINS` = URL Vercel du site public (ex. `https://avalon-pharma.vercel.app`)
- `TALISMAN_FORCE_HTTPS=true`

### 4. Web app (onglet Web)

- **Source code** : `/home/VOTRE_USER/AvalonPharmaInterne`
- **WSGI** : pointer vers `wsgi.py` du projet (voir fichier modèle `deploy/pythonanywhere_wsgi.py.example`)
- **Virtualenv** : `/home/VOTRE_USER/.virtualenvs/avalon-interne`
- **Static files** : `/static/` → `/home/VOTRE_USER/AvalonPharmaInterne/app/static`

### 5. Base de données

Créez une base MySQL sur PA, puis :

```bash
workon avalon-interne
cd ~/AvalonPharmaInterne
python -c "from app import create_app; from app.extensions import db; import app.models; app=create_app('production'); ctx=app.app_context(); ctx.push(); db.create_all(); print('OK')"
```

### 6. Recharger l'application

```bash
# Depuis une console PA (API_TOKEN est déjà dans l'environnement)
curl -X POST \
  -H "Authorization: Token $API_TOKEN" \
  "https://www.pythonanywhere.com/api/v0/user/$USER/webapps/$USER.pythonanywhere.com/reload/"
```

> **Ne commitez jamais** votre token API PythonAnywhere. Utilisez les secrets GitHub pour la CI.

## Docker (local / serveur privé)

```bash
cp .env.example .env
docker compose up -d --build
```

- ERP : http://localhost:5050/auth/login

## Développement local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export FLASK_CONFIG=development
python run.py
```

## API publique (pour Vercel)

L'ERP expose en lecture seule :

`https://VOTRE_USER.pythonanywhere.com/api/public/v1`

Configurez cette URL dans Vercel (`VITE_API_BASE`) sur le dépôt AvalonPharmapublic.

## Sécurité

- [ ] Secrets forts dans `.env` (jamais sur Git)
- [ ] CORS limité au domaine Vercel
- [ ] HTTPS activé sur PythonAnywhere
- [ ] Mots de passe `passer123` changés
- [ ] Token API PA régénéré si exposé

## Structure

```
app/           # Modules ERP Flask
deploy/        # Modèles WSGI / CI
config.py
run.py
wsgi.py
```
