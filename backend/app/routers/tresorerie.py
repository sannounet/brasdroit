"""
Routes API — Trésorerie (Mouvements bancaires, Solde, Relevés, Charges, Prévisions)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import date
from decimal import Decimal
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import MouvementBancaire

router = APIRouter(prefix="/api/tresorerie", tags=["Trésorerie"])


# ─── MOUVEMENTS BANCAIRES ───

@router.get("/mouvements")
def list_mouvements(
    annee: Optional[int] = None,
    mois: Optional[int] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Liste des mouvements bancaires, filtrable par année et mois."""
    q = db.query(MouvementBancaire).filter(
        MouvementBancaire.entreprise_id == current_user.entreprise_id
    )
    if annee:
        q = q.filter(extract("year", MouvementBancaire.date_operation) == annee)
    if mois:
        q = q.filter(extract("month", MouvementBancaire.date_operation) == mois)
    return q.order_by(MouvementBancaire.date_operation.desc()).all()


# ─── SOLDE ───

@router.get("/solde")
def get_solde(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Solde actuel + encaissements et décaissements du mois en cours."""
    eid = current_user.entreprise_id
    today = date.today()

    # Solde global = somme de tous les montants
    solde = db.query(func.coalesce(func.sum(MouvementBancaire.montant), 0)).filter(
        MouvementBancaire.entreprise_id == eid
    ).scalar()

    # Mouvements du mois en cours
    mois_filter = [
        MouvementBancaire.entreprise_id == eid,
        extract("year", MouvementBancaire.date_operation) == today.year,
        extract("month", MouvementBancaire.date_operation) == today.month,
    ]

    encaissements = db.query(func.coalesce(func.sum(MouvementBancaire.montant), 0)).filter(
        *mois_filter, MouvementBancaire.montant > 0
    ).scalar()

    decaissements = db.query(func.coalesce(func.sum(MouvementBancaire.montant), 0)).filter(
        *mois_filter, MouvementBancaire.montant < 0
    ).scalar()

    return {
        "solde": float(solde),
        "encaissements_mois": float(encaissements),
        "decaissements_mois": float(decaissements),
        "mois": today.month,
        "annee": today.year,
    }


# ─── RELEVÉ MENSUEL ───

@router.get("/releves")
def releve_mensuel(
    annee: int = Query(...),
    mois: int = Query(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Relevé bancaire mensuel : mouvements + solde d'ouverture / clôture."""
    eid = current_user.entreprise_id

    # Solde d'ouverture = somme de tous les mouvements avant le mois demandé
    solde_ouverture = db.query(func.coalesce(func.sum(MouvementBancaire.montant), 0)).filter(
        MouvementBancaire.entreprise_id == eid,
        MouvementBancaire.date_operation < date(annee, mois, 1),
    ).scalar()

    # Mouvements du mois
    mouvements = db.query(MouvementBancaire).filter(
        MouvementBancaire.entreprise_id == eid,
        extract("year", MouvementBancaire.date_operation) == annee,
        extract("month", MouvementBancaire.date_operation) == mois,
    ).order_by(MouvementBancaire.date_operation).all()

    total_mois = sum(float(m.montant or 0) for m in mouvements)
    solde_cloture = float(solde_ouverture) + total_mois

    return {
        "annee": annee,
        "mois": mois,
        "solde_ouverture": float(solde_ouverture),
        "solde_cloture": solde_cloture,
        "nb_mouvements": len(mouvements),
        "mouvements": mouvements,
    }


# ─── CHARGES ANNUELLES ───

@router.get("/charges")
def charges_annuelles(
    annee: int = Query(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ventilation des charges (mouvements négatifs) par catégorie pour l'année."""
    eid = current_user.entreprise_id

    rows = db.query(
        MouvementBancaire.categorie,
        func.sum(MouvementBancaire.montant).label("total"),
        func.count(MouvementBancaire.id).label("nb"),
    ).filter(
        MouvementBancaire.entreprise_id == eid,
        extract("year", MouvementBancaire.date_operation) == annee,
        MouvementBancaire.montant < 0,
    ).group_by(MouvementBancaire.categorie).all()

    charges = [
        {"categorie": r.categorie or "Non catégorisé", "total": float(r.total), "nb_operations": r.nb}
        for r in rows
    ]
    total_charges = sum(c["total"] for c in charges)

    return {
        "annee": annee,
        "total_charges": total_charges,
        "categories": charges,
    }


# ─── PRÉVISION DE TRÉSORERIE ───

@router.get("/prevision")
def prevision_tresorerie(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Prévision de trésorerie sur 12 mois basée sur les moyennes mensuelles."""
    eid = current_user.entreprise_id
    today = date.today()

    # Solde actuel
    solde = db.query(func.coalesce(func.sum(MouvementBancaire.montant), 0)).filter(
        MouvementBancaire.entreprise_id == eid
    ).scalar()
    solde = float(solde)

    # Moyenne mensuelle des encaissements et décaissements (sur les 12 derniers mois)
    date_debut = date(today.year - 1, today.month, 1)

    avg_encaissements = db.query(func.coalesce(func.avg(MouvementBancaire.montant), 0)).filter(
        MouvementBancaire.entreprise_id == eid,
        MouvementBancaire.date_operation >= date_debut,
        MouvementBancaire.montant > 0,
    ).scalar()

    avg_decaissements = db.query(func.coalesce(func.avg(MouvementBancaire.montant), 0)).filter(
        MouvementBancaire.entreprise_id == eid,
        MouvementBancaire.date_operation >= date_debut,
        MouvementBancaire.montant < 0,
    ).scalar()

    # Nombre de mois avec des mouvements pour calculer la moyenne mensuelle
    nb_mois = db.query(
        func.count(func.distinct(
            func.concat(
                extract("year", MouvementBancaire.date_operation), "-",
                extract("month", MouvementBancaire.date_operation),
            )
        ))
    ).filter(
        MouvementBancaire.entreprise_id == eid,
        MouvementBancaire.date_operation >= date_debut,
    ).scalar() or 1

    total_enc = db.query(func.coalesce(func.sum(MouvementBancaire.montant), 0)).filter(
        MouvementBancaire.entreprise_id == eid,
        MouvementBancaire.date_operation >= date_debut,
        MouvementBancaire.montant > 0,
    ).scalar()

    total_dec = db.query(func.coalesce(func.sum(MouvementBancaire.montant), 0)).filter(
        MouvementBancaire.entreprise_id == eid,
        MouvementBancaire.date_operation >= date_debut,
        MouvementBancaire.montant < 0,
    ).scalar()

    moy_enc = float(total_enc) / nb_mois
    moy_dec = float(total_dec) / nb_mois
    flux_net_mensuel = moy_enc + moy_dec  # moy_dec is negative

    # Projection sur 12 mois
    previsions = []
    solde_courant = solde
    mois = today.month
    annee = today.year
    for i in range(1, 13):
        mois += 1
        if mois > 12:
            mois = 1
            annee += 1
        solde_courant += flux_net_mensuel
        previsions.append({
            "mois": mois,
            "annee": annee,
            "encaissements_prevus": round(moy_enc, 2),
            "decaissements_prevus": round(moy_dec, 2),
            "solde_prevu": round(solde_courant, 2),
        })

    return {
        "solde_actuel": solde,
        "moyenne_encaissements_mensuels": round(moy_enc, 2),
        "moyenne_decaissements_mensuels": round(moy_dec, 2),
        "flux_net_mensuel": round(flux_net_mensuel, 2),
        "previsions": previsions,
    }
