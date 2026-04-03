# Bras Droit — Guide de deploiement complet

## Architecture

```
GitHub (code source)
    ├── /backend  → Render (FastAPI + PostgreSQL)
    └── /frontend → Vercel (HTML statique)
```

---

## ETAPE 1 — Preparer GitHub

1. Creer un compte sur https://github.com
2. Creer un nouveau repo : `brasdroit`
3. Mettre le code dedans :

```bash
git init
git add .
git commit -m "Initial commit — Bras Droit"
git remote add origin https://github.com/TON_PSEUDO/brasdroit.git
git push -u origin main
```

---

## ETAPE 2 — Deployer le backend sur Render

1. Aller sur https://render.com
2. Creer un compte (gratuit)
3. Cliquer "New" → "Web Service"
4. Connecter ton repo GitHub `brasdroit`
5. Configurer :
   - **Root Directory** : `backend`
   - **Runtime** : Python 3
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Ajouter les variables d'environnement :
   - `SECRET_KEY` : (Render peut la generer)
   - `ANTHROPIC_API_KEY` : ta cle Claude
   - `FRONTEND_URL` : https://brasdroit.vercel.app

7. Creer la base PostgreSQL :
   - "New" → "PostgreSQL"
   - Nom : `brasdroit-db`
   - Plan : Free
   - Copier la `Internal Database URL`
   - L'ajouter comme variable `DATABASE_URL` dans le Web Service

8. Deployer → attendre 3-5 minutes

Ton API sera accessible sur : `https://brasdroit-api.onrender.com`
Swagger UI : `https://brasdroit-api.onrender.com/docs`

---

## ETAPE 3 — Deployer le frontend sur Vercel

1. Aller sur https://vercel.com
2. Creer un compte (gratuit)
3. "Add New Project" → importer le repo GitHub
4. **Root Directory** : `frontend`
5. Ajouter variable d'environnement :
   - `NEXT_PUBLIC_API_URL` : `https://brasdroit-api.onrender.com`
6. Deployer

Ton frontend sera sur : `https://brasdroit.vercel.app`

---

## ETAPE 4 — Connecter le frontend au backend

Dans le fichier `bras_droit.html`, ajouter en debut de script :

```javascript
const API_URL = 'https://brasdroit-api.onrender.com';

// Exemple d'appel API
async function login(email, password) {
    const resp = await fetch(API_URL + '/api/auth/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: new URLSearchParams({username: email, password: password})
    });
    const data = await resp.json();
    localStorage.setItem('token', data.access_token);
}

async function apiGet(endpoint) {
    const token = localStorage.getItem('token');
    const resp = await fetch(API_URL + endpoint, {
        headers: {'Authorization': 'Bearer ' + token}
    });
    return resp.json();
}
```

---

## Couts mensuels

| Service     | Plan   | Cout         |
|-------------|--------|--------------|
| Render API  | Free   | 0 EUR/mois   |
| Render DB   | Free   | 0 EUR/mois (90 jours) puis 7 USD |
| Vercel      | Free   | 0 EUR/mois   |
| Anthropic   | Pay/use | ~5 EUR/mois  |
| **TOTAL**   |        | **~5 EUR/mois** |

---

## Structure des fichiers

```
brasdroit/
├── backend/
│   ├── app/
│   │   ├── main.py              # Point d'entree FastAPI
│   │   ├── core/
│   │   │   ├── config.py        # Variables d'environnement
│   │   │   ├── database.py      # Connexion PostgreSQL
│   │   │   └── security.py      # JWT + bcrypt
│   │   ├── models/
│   │   │   └── models.py        # Tables SQLAlchemy
│   │   ├── schemas/
│   │   │   └── schemas.py       # Validation Pydantic
│   │   ├── routers/
│   │   │   ├── auth.py          # Inscription + Connexion
│   │   │   ├── facturation.py   # BC + Factures + Recouvrement
│   │   │   ├── paie.py          # Employes + Bulletins
│   │   │   └── dashboard.py     # Stats + Alertes + IA
│   │   └── services/
│   │       ├── paie_service.py  # Moteur de calcul paie
│   │       └── ia_service.py    # Anthropic Claude
│   ├── requirements.txt
│   ├── render.yaml
│   └── .env.example
└── frontend/
    └── bras_droit.html          # Interface complete
```

---

## Endpoints API disponibles

### Authentification
- `POST /api/auth/register` — Creer un compte
- `POST /api/auth/login` — Se connecter
- `GET  /api/auth/me` — Mon profil

### Dashboard
- `GET  /api/dashboard/stats` — Chiffres cles
- `GET  /api/dashboard/alertes` — Alertes urgentes
- `POST /api/dashboard/ia/question` — Poser une question a l'IA

### Facturation
- `GET  /api/facturation/bc` — Liste bons de commande
- `POST /api/facturation/bc` — Creer un BC
- `POST /api/facturation/bc/{id}/convertir` — BC → Facture
- `GET  /api/facturation/factures` — Liste factures
- `POST /api/facturation/factures` — Creer une facture
- `POST /api/facturation/factures/{id}/regler` — Marquer reglee
- `POST /api/facturation/factures/{id}/relancer` — Relance IA
- `GET  /api/facturation/dashboard-recouvrement` — Impayes

### Paie
- `GET  /api/paie/employes` — Liste employes
- `POST /api/paie/employes` — Creer employe
- `POST /api/paie/bulletins/calculer` — Calculer bulletin (sans sauvegarder)
- `POST /api/paie/bulletins/valider` — Valider et sauvegarder bulletin
- `GET  /api/paie/bulletins/{annee}/{mois}` — Resume DSN du mois
