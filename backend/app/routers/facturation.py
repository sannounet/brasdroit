"""
Routes API — Facturation (Bons de commande + Factures + Recouvrement)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from decimal import Decimal
from typing import List

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Facture, BonCommande, Client, Relance, StatutFacture, StatutBC
from app.schemas.schemas import FactureCreate, FactureOut, BCCreate, BCOut
from app.services.ia_service import generer_relance

router = APIRouter(prefix="/api/facturation", tags=["Facturation"])


@router.get("/clients")
def list_clients(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Liste des clients de l'entreprise."""
    clients = db.query(Client).filter(
        Client.entreprise_id == current_user.entreprise_id,
        Client.is_active == True,
    ).order_by(Client.nom).all()
    return [{
        "id": c.id, "nom": c.nom, "siret": c.siret, "email": c.email,
        "adresse": c.adresse, "code_postal": c.code_postal, "ville": c.ville,
        "delai_paiement": c.delai_paiement,
    } for c in clients]


def next_numero_facture(db: Session, entreprise_id: int) -> str:
    """Génère le prochain numéro de facture FA-2026-XXX."""
    annee = date.today().year
    count = db.query(func.count(Facture.id)).filter(
        Facture.entreprise_id == entreprise_id,
        func.extract("year", Facture.date_facture) == annee
    ).scalar()
    return f"FA-{annee}-{str(count + 1).zfill(3)}"


def next_numero_bc(db: Session, entreprise_id: int) -> str:
    annee = date.today().year
    count = db.query(func.count(BonCommande.id)).filter(
        BonCommande.entreprise_id == entreprise_id,
        func.extract("year", BonCommande.date_bc) == annee
    ).scalar()
    return f"BC-{annee}-{str(count + 1).zfill(3)}"


# ─── BONS DE COMMANDE ───

@router.get("/bc", response_model=List[BCOut])
def list_bc(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(BonCommande).filter(
        BonCommande.entreprise_id == current_user.entreprise_id
    ).order_by(BonCommande.id.desc()).all()


@router.post("/bc", response_model=BCOut, status_code=201)
def create_bc(data: BCCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    tva = Decimal(str(data.montant_ht)) * Decimal(str(data.taux_tva)) / 100
    bc = BonCommande(
        entreprise_id=current_user.entreprise_id,
        client_id=data.client_id,
        numero=next_numero_bc(db, current_user.entreprise_id),
        date_bc=data.date_bc,
        objet=data.objet,
        montant_ht=data.montant_ht,
        taux_tva=data.taux_tva,
        montant_tva=tva,
        montant_ttc=data.montant_ht + tva,
        statut=StatutBC.valide,
    )
    db.add(bc)
    db.commit()
    db.refresh(bc)
    return bc


@router.post("/bc/{bc_id}/convertir", response_model=FactureOut)
def convertir_bc_en_facture(bc_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Convertit un BC validé en facture en 1 clic."""
    bc = db.query(BonCommande).filter(
        BonCommande.id == bc_id,
        BonCommande.entreprise_id == current_user.entreprise_id
    ).first()
    if not bc:
        raise HTTPException(404, "Bon de commande introuvable")
    if bc.statut == StatutBC.converti:
        raise HTTPException(400, "Ce BC est déjà converti en facture")
    
    client = db.query(Client).filter(Client.id == bc.client_id).first()
    delai = client.delai_paiement if client else 30
    
    facture = Facture(
        entreprise_id=current_user.entreprise_id,
        client_id=bc.client_id,
        numero=next_numero_facture(db, current_user.entreprise_id),
        bc_origine=bc.numero,
        date_facture=date.today(),
        date_echeance=date.today() + timedelta(days=delai),
        objet=bc.objet,
        montant_ht=bc.montant_ht,
        taux_tva=bc.taux_tva,
        montant_tva=bc.montant_tva,
        montant_ttc=bc.montant_ttc,
        statut=StatutFacture.emise,
    )
    db.add(facture)
    bc.statut = StatutBC.converti
    bc.facture_id = facture.id
    db.commit()
    db.refresh(facture)
    return facture


# ─── FACTURES ───

@router.get("/factures", response_model=List[FactureOut])
def list_factures(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    factures = db.query(Facture).filter(
        Facture.entreprise_id == current_user.entreprise_id
    ).order_by(Facture.id.desc()).all()
    
    # Mise à jour automatique des statuts
    today = date.today()
    for f in factures:
        if f.statut in [StatutFacture.emise, StatutFacture.envoyee, StatutFacture.en_attente]:
            if f.date_echeance < today:
                f.statut = StatutFacture.en_retard
    db.commit()
    return factures


@router.post("/factures", response_model=FactureOut, status_code=201)
def create_facture(data: FactureCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    tva = data.montant_ht * Decimal(str(data.taux_tva)) / 100
    facture = Facture(
        entreprise_id=current_user.entreprise_id,
        client_id=data.client_id,
        numero=next_numero_facture(db, current_user.entreprise_id),
        bc_origine=data.bc_origine,
        date_facture=data.date_facture,
        date_echeance=data.date_echeance,
        objet=data.objet,
        montant_ht=data.montant_ht,
        taux_tva=data.taux_tva,
        montant_tva=tva,
        montant_ttc=data.montant_ht + tva,
        statut=StatutFacture.emise,
    )
    db.add(facture)
    db.commit()
    db.refresh(facture)
    return facture


@router.post("/factures/{facture_id}/regler")
def regler_facture(facture_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    f = db.query(Facture).filter(
        Facture.id == facture_id,
        Facture.entreprise_id == current_user.entreprise_id
    ).first()
    if not f:
        raise HTTPException(404, "Facture introuvable")
    f.statut = StatutFacture.reglee
    f.date_paiement = date.today()
    db.commit()
    return {"message": "Facture marquée comme réglée", "facture": f.numero}


# ─── RECOUVREMENT ───

@router.post("/factures/{facture_id}/relancer")
def envoyer_relance(
    facture_id: int,
    type_relance: str = "R1",
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Génère et enregistre une relance IA."""
    f = db.query(Facture).filter(
        Facture.id == facture_id,
        Facture.entreprise_id == current_user.entreprise_id
    ).first()
    if not f:
        raise HTTPException(404, "Facture introuvable")
    
    client = db.query(Client).filter(Client.id == f.client_id).first()
    jours_retard = (date.today() - f.date_echeance).days if f.date_echeance < date.today() else 0
    
    # Génération IA
    mail = generer_relance(
        client_nom=client.nom if client else "Client",
        facture_numero=f.numero,
        montant=float(f.montant_ttc or 0),
        date_echeance=str(f.date_echeance),
        jours_retard=jours_retard,
        type_relance=type_relance,
    )
    
    # Enregistrer la relance
    relance = Relance(
        facture_id=f.id,
        type_relance=type_relance,
        objet=mail.get("objet", ""),
        corps=mail.get("corps", ""),
    )
    db.add(relance)
    f.nb_relances += 1
    f.date_derniere_relance = date.today()
    
    # Migration judiciaire après 3 relances
    if f.nb_relances >= 3:
        f.phase_judiciaire = True
        f.statut = StatutFacture.judiciaire
    
    db.commit()
    return {"relance": mail, "nb_relances_total": f.nb_relances}


# ─── JUDICIAIRE ───

@router.get("/judiciaire")
def dossiers_judiciaires(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Liste des factures en phase judiciaire avec relances et interets."""
    from sqlalchemy.orm import joinedload

    factures = db.query(Facture).options(joinedload(Facture.relances)).filter(
        Facture.entreprise_id == current_user.entreprise_id,
        (Facture.statut == StatutFacture.judiciaire) | (Facture.phase_judiciaire == True),
    ).order_by(Facture.id.desc()).all()

    today = date.today()
    result = []
    total_principal = 0
    total_interets = 0

    for f in factures:
        client = db.query(Client).filter(Client.id == f.client_id).first()
        jours_retard = (today - f.date_echeance).days if f.date_echeance and f.date_echeance < today else 0
        montant = float(f.montant_ttc or 0)
        interets = round(montant * 0.02, 2)
        total_principal += montant
        total_interets += interets

        relances_list = [
            {
                "id": r.id,
                "type_relance": r.type_relance,
                "date_envoi": str(r.date_envoi) if r.date_envoi else None,
                "objet": r.objet,
                "corps": r.corps,
                "mail_lu": r.mail_lu,
            }
            for r in f.relances
        ]

        result.append({
            "facture_id": f.id,
            "numero": f.numero,
            "client": client.nom if client else "—",
            "client_email": client.email if client else None,
            "objet": f.objet,
            "date_facture": str(f.date_facture),
            "date_echeance": str(f.date_echeance),
            "montant_ttc": montant,
            "jours_retard": jours_retard,
            "nb_relances": f.nb_relances,
            "interets": interets,
            "total_du": round(montant + interets, 2),
            "relances": relances_list,
        })

    return {
        "dossiers": result,
        "nb_dossiers": len(result),
        "total_principal": round(total_principal, 2),
        "total_interets": round(total_interets, 2),
        "total_global": round(total_principal + total_interets, 2),
    }


@router.get("/dashboard-recouvrement")
def dashboard_recouvrement(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Résumé des impayés avec calcul des jours de retard."""
    today = date.today()
    factures_retard = db.query(Facture).filter(
        Facture.entreprise_id == current_user.entreprise_id,
        Facture.statut.in_([StatutFacture.en_retard, StatutFacture.judiciaire])
    ).all()
    
    result = []
    total_impayes = 0
    for f in factures_retard:
        jours = (today - f.date_echeance).days if f.date_echeance else 0
        client = db.query(Client).filter(Client.id == f.client_id).first()
        total_impayes += float(f.montant_ttc or 0)
        result.append({
            "facture": f.numero,
            "client": client.nom if client else "—",
            "montant_ttc": float(f.montant_ttc or 0),
            "jours_retard": jours,
            "nb_relances": f.nb_relances,
            "statut": f.statut,
            "judiciaire": f.phase_judiciaire,
        })
    
    return {"dossiers": result, "total_impayes": total_impayes, "nb_dossiers": len(result)}
