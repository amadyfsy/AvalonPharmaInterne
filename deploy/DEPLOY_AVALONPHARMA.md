# Déploiement Avalon sur avalonpharma.pythonanywhere.com (compte DMS07)

DMS-Shoper reste sur : https://dms07.pythonanywhere.com  
Avalon ERP va sur : **https://avalonpharma.pythonanywhere.com**

Onglet Web cible :  
https://www.pythonanywhere.com/user/DMS07/webapps/#tab_id_avalonpharma__pythonanywhere

---

## A. Une fois dans la console Bash PythonAnywhere

Copiez-collez **tout le bloc** :

```bash
cd ~
git clone https://github.com/amadyfsy/AvalonPharmaInterne.git || true
cd ~/AvalonPharmaInterne
git fetch origin main && git reset --hard origin/main

# Python 3.12 si dispo, sinon 3.10
PY=/usr/bin/python3.12; [ -x "$PY" ] || PY=/usr/bin/python3.10
"$PY" -m venv ~/.virtualenvs/avalon-interne
source ~/.virtualenvs/avalon-interne/bin/activate
pip install -U pip
pip install -r requirements.txt

# .env — REMPLACEZ MOT_DE_PASSE_MYSQL
cp deploy/env.dms07.example .env
nano .env
```

Dans `.env`, lignes importantes :

```env
DATABASE_URL=mysql+pymysql://DMS07:MOT_DE_PASSE_MYSQL@DMS07.mysql.pythonanywhere-services.com/DMS07%24Avalon_pharma?charset=utf8mb4
FLASK_CONFIG=production
TALISMAN_FORCE_HTTPS=true
```

Générez les clés :

```bash
python -c "import secrets; print('SECRET_KEY='+secrets.token_hex(32))"
python -c "import secrets; print('SECURITY_PASSWORD_SALT='+secrets.token_hex(16))"
python -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY='+Fernet.generate_key().decode())"
```

Créer les tables :

```bash
cd ~/AvalonPharmaInterne
source ~/.virtualenvs/avalon-interne/bin/activate
set -a && source .env && set +a
python -c "
from app import create_app
from app.extensions import db
import app.models
app = create_app('production')
with app.app_context():
    db.create_all()
    print('OK')
"
```

---

## B. Onglet Web → avalonpharma.pythonanywhere.com

| Paramètre | Valeur |
|-----------|--------|
| Source code | `/home/DMS07/AvalonPharmaInterne` |
| Working directory | `/home/DMS07/AvalonPharmaInterne` |
| Virtualenv | `/home/DMS07/.virtualenvs/avalon-interne` |
| Static `/static/` | `/home/DMS07/AvalonPharmaInterne/app/static` |

**Fichier WSGI** (lien dans l’onglet Web) — remplacer **tout** le contenu par :

```python
import sys
project_home = '/home/DMS07/AvalonPharmaInterne'
if project_home not in sys.path:
    sys.path.insert(0, project_home)
from wsgi import application
```

⚠️ Ne modifiez **pas** le WSGI de `dms07.pythonanywhere.com` (DMS-Shoper).

Puis bouton vert **Reload** sur l’onglet **avalonpharma**.

---

## C. Tester

- https://avalonpharma.pythonanywhere.com/ping  
- https://avalonpharma.pythonanywhere.com/auth/login  

Créer un admin si besoin :

```bash
cd ~/AvalonPharmaInterne && source ~/.virtualenvs/avalon-interne/bin/activate
set -a && source .env && set +a
python -c "
from app import create_app
from app.extensions import db, bcrypt
from app.models.user import User
app = create_app('production')
with app.app_context():
    if not User.query.filter_by(email='admin@avalon.sn').first():
        u = User(first_name='Admin', last_name='Avalon', email='admin@avalon.sn',
            password_hash=bcrypt.generate_password_hash('ChangerCeMdp123!', rounds=12).decode(),
            role='admin', is_active=True)
        db.session.add(u); db.session.commit()
        print('admin@avalon.sn / ChangerCeMdp123!')
    else:
        print('admin existe déjà')
"
```

---

## D. Déploiements suivants (auto)

Secrets GitHub (`AvalonPharmaInterne`) :

| Secret | Valeur |
|--------|--------|
| `PA_USERNAME` | `DMS07` |
| `PA_DOMAIN` | `avalonpharma.pythonanywhere.com` |
| `PA_PASSWORD` | mot de passe compte PA |
| `PA_API_TOKEN` | Account → API token |
| `MYSQL_PASSWORD` | onglet Databases |

Ensuite chaque `git push` sur `main` met à jour Avalon **sans toucher** DMS-Shoper.
