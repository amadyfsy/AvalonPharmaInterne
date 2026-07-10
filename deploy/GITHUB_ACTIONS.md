# Déploiement automatique — GitHub Actions → PythonAnywhere

Chaque **push sur `main`** déploie automatiquement l'ERP sur PythonAnywhere.

## Configuration unique (≈ 15 minutes)

### 1. Secrets GitHub

Dépôt **AvalonPharmaInterne** → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret | Description |
|--------|-------------|
| `PA_USERNAME` | Votre identifiant PythonAnywhere |
| `PA_PASSWORD` | Mot de passe de **connexion** PA (utilisé pour SSH) |
| `PA_API_TOKEN` | Token API (Account → API token) |

Optionnels :

| Secret | Défaut |
|--------|--------|
| `PA_DOMAIN` | `{PA_USERNAME}.pythonanywhere.com` |
| `PA_SSH_HOST` | `ssh.pythonanywhere.com` (EU : `ssh.eu.pythonanywhere.com`) |
| `PA_API_HOST` | `www.pythonanywhere.com` (EU : `eu.pythonanywhere.com`) |
| `PA_PROJECT_DIR` | `$HOME/AvalonPharmaInterne` |
| `PA_VENV_DIR` | `$HOME/.virtualenvs/avalon-interne` |
| `PA_PYTHON` | `/usr/bin/python3.10` |

> Ne mettez **jamais** ces valeurs dans le code source.

### 2. Environnement GitHub (recommandé)

**Settings** → **Environments** → **New environment** → nom : `production`

Ajoutez les mêmes secrets dans cet environnement (protection optionnelle des déploiements).

Le workflow utilise `environment: production`.

### 3. Configuration unique sur PythonAnywhere

#### A. Base MySQL (onglet Databases)

- Créez la base `medical_erp`
- Notez le mot de passe MySQL

#### B. Fichier `.env` sur le serveur (une seule fois)

Console **Bash** PA :

```bash
mkdir -p ~/AvalonPharmaInterne
cd ~/AvalonPharmaInterne
git clone https://github.com/amadyfsy/AvalonPharmaInterne.git .
cp .env.example .env
nano .env
```

Remplissez `SECRET_KEY`, `SECURITY_PASSWORD_SALT`, `ENCRYPTION_KEY`, `DATABASE_URL`, `PUBLIC_CORS_ORIGINS`.

Génération des clés :

```bash
python3.10 -c "import secrets; print(secrets.token_hex(32))"
python3.10 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

#### C. Application Web (onglet Web — une seule fois)

1. **Add a new web app** → Manual configuration → Python 3.10
2. **Virtualenv** : `/home/VOTRE_USER/.virtualenvs/avalon-interne`
3. **Source code** : `/home/VOTRE_USER/AvalonPharmaInterne`
4. **Static files** : `/static/` → `/home/VOTRE_USER/AvalonPharmaInterne/app/static`
5. **WSGI** (`/var/www/VOTRE_USER_pythonanywhere_com_wsgi.py`) :

```python
import sys
project_home = '/home/VOTRE_USER/AvalonPharmaInterne'
if project_home not in sys.path:
    sys.path.insert(0, project_home)
from wsgi import application
```

6. **Reload** une fois

### 4. Premier déploiement automatique

```bash
git push origin main
```

Ou : **Actions** → **Deploy PythonAnywhere** → **Run workflow**

---

## Ce que fait le workflow à chaque push

1. Se connecte en SSH à PythonAnywhere
2. `git fetch` + `git reset --hard origin/main`
3. Met à jour le virtualenv (`pip install -r requirements.txt`)
4. Vérifie que `.env` existe sur le serveur
5. Exécute `db.create_all()` (schéma à jour)
6. Recharge l'app via l'API PythonAnywhere

---

## Dépannage

### Secret manquant

Le workflow échoue avec le nom du secret à ajouter.

### `.env` absent

Créez-le sur PA (étape 3B), puis relancez le workflow.

### Erreur SSH

- Vérifiez `PA_USERNAME` et `PA_PASSWORD` (mot de passe du **compte**, pas MySQL)
- Compte EU : `PA_SSH_HOST=ssh.eu.pythonanywhere.com`

### Erreur reload API

- Régénérez `PA_API_TOKEN` sur PA
- Vérifiez `PA_DOMAIN` (ex. `amadyfsy.pythonanywhere.com`)

### Logs

GitHub → **Actions** → dernier run → détails des étapes

PythonAnywhere → **Web** → **Error log**

---

## Site public Vercel (séparé)

Le site React se déploie automatiquement via **Vercel** connecté au dépôt **AvalonPharmapublic** (import GitHub sur vercel.com).

Variable Vercel :

```
VITE_API_BASE=https://VOTRE_USER.pythonanywhere.com/api/public/v1
```
