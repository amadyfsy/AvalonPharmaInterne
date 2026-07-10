# Guide PythonAnywhere — AvalonPharmaInterne

Déploiement pas à pas de l'ERP privé Avalon sur [PythonAnywhere](https://www.pythonanywhere.com).

Remplacez `VOTRE_USER` par votre identifiant PA (ex. `amadyfsy`).

---

## Étape 1 — Créer / ouvrir le compte

1. Connectez-vous sur https://www.pythonanywhere.com
2. Notez votre **username** (en haut à droite) → `VOTRE_USER`
3. URL du site : `https://VOTRE_USER.pythonanywhere.com`

---

## Étape 2 — Base MySQL

1. Onglet **Databases**
2. Choisissez un mot de passe MySQL (notez-le : `MYSQL_PA_PASSWORD`)
3. Créez une base, ex. `medical_erp`
   - Nom complet affiché : `VOTRE_USER$medical_erp`
4. Notez l'hôte : `VOTRE_USER.mysql.pythonanywhere-services.com`

**DATABASE_URL** (à mettre dans `.env`) :

```
mysql+pymysql://VOTRE_USER:MYSQL_PA_PASSWORD@VOTRE_USER.mysql.pythonanywhere-services.com/VOTRE_USER$medical_erp?charset=utf8mb4
```

> Si le mot de passe contient des caractères spéciaux (`@`, `#`, `%`…), encodez-les en URL ou utilisez un mot de passe alphanumérique.

---

## Étape 3 — Cloner le projet

Onglet **Consoles** → **Bash** :

```bash
cd ~
git clone https://github.com/amadyfsy/AvalonPharmaInterne.git
cd AvalonPharmaInterne
```

---

## Étape 4 — Environnement virtuel Python

Toujours dans la console Bash :

```bash
mkvirtualenv --python=/usr/bin/python3.10 avalon-interne
workon avalon-interne
pip install --upgrade pip
pip install -r requirements.txt
```

*(Python 3.10 ou 3.11 selon ce que propose votre compte PA.)*

---

## Étape 5 — Fichier `.env`

```bash
cd ~/AvalonPharmaInterne
cp .env.example .env
nano .env
```

Générez les secrets (dans la console) :

```bash
python3.10 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
python3.10 -c "import secrets; print('SECURITY_PASSWORD_SALT=' + secrets.token_hex(16))"
python3.10 -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

Exemple de `.env` rempli :

```env
SECRET_KEY=votre_cle_64_caracteres_hex
SECURITY_PASSWORD_SALT=votre_salt_32_caracteres_hex
ENCRYPTION_KEY=votre_cle_fernet_base64

DATABASE_URL=mysql+pymysql://VOTRE_USER:MOT_DE_PASSE@VOTRE_USER.mysql.pythonanywhere-services.com/VOTRE_USER$medical_erp?charset=utf8mb4

FLASK_CONFIG=production
TALISMAN_FORCE_HTTPS=true
PUBLIC_CORS_ORIGINS=https://votre-projet.vercel.app

MAIL_SUPPRESS_SEND=true
COMPANY_NAME=Avalon Pharma Senegal
```

Enregistrez : `Ctrl+O`, Entrée, `Ctrl+X`.

---

## Étape 6 — Initialiser les tables

```bash
workon avalon-interne
cd ~/AvalonPharmaInterne
python -c "
from app import create_app
from app.extensions import db
import app.models
app = create_app('production')
with app.app_context():
    db.create_all()
    print('Tables créées.')
"
```

Si erreur `SECRET_KEY` : vérifiez que `.env` est bien dans `~/AvalonPharmaInterne/`.

---

## Étape 7 — Configurer l'application Web

1. Onglet **Web**
2. **Add a new web app** (si pas encore fait) → **Manual configuration** → **Python 3.10**
3. Réglez :

| Paramètre | Valeur |
|-----------|--------|
| **Source code** | `/home/VOTRE_USER/AvalonPharmaInterne` |
| **Working directory** | `/home/VOTRE_USER/AvalonPharmaInterne` |
| **Virtualenv** | `/home/VOTRE_USER/.virtualenvs/avalon-interne` |

4. **Static files** — ajoutez une ligne :

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/VOTRE_USER/AvalonPharmaInterne/app/static` |

5. **WSGI configuration file** — cliquez sur le lien du fichier WSGI et remplacez tout par :

```python
import sys

project_home = '/home/VOTRE_USER/AvalonPharmaInterne'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from wsgi import application
```

*(Remplacez `VOTRE_USER`.)*

6. **Force HTTPS** : cochez si disponible (recommandé).

7. Cliquez sur le gros bouton vert **Reload** `VOTRE_USER.pythonanywhere.com`.

---

## Étape 8 — Tester

1. **Santé** : https://VOTRE_USER.pythonanywhere.com/ping  
   → doit afficher une réponse (ex. `pong` ou JSON OK)

2. **Connexion ERP** : https://VOTRE_USER.pythonanywhere.com/auth/login

3. **API publique** (pour Vercel) :  
   https://VOTRE_USER.pythonanywhere.com/api/public/v1/entreprise  
   → JSON entreprise

---

## Étape 9 — Lier le site Vercel

Sur **Vercel** (dépôt AvalonPharmapublic) :

```
VITE_API_BASE=https://VOTRE_USER.pythonanywhere.com/api/public/v1
```

Sur **PythonAnywhere**, dans `.env` :

```
PUBLIC_CORS_ORIGINS=https://votre-url-vercel.app
```

Puis **Reload** l'app Web.

---

## Étape 10 — Premier utilisateur admin

Si aucun compte n'existe encore, en console :

```bash
workon avalon-interne
cd ~/AvalonPharmaInterne
python -c "
from app import create_app
from app.extensions import db, bcrypt
from app.models.user import User

app = create_app('production')
with app.app_context():
    if User.query.filter_by(email='admin@avalon.sn').first():
        print('Compte admin existe déjà.')
    else:
        u = User(
            first_name='Admin',
            last_name='Avalon',
            email='admin@avalon.sn',
            password_hash=bcrypt.generate_password_hash('ChangerCeMdp123!', rounds=12).decode('utf-8'),
            role='admin',
            is_active=True,
        )
        db.session.add(u)
        db.session.commit()
        print('Admin créé : admin@avalon.sn / ChangerCeMdp123!')
"
```

**Changez ce mot de passe** dès la première connexion (Profil).

---

## Mises à jour (après un `git pull`)

```bash
cd ~/AvalonPharmaInterne
git pull origin main
workon avalon-interne
pip install -r requirements.txt
```

Puis onglet **Web** → **Reload**, ou en console :

```bash
curl -X POST \
  -H "Authorization: Token $API_TOKEN" \
  "https://www.pythonanywhere.com/api/v0/user/$USER/webapps/$USER.pythonanywhere.com/reload/"
```

---

## Dépannage

### Erreur 500 au chargement

- Onglet **Web** → **Error log** (lien en bas)
- Vérifiez virtualenv, chemin WSGI, `.env` et `DATABASE_URL`

### `SECRET_KEY est obligatoire`

- `.env` manquant ou `FLASK_CONFIG=production` sans `SECRET_KEY`

### Erreur MySQL / connexion refusée

- Vérifiez mot de passe et nom de base `VOTRE_USER$medical_erp`
- Test :

```bash
workon avalon-interne
python -c "import os; from dotenv import load_dotenv; load_dotenv(); import pymysql; print('ok')"
```

### Static CSS/JS ne chargent pas

- Vérifiez la ligne **Static files** `/static/` → `app/static`

### CORS sur Vercel

- `PUBLIC_CORS_ORIGINS` doit être **exactement** l'URL Vercel (sans slash final)
- Reload après modification de `.env`

---

## Sécurité

- Ne commitez **jamais** `.env` ni votre token API PA
- Régénérez le token API si vous l'avez partagé (Account → API token)
- Utilisez **HTTPS** sur PA et Vercel
- Comptes : pas de mot de passe `passer123` en production
