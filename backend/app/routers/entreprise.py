"""
Routes API — Entreprise (infos entreprise du user connecte)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Entreprise

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
