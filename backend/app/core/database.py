from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # Vérifie la connexion avant chaque requête
    pool_size=5,              # Adapté au plan gratuit Render
    max_overflow=5,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency injection — fournit une session DB par requête."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
