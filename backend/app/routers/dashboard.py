"""
Routes API — Dashboard, Alertes, IA
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Facture, BulletinPaie, Declaration, MouvementBancaire, StatutFacture, StatutDeclaration
from app.schemas.schemas import DashboardStats, IAQuestion
from app.services.ia_service import question_ia

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard et IA"])


@router.get("/stats")
def get_stats(
    periode: Optional[str] = Query("mois", description="mois, semaine, trimestre"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Chiffres clés pour le tableau de bord."""
    eid = current_user.entreprise_id
    today = date.today()

    # Calculer les dates de début selon la période
    if periode == "semaine":
        debut = today - timedelta(days=today.weekday())
    elif periode == "trimestre":
        mois_trim = ((today.month - 1) // 3) * 3 + 1
        debut = today.replace(month=mois_trim, day=1)
    else:  # mois
        debut = today.replace(day=1)

    # CA période (factures réglées dans la période)
    ca = db.query(func.sum(Facture.montant_ht)).filter(
        Facture.entreprise_id == eid,
        Facture.statut == StatutFacture.reglee,
        Facture.date_paiement >= debut,
    ).scalar() or 0

    # Impayés (toujours total)
    impayes = db.query(func.sum(Facture.montant_ttc)).filter(
        Facture.entreprise_id == eid,
        Facture.statut.in_([StatutFacture.en_retard, StatutFacture.judiciaire]),
    ).scalar() or 0

    # Trésorerie
    tresorerie = db.query(func.sum(MouvementBancaire.montant)).filter(
        MouvementBancaire.entreprise_id == eid,
    ).scalar() or 0

    # Obligations de la période (déclarations à payer)
    obligations = db.query(func.sum(Declaration.montant)).filter(
        Declaration.entreprise_id == eid,
        Declaration.statut == StatutDeclaration.a_preparer,
        Declaration.date_echeance >= debut,
        Declaration.date_echeance <= debut + timedelta(days=90),
    ).scalar() or 0

    # Déclarations urgentes (< 7 jours)
    urgentes = db.query(Declaration).filter(
        Declaration.entreprise_id == eid,
        Declaration.statut == StatutDeclaration.a_preparer,
        Declaration.date_echeance <= today + timedelta(days=7),
    ).count()

    # Factures en retard
    nb_retard = db.query(func.count(Facture.id)).filter(
        Facture.entreprise_id == eid,
        Facture.statut == StatutFacture.en_retard,
    ).scalar() or 0

    # Score de santé simplifié
    score = 50
    if float(impayes) == 0:
        score += 20
    elif float(impayes) < 10000:
        score += 10
    if float(tresorerie) > 20000:
        score += 15
    elif float(tresorerie) > 0:
        score += 5
    if nb_retard == 0:
        score += 15
    elif nb_retard <= 2:
        score += 5

    return {
        "periode": periode,
        "debut": str(debut),
        "ca_mois": float(ca),
        "tresorerie": float(tresorerie),
        "impayes": float(impayes),
        "obligations_mois": float(obligations),
        "nb_alertes_urgentes": urgentes,
        "nb_factures_en_retard": nb_retard,
        "score_sante": min(score, 100),
    }


@router.get("/alertes")
def get_alertes(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Liste toutes les alertes urgentes et importantes."""
    eid = current_user.entreprise_id
    today = date.today()
    alertes = []

    # Factures en retard
    factures_retard = db.query(Facture).filter(
        Facture.entreprise_id == eid,
        Facture.statut == StatutFacture.en_retard,
    ).all()
    for f in factures_retard:
        jours = (today - f.date_echeance).days if f.date_echeance else 0
        alertes.append({
            "type": "IMPAYE",
            "severite": "urgent" if jours > 30 else "important",
            "titre": f"Impayé J+{jours} — {f.numero}",
            "montant": float(f.montant_ttc or 0),
            "action": f"/api/facturation/factures/{f.id}/relancer",
        })

    # Déclarations à venir
    declarations = db.query(Declaration).filter(
        Declaration.entreprise_id == eid,
        Declaration.statut == StatutDeclaration.a_preparer,
        Declaration.date_echeance >= today,
        Declaration.date_echeance <= today + timedelta(days=30),
    ).all()
    for d in declarations:
        jours_restants = (d.date_echeance - today).days
        alertes.append({
            "type": d.type_decl,
            "severite": "urgent" if jours_restants <= 3 else "important",
            "titre": f"{d.type_decl} — J-{jours_restants}",
            "montant": float(d.montant or 0),
            "echeance": str(d.date_echeance),
        })

    alertes.sort(key=lambda x: 0 if x["severite"] == "urgent" else 1)
    return {"alertes": alertes, "nb_urgentes": sum(1 for a in alertes if a["severite"] == "urgent")}


@router.post("/ia/question")
def poser_question_ia(data: IAQuestion, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Pose une question à l'IA avec le contexte financier de l'entreprise."""
    eid = current_user.entreprise_id

    impayes = db.query(func.sum(Facture.montant_ttc)).filter(
        Facture.entreprise_id == eid,
        Facture.statut.in_([StatutFacture.en_retard, StatutFacture.judiciaire]),
    ).scalar() or 0

    contexte = {
        "entreprise_id": eid,
        "impayes_total": float(impayes),
        "contexte_utilisateur": data.contexte or "",
    }

    reponse = question_ia(data.question, contexte)
    return {"reponse": reponse, "question": data.question}
