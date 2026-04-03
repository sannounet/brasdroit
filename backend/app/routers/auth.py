"""
Routes API — Authentification et gestion utilisateurs
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.models.models import User, Entreprise
from app.schemas.schemas import RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["Authentification"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """Création d'un compte + entreprise."""
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    
    # Créer l'entreprise
    entreprise = Entreprise(nom=data.entreprise_nom, siret=data.entreprise_siret)
    db.add(entreprise)
    db.flush()
    
    # Créer l'utilisateur admin
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        prenom=data.prenom,
        nom=data.nom,
        entreprise_id=entreprise.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        prenom=user.prenom,
        entreprise_id=entreprise.id,
        entreprise_nom=entreprise.nom,
    )


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Connexion et retour du token JWT."""
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")
    
    user.last_login = datetime.utcnow()
    db.commit()
    
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        prenom=user.prenom,
        entreprise_id=user.entreprise_id,
        entreprise_nom=user.entreprise.nom,
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    """Retourne l'utilisateur connecté."""
    return current_user
