# Enregistrer les secrets GitHub (une seule fois)

Exécutez localement après avoir rempli les valeurs :

```bash
cd AvalonPharmaInterne
export PA_USERNAME=DMS07
export PA_PASSWORD='mot_de_passe_connexion_pythonanywhere'
export PA_API_TOKEN='votre_token_api_pa'
export MYSQL_PASSWORD='mot_de_passe_mysql_onglet_databases'

gh secret set PA_USERNAME -b"$PA_USERNAME"
gh secret set PA_PASSWORD -b"$PA_PASSWORD"
gh secret set PA_API_TOKEN -b"$PA_API_TOKEN"
gh secret set MYSQL_PASSWORD -b"$MYSQL_PASSWORD"
gh secret set PUBLIC_CORS_ORIGINS -b"https://votre-projet.vercel.app"
```

Optionnel (sinon générés automatiquement au 1er déploiement) :

```bash
gh secret set SECRET_KEY -b"$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
gh secret set SECURITY_PASSWORD_SALT -b"$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
gh secret set ENCRYPTION_KEY -b"$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
```

Puis déclenchez : **Actions → Deploy PythonAnywhere → Run workflow**

Ou `git push origin main`.

## Secrets requis

| Secret | Exemple DMS07 |
|--------|----------------|
| `PA_USERNAME` | `DMS07` |
| `PA_PASSWORD` | Mot de passe compte PA |
| `PA_API_TOKEN` | Account → API token |
| `MYSQL_PASSWORD` | Onglet Databases |

## Base de données (automatique)

Le workflow écrit :

`DMS07$Avalon_pharma` sur `DMS07.mysql.pythonanywhere-services.com`
