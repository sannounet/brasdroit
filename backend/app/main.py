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
        # Compter les lignes par table
        counts = {}
        for t in tables:
            count = db.execute(text(f"SELECT COUNT(*) FROM {t[0]}")).scalar()
            counts[t[0]] = count
        # Foreign keys
        fks = db.execute(text("""
            SELECT tc.table_name, kcu.column_name, ccu.table_name AS foreign_table
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
            ORDER BY tc.table_name
        """)).fetchall()
        relations = [{"table": r[0], "column": r[1], "references": r[2]} for r in fks]
        db.close()
        return {"db": "ok", "tables": counts, "relations": relations}
    except Exception as e:
        return {"db": "error", "detail": str(e)}


@app.post("/debug/seed")
def run_seed(entreprise_id: int = 0):
    """Peuple la base avec des données de démo — À SUPPRIMER en production."""
    from sqlalchemy import text
    from app.core.database import SessionLocal
    from app.seed_demo import seed_demo
    db = SessionLocal()
    try:
        if entreprise_id == 0:
            row = db.execute(text("SELECT id, nom FROM entreprises LIMIT 1")).fetchone()
            if not row:
                return {"status": "error", "detail": "Aucune entreprise trouvée. Créez un compte d'abord."}
            entreprise_id = row[0]
        result = seed_demo(db, entreprise_id)
        return {"status": "ok", "entreprise_id": entreprise_id, "inserted": result}
    except Exception as e:
        db.rollback()
        return {"status": "error", "detail": str(e)}
    finally:
        db.close()
