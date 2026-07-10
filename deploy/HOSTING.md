# Hébergement Avalon ERP — ne pas utiliser dms07.pythonanywhere.com

## Situation actuelle

Le compte **DMS07** héberge déjà **DMS-Shoper** sur :

https://dms07.pythonanywhere.com/login

Sur l’offre gratuite PythonAnywhere, **un seul site web** est possible par compte (`username.pythonanywhere.com`).

➡️ **Avalon ERP ne peut pas** être déployé sur cette même URL sans remplacer DMS-Shoper.

La base `DMS07$Avalon_pharma` peut exister sur le compte, mais l’application web Avalon doit aller **ailleurs**.

---

## Options recommandées

### Option 1 — Nouveau compte PythonAnywhere (recommandé, gratuit)

1. Créez un compte PA dédié, ex. `avalonpharmasn`
2. Créez une base MySQL sur ce **nouveau** compte
3. Déployez Avalon sur `https://avalonpharmasn.pythonanywhere.com`

Dans `deploy/SETUP_UNE_FOIS.sh` :

```bash
PA_USERNAME='avalonpharmasn'   # PAS DMS07
PA_DOMAIN='avalonpharmasn.pythonanywhere.com'
```

### Option 2 — Docker (serveur / VPS / local)

```bash
cp .env.example .env
docker compose up -d --build
```

ERP : http://localhost:5050/auth/login

Aucun conflit avec DMS-Shoper.

### Option 3 — Compte DMS07 payant (domaine personnalisé)

Avec un plan payant PA, vous pouvez ajouter une **deuxième web app** ou un **domaine personnalisé** (ex. `erp.avalon-pharma.sn`) en plus de DMS-Shoper.

---

## GitHub Actions — secrets à utiliser

| Secret | DMS07 (DMS-Shoper) | Nouveau compte Avalon |
|--------|--------------------|------------------------|
| `PA_USERNAME` | ❌ ne pas utiliser pour Avalon | `avalonpharmasn` |
| `PA_DOMAIN` | ❌ | `avalonpharmasn.pythonanywhere.com` |
| `MYSQL_PASSWORD` | base DMS07 si même compte | mot de passe du **nouveau** compte |

---

## Site public Vercel

Indépendant. Variable :

```
VITE_API_BASE=https://VOTRE_NOUVEAU_USER.pythonanywhere.com/api/public/v1
```

Et sur l’ERP :

```
PUBLIC_CORS_ORIGINS=https://votre-projet.vercel.app
```
