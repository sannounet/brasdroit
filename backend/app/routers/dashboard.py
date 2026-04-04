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


@router.post("/rapport")
def generer_rapport(
    type_rapport: str = Query("reduit", description="reduit ou complet"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Génère un rapport de gestion via Claude IA."""
    from app.models.models import Entreprise, Employe
    eid = current_user.entreprise_id
    today = date.today()
    debut_mois = today.replace(day=1)

    # Collecter toutes les données
    entreprise = db.query(Entreprise).filter(Entreprise.id == eid).first()
    ca_mois = float(db.query(func.sum(Facture.montant_ht)).filter(
        Facture.entreprise_id == eid, Facture.statut == StatutFacture.reglee,
        Facture.date_paiement >= debut_mois,
    ).scalar() or 0)
    ca_annee = float(db.query(func.sum(Facture.montant_ht)).filter(
        Facture.entreprise_id == eid, Facture.statut == StatutFacture.reglee,
        Facture.date_paiement >= date(today.year, 1, 1),
    ).scalar() or 0)
    tresorerie = float(db.query(func.sum(MouvementBancaire.montant)).filter(
        MouvementBancaire.entreprise_id == eid,
    ).scalar() or 0)
    impayes = float(db.query(func.sum(Facture.montant_ttc)).filter(
        Facture.entreprise_id == eid,
        Facture.statut.in_([StatutFacture.en_retard, StatutFacture.judiciaire]),
    ).scalar() or 0)
    nb_retard = db.query(func.count(Facture.id)).filter(
        Facture.entreprise_id == eid, Facture.statut == StatutFacture.en_retard,
    ).scalar() or 0
    nb_employes = db.query(func.count(Employe.id)).filter(
        Employe.entreprise_id == eid, Employe.is_active == True,
    ).scalar() or 0
    masse_salariale = float(db.query(func.sum(BulletinPaie.salaire_brut)).filter(
        BulletinPaie.entreprise_id == eid,
        BulletinPaie.annee == today.year,
    ).scalar() or 0)
    nb_factures_total = db.query(func.count(Facture.id)).filter(
        Facture.entreprise_id == eid,
    ).scalar() or 0
    nb_factures_reglees = db.query(func.count(Facture.id)).filter(
        Facture.entreprise_id == eid, Facture.statut == StatutFacture.reglee,
    ).scalar() or 0
    declarations_a_preparer = db.query(Declaration).filter(
        Declaration.entreprise_id == eid,
        Declaration.statut == StatutDeclaration.a_preparer,
    ).count()

    donnees = {
        "entreprise": entreprise.nom if entreprise else "",
        "siret": entreprise.siret if entreprise else "",
        "date_rapport": str(today),
        "ca_mois": ca_mois,
        "ca_annee": ca_annee,
        "tresorerie": tresorerie,
        "impayes": impayes,
        "nb_factures_en_retard": nb_retard,
        "nb_employes": nb_employes,
        "masse_salariale_ytd": masse_salariale,
        "nb_factures_total": nb_factures_total,
        "nb_factures_reglees": nb_factures_reglees,
        "taux_recouvrement": round(nb_factures_reglees / nb_factures_total * 100, 1) if nb_factures_total > 0 else 0,
        "declarations_a_preparer": declarations_a_preparer,
    }

    if type_rapport == "reduit":
        prompt = f"""Génère un rapport de gestion RÉDUIT (synthèse exécutive) pour cette PME française.
Données : {donnees}

Le rapport doit contenir :
1. Titre avec nom entreprise et date
2. Synthèse en 3-4 phrases (situation globale)
3. 4-5 indicateurs clés avec commentaire court
4. 2-3 actions prioritaires

Format : HTML propre (pas de markdown). Utilise des balises <h2>, <p>, <table>, <strong>.
Style professionnel, concis, chiffré. Maximum 400 mots."""
    else:
        prompt = f"""Génère un rapport de gestion COMPLET et détaillé pour cette PME française.
Données : {donnees}

Le rapport doit contenir :
1. Page de garde (nom entreprise, SIRET, date, titre "Rapport de gestion")
2. Synthèse exécutive (5-6 phrases, situation globale, tendances)
3. Analyse du chiffre d'affaires (CA mois, CA annuel, tendance, commentaire)
4. Analyse de la trésorerie (solde, flux, risques, recommandations)
5. Gestion des créances (impayés, taux recouvrement, DSO estimé, plan d'action)
6. Ressources humaines (effectif, masse salariale, coût moyen, optimisations possibles)
7. Obligations fiscales et sociales (déclarations en attente, échéances)
8. Recommandations stratégiques (3-5 recommandations chiffrées et priorisées)
9. Conclusion

Format : HTML propre et professionnel (pas de markdown). Utilise <h1>, <h2>, <h3>, <p>, <table>, <strong>, <ul><li>.
Chaque section doit être détaillée avec des chiffres précis et des recommandations actionables.
Ton : professionnel, analytique, orienté décision. 800-1200 mots."""

    analyse_ia = question_ia(prompt, donnees)

    return {
        "type": type_rapport,
        "donnees": donnees,
        "rapport_html": analyse_ia,
    }
