"""
Routes API — Comptabilite (ecritures, bilan, resultat, ratios, lettrage)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Optional
from decimal import Decimal

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    Ecriture, CompteComptable, Facture, MouvementBancaire,
    StatutFacture,
)

router = APIRouter(prefix="/api/compta", tags=["Comptabilite"])


# ─── ECRITURES ───

@router.get("/ecritures")
def list_ecritures(
    annee: Optional[int] = None,
    mois: Optional[int] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Liste des ecritures comptables, filtrable par annee/mois."""
    q = db.query(Ecriture).filter(
        Ecriture.entreprise_id == current_user.entreprise_id
    )
    if annee:
        q = q.filter(extract("year", Ecriture.date_ecriture) == annee)
    if mois:
        q = q.filter(extract("month", Ecriture.date_ecriture) == mois)
    return q.order_by(Ecriture.date_ecriture.desc()).all()


# ─── COMPTES COMPTABLES ───

@router.get("/comptes")
def list_comptes(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Liste des comptes comptables de l'entreprise."""
    return db.query(CompteComptable).filter(
        CompteComptable.entreprise_id == current_user.entreprise_id
    ).order_by(CompteComptable.numero).all()


# ─── BILAN ───

@router.get("/bilan")
def bilan(
    annee: int = Query(..., description="Annee de l'exercice"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bilan simplifie : actif (debits classes 1-5) et passif (credits classes 1-5)."""
    eid = current_user.entreprise_id

    ecritures = db.query(Ecriture).filter(
        Ecriture.entreprise_id == eid,
        extract("year", Ecriture.date_ecriture) == annee,
    ).all()

    actif: dict[int, float] = {}   # classe -> total debit
    passif: dict[int, float] = {}  # classe -> total credit

    # Charger la correspondance numero compte -> classe
    comptes = db.query(CompteComptable).filter(
        CompteComptable.entreprise_id == eid
    ).all()
    compte_classe = {c.numero: c.classe for c in comptes}

    for e in ecritures:
        montant = float(e.montant or 0)

        # Cote debit
        classe_d = compte_classe.get(e.compte_debit) or _classe_from_numero(e.compte_debit)
        if classe_d and 1 <= classe_d <= 5:
            actif[classe_d] = actif.get(classe_d, 0) + montant

        # Cote credit
        classe_c = compte_classe.get(e.compte_credit) or _classe_from_numero(e.compte_credit)
        if classe_c and 1 <= classe_c <= 5:
            passif[classe_c] = passif.get(classe_c, 0) + montant

    return {
        "annee": annee,
        "actif": actif,
        "passif": passif,
        "total_actif": sum(actif.values()),
        "total_passif": sum(passif.values()),
    }


# ─── COMPTE DE RESULTAT ───

@router.get("/resultat")
def resultat(
    annee: int = Query(..., description="Annee de l'exercice"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compte de resultat simplifie : charges (classe 6) et produits (classe 7)."""
    eid = current_user.entreprise_id

    ecritures = db.query(Ecriture).filter(
        Ecriture.entreprise_id == eid,
        extract("year", Ecriture.date_ecriture) == annee,
    ).all()

    comptes = db.query(CompteComptable).filter(
        CompteComptable.entreprise_id == eid
    ).all()
    compte_classe = {c.numero: c.classe for c in comptes}

    charges = 0.0
    produits = 0.0

    for e in ecritures:
        montant = float(e.montant or 0)

        classe_d = compte_classe.get(e.compte_debit) or _classe_from_numero(e.compte_debit)
        classe_c = compte_classe.get(e.compte_credit) or _classe_from_numero(e.compte_credit)

        # Charges = debits en classe 6
        if classe_d == 6:
            charges += montant
        # Produits = credits en classe 7
        if classe_c == 7:
            produits += montant

    resultat_net = produits - charges

    return {
        "annee": annee,
        "charges": round(charges, 2),
        "produits": round(produits, 2),
        "resultat_net": round(resultat_net, 2),
    }


# ─── RATIOS ───

@router.get("/ratios")
def ratios(
    annee: int = Query(..., description="Annee de l'exercice"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ratios financiers cles."""
    eid = current_user.entreprise_id

    ecritures = db.query(Ecriture).filter(
        Ecriture.entreprise_id == eid,
        extract("year", Ecriture.date_ecriture) == annee,
    ).all()

    comptes = db.query(CompteComptable).filter(
        CompteComptable.entreprise_id == eid
    ).all()
    compte_classe = {c.numero: c.classe for c in comptes}

    charges = 0.0
    produits = 0.0
    achats = 0.0      # comptes 60x
    dettes = 0.0      # classe 4 credit (fournisseurs, fiscal, social)
    capitaux = 0.0    # classe 1 credit (capitaux propres)
    creances = 0.0    # classe 4 debit (clients)

    for e in ecritures:
        montant = float(e.montant or 0)
        classe_d = compte_classe.get(e.compte_debit) or _classe_from_numero(e.compte_debit)
        classe_c = compte_classe.get(e.compte_credit) or _classe_from_numero(e.compte_credit)

        if classe_d == 6:
            charges += montant
            if e.compte_debit.startswith("60"):
                achats += montant
        if classe_c == 7:
            produits += montant

        # Creances clients (debit classe 4)
        if classe_d == 4:
            creances += montant
        # Dettes (credit classe 4)
        if classe_c == 4:
            dettes += montant
        # Capitaux propres (credit classe 1)
        if classe_c == 1:
            capitaux += montant

    # CA depuis factures reglees
    ca = db.query(func.coalesce(func.sum(Facture.montant_ht), 0)).filter(
        Facture.entreprise_id == eid,
        extract("year", Facture.date_facture) == annee,
        Facture.statut == StatutFacture.reglee,
    ).scalar()
    ca = float(ca)

    marge_brute = ((produits - achats) / produits * 100) if produits else 0
    rentabilite = ((produits - charges) / produits * 100) if produits else 0
    dso = (creances / ca * 360) if ca else 0
    ratio_endettement = (dettes / capitaux) if capitaux else 0

    return {
        "annee": annee,
        "marge_brute_pct": round(marge_brute, 2),
        "rentabilite_nette_pct": round(rentabilite, 2),
        "dso_jours": round(dso, 1),
        "ratio_endettement": round(ratio_endettement, 2),
        "details": {
            "produits": round(produits, 2),
            "charges": round(charges, 2),
            "achats": round(achats, 2),
            "ca_facture": round(ca, 2),
            "creances": round(creances, 2),
            "dettes": round(dettes, 2),
            "capitaux_propres": round(capitaux, 2),
        },
    }


# ─── LETTRAGE ───

@router.get("/lettrage")
def lettrage(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ecritures et mouvements bancaires cote a cote pour rapprochement."""
    eid = current_user.entreprise_id

    ecritures = db.query(Ecriture).filter(
        Ecriture.entreprise_id == eid
    ).order_by(Ecriture.date_ecriture.desc()).all()

    mouvements = db.query(MouvementBancaire).filter(
        MouvementBancaire.entreprise_id == eid
    ).order_by(MouvementBancaire.date_operation.desc()).all()

    return {
        "ecritures": [
            {
                "id": e.id,
                "date": str(e.date_ecriture),
                "numero_piece": e.numero_piece,
                "compte_debit": e.compte_debit,
                "compte_credit": e.compte_credit,
                "libelle": e.libelle,
                "montant": float(e.montant or 0),
                "lettre": e.lettre,
                "is_lettree": e.is_lettree,
            }
            for e in ecritures
        ],
        "mouvements_bancaires": [
            {
                "id": m.id,
                "date": str(m.date_operation),
                "libelle": m.libelle,
                "montant": float(m.montant or 0),
                "categorie": m.categorie,
                "compte_comptable": m.compte_comptable,
                "lettre": m.lettre,
                "is_lettree": m.is_lettree,
                "source": m.source,
            }
            for m in mouvements
        ],
    }


# ─── HELPERS ───

def _classe_from_numero(numero: str) -> Optional[int]:
    """Deduit la classe comptable du premier chiffre du numero de compte."""
    if numero and numero[0].isdigit():
        return int(numero[0])
    return None
