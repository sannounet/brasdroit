"""
Routes API — Entreprise (infos entreprise du user connecte)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user, hash_password, verify_password
from app.models.models import Entreprise, User

router = APIRouter(prefix="/api/entreprise", tags=["Entreprise"])


class EntrepriseOut(BaseModel):
    id: int
    nom: str
    siret: Optional[str] = None
    siren: Optional[str] = None
    tva_intra: Optional[str] = None
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    forme_juridique: Optional[str] = None
    capital: Optional[float] = None
    convention_collective: Optional[str] = None
    code_ape: Optional[str] = None
    taux_tva_defaut: Optional[float] = None

    class Config:
        from_attributes = True


class EntrepriseUpdate(BaseModel):
    nom: Optional[str] = None
    siret: Optional[str] = None
    siren: Optional[str] = None
    tva_intra: Optional[str] = None
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    forme_juridique: Optional[str] = None
    capital: Optional[float] = None
    convention_collective: Optional[str] = None
    code_ape: Optional[str] = None
    taux_tva_defaut: Optional[float] = None


@router.get("", response_model=EntrepriseOut)
def get_entreprise(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Retourne les informations de l'entreprise du user connecte."""
    ent = db.query(Entreprise).filter(Entreprise.id == current_user.entreprise_id).first()
    if not ent:
        raise HTTPException(404, "Entreprise introuvable")
    return ent


@router.patch("", response_model=EntrepriseOut)
def update_entreprise(
    data: EntrepriseUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Met a jour les informations de l'entreprise."""
    ent = db.query(Entreprise).filter(Entreprise.id == current_user.entreprise_id).first()
    if not ent:
        raise HTTPException(404, "Entreprise introuvable")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ent, field, value)

    db.commit()
    db.refresh(ent)
    return ent


# ─── PROFIL UTILISATEUR ───

class ProfilOut(BaseModel):
    id: int
    email: str
    prenom: Optional[str] = None
    nom: Optional[str] = None
    role: Optional[str] = None
    entreprise_id: int
    entreprise_nom: Optional[str] = None
    class Config:
        from_attributes = True

class ProfilUpdate(BaseModel):
    prenom: Optional[str] = None
    nom: Optional[str] = None
    email: Optional[str] = None

class PasswordChange(BaseModel):
    ancien_mdp: str
    nouveau_mdp: str


@router.get("/profil")
def get_profil(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    ent = db.query(Entreprise).filter(Entreprise.id == current_user.entreprise_id).first()
    return {
        "id": current_user.id,
        "email": current_user.email,
        "prenom": current_user.prenom,
        "nom": current_user.nom,
        "role": current_user.role.value if current_user.role else "admin",
        "entreprise_id": current_user.entreprise_id,
        "entreprise_nom": ent.nom if ent else "",
    }


@router.patch("/profil")
def update_profil(data: ProfilUpdate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return {"status": "ok"}


@router.post("/profil/password")
def change_password(data: PasswordChange, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(data.ancien_mdp[:72], current_user.hashed_password):
        raise HTTPException(400, "Ancien mot de passe incorrect")
    if len(data.nouveau_mdp) < 8:
        raise HTTPException(400, "Le nouveau mot de passe doit faire au moins 8 caractères")
    current_user.hashed_password = hash_password(data.nouveau_mdp[:72])
    db.commit()
    return {"status": "ok"}


# ─── EXERCICES DISPONIBLES ───

@router.get("/exercices")
def get_exercices(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Retourne les exercices disponibles basés sur les données existantes."""
    from sqlalchemy import func, distinct, extract
    from app.models.models import Facture, Ecriture, MouvementBancaire

    eid = current_user.entreprise_id
    annees = set()

    for model, col in [(Facture, Facture.date_facture), (Ecriture, Ecriture.date_ecriture), (MouvementBancaire, MouvementBancaire.date_operation)]:
        rows = db.query(distinct(extract("year", col))).filter(
            model.entreprise_id == eid
        ).all()
        for r in rows:
            if r[0]:
                annees.add(int(r[0]))

    return {"exercices": sorted(annees, reverse=True)}
