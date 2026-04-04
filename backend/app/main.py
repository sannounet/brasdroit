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
from app.routers import auth, facturation, paie, dashboard, comptabilite, tresorerie, declarations, entreprise

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
app.include_router(comptabilite.router)
app.include_router(tresorerie.router)
app.include_router(declarations.router)
app.include_router(entreprise.router)


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


