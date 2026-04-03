"""
Bras Droit — API principale FastAPI
Point d'entrée : uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base

# Import des modèles pour création des tables
from app.models import models  # noqa

# Import des routers
from app.routers import auth, facturation, paie, dashboard

# ── Création des tables PostgreSQL ──
Base.metadata.create_all(bind=engine)

# ── Application FastAPI ──
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Backend complet de Bras Droit — Gestion integree pour PME françaises",
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",
)

# ── CORS — autorise Vercel et localhost ──
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Enregistrement des routers ──
app.include_router(auth.router)
app.include_router(facturation.router)
app.include_router(paie.router)
app.include_router(dashboard.router)


# ── Routes de base ──
@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "OK",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    """Endpoint de santé pour Render."""
    return {"status": "healthy"}


@app.get("/debug/db")
def debug_db():
    """Vérifie la connexion DB — À SUPPRIMER en production."""
    from sqlalchemy import text
    from app.core.database import SessionLocal
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        tables = db.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        )).fetchall()
        db.close()
        return {"db": "ok", "tables": [t[0] for t in tables]}
    except Exception as e:
        return {"db": "error", "detail": str(e)}


@app.post("/debug/seed")
def run_seed(entreprise_id: int = 1):
    """Peuple la base avec des données de démo — À SUPPRIMER en production."""
    from app.core.database import SessionLocal
    from app.seed_demo import seed_demo
    db = SessionLocal()
    try:
        result = seed_demo(db, entreprise_id)
        return {"status": "ok", "inserted": result}
    except Exception as e:
        db.rollback()
        return {"status": "error", "detail": str(e)}
    finally:
        db.close()
