"""
Routes API — Dashboard, Alertes, IA
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Facture, BulletinPaie, Declaration, MouvementBancaire, StatutFacture, StatutDeclaration
from app.schemas.schemas import DashboardStats, IAQuestion
from app.services.ia_service import question_ia

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard et IA"])


@router.get("/stats", response_model=DashboardStats)
def get_stats(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Chiffres clés pour le tableau de bord."""
    eid = current_user.entreprise_id
    today = date.today()
    debut_mois = today.replace(day=1)

    # CA ce mois (factures réglées ce mois)
    ca_mois = db.query(func.sum(Facture.montant_ht)).filter(
        Facture.entreprise_id == eid,
        Facture.statut == StatutFacture.reglee,
        Facture.date_paiement >= debut_mois
    ).scalar() or 0

    # Impayés
    impayes = db.query(func.sum(Facture.montant_ttc)).filter(
        Facture.entreprise_id == eid,
        Facture.statut.in_([StatutFacture.en_retard, StatutFacture.judiciaire])
    ).scalar() or 0

    # Trésorerie (derniers mouvements bancaires)
    dernier_solde = db.query(func.sum(MouvementBancaire.montant)).filter(
        MouvementBancaire.entreprise_id == eid
    ).scalar() or 0

    # Déclarations urgentes (< 7 jours)
    urgentes = db.query(Declaration).filter(
        Declaration.entreprise_id == eid,
        Declaration.statut == StatutDeclaration.a_preparer,
        Declaration.date_echeance <= today + timedelta(days=7)
    ).count()

    # Factures en retard
    nb_retard = db.query(func.count(Facture.id)).filter(
        Facture.entreprise_id == eid,
        Facture.statut == StatutFacture.en_retard
    ).scalar() or 0

    return DashboardStats(
        ca_mois=float(ca_mois),
        tresorerie=float(dernier_solde),
        impayes=float(impayes),
        obligations_mois=0.0,
        nb_alertes_urgentes=urgentes,
        nb_factures_en_retard=nb_retard,
        score_sante=72,  # À calculer dynamiquement
    )


@router.get("/alertes")
def get_alertes(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Liste toutes les alertes urgentes et importantes."""
    eid = current_user.entreprise_id
    today = date.today()
    alertes = []

    # Factures en retard
    factures_retard = db.query(Facture).filter(
        Facture.entreprise_id == eid,
        Facture.statut == StatutFacture.en_retard
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
        Declaration.date_echeance <= today + timedelta(days=30)
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

    # Construire le contexte
    impayes = db.query(func.sum(Facture.montant_ttc)).filter(
        Facture.entreprise_id == eid,
        Facture.statut.in_([StatutFacture.en_retard, StatutFacture.judiciaire])
    ).scalar() or 0

    contexte = {
        "entreprise_id": eid,
        "impayes_total": float(impayes),
        "contexte_utilisateur": data.contexte or "",
    }

    reponse = question_ia(data.question, contexte)
    return {"reponse": reponse, "question": data.question}
