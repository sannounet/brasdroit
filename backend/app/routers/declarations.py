"""
Routes API — Déclarations (TVA, IS, URSSAF, DSN, RAS, Budget)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import date
from decimal import Decimal
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    Declaration, BulletinPaie, Employe, MouvementBancaire, StatutDeclaration,
    BudgetPrevisionnel,
)
from pydantic import BaseModel

router = APIRouter(prefix="/api/declarations", tags=["Déclarations"])


# ─── LISTE DES DÉCLARATIONS ───

@router.get("/")
def list_declarations(
    type_decl: Optional[str] = None,
    annee: Optional[int] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Liste de toutes les déclarations, filtrable par type et année."""
    q = db.query(Declaration).filter(
        Declaration.entreprise_id == current_user.entreprise_id
    )
    if type_decl:
        q = q.filter(Declaration.type_decl == type_decl)
    if annee:
        q = q.filter(Declaration.periode_annee == annee)
    return q.order_by(Declaration.periode_annee.desc(), Declaration.periode_mois.desc()).all()


# ─── TVA ───

@router.get("/tva")
def declarations_tva(
    annee: int = Query(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Déclarations TVA pour l'année avec TVA collectée et déductible estimées."""
    eid = current_user.entreprise_id

    declarations = db.query(Declaration).filter(
        Declaration.entreprise_id == eid,
        Declaration.type_decl == "TVA",
        Declaration.periode_annee == annee,
    ).order_by(Declaration.periode_mois).all()

    # Estimation TVA collectée (encaissements) et déductible (décaissements) par mois
    resultats = []
    total_collectee = 0
    total_deductible = 0

    for mois in range(1, 13):
        # Encaissements du mois -> TVA collectée (approximation 20%)
        enc = db.query(func.coalesce(func.sum(MouvementBancaire.montant), 0)).filter(
            MouvementBancaire.entreprise_id == eid,
            extract("year", MouvementBancaire.date_operation) == annee,
            extract("month", MouvementBancaire.date_operation) == mois,
            MouvementBancaire.montant > 0,
        ).scalar()

        # Décaissements du mois -> TVA déductible (approximation 20%)
        dec = db.query(func.coalesce(func.sum(MouvementBancaire.montant), 0)).filter(
            MouvementBancaire.entreprise_id == eid,
            extract("year", MouvementBancaire.date_operation) == annee,
            extract("month", MouvementBancaire.date_operation) == mois,
            MouvementBancaire.montant < 0,
        ).scalar()

        tva_collectee = round(float(enc) * 20 / 120, 2)
        tva_deductible = round(abs(float(dec)) * 20 / 120, 2)
        tva_nette = round(tva_collectee - tva_deductible, 2)

        total_collectee += tva_collectee
        total_deductible += tva_deductible

        # Trouver la déclaration correspondante
        decl = next((d for d in declarations if d.periode_mois == mois), None)

        resultats.append({
            "mois": mois,
            "tva_collectee": tva_collectee,
            "tva_deductible": tva_deductible,
            "tva_nette": tva_nette,
            "declaration": decl,
        })

    return {
        "annee": annee,
        "total_tva_collectee": round(total_collectee, 2),
        "total_tva_deductible": round(total_deductible, 2),
        "total_tva_nette": round(total_collectee - total_deductible, 2),
        "mois": resultats,
    }


# ─── IS (IMPÔT SUR LES SOCIÉTÉS) ───

@router.get("/is")
def declaration_is(
    annee: int = Query(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """IS : résultat fiscal estimé, montant IS, acomptes versés."""
    eid = current_user.entreprise_id

    # Chiffre d'affaires (encaissements)
    ca = db.query(func.coalesce(func.sum(MouvementBancaire.montant), 0)).filter(
        MouvementBancaire.entreprise_id == eid,
        extract("year", MouvementBancaire.date_operation) == annee,
        MouvementBancaire.montant > 0,
    ).scalar()

    # Charges (décaissements)
    charges = db.query(func.coalesce(func.sum(MouvementBancaire.montant), 0)).filter(
        MouvementBancaire.entreprise_id == eid,
        extract("year", MouvementBancaire.date_operation) == annee,
        MouvementBancaire.montant < 0,
    ).scalar()

    ca_ht = float(ca) / 1.2  # HT approximé
    charges_ht = abs(float(charges)) / 1.2
    resultat_fiscal = round(ca_ht - charges_ht, 2)

    # IS : 15% jusqu'à 42 500 EUR, 25% au-delà
    if resultat_fiscal <= 0:
        montant_is = 0
    elif resultat_fiscal <= 42500:
        montant_is = round(resultat_fiscal * 0.15, 2)
    else:
        montant_is = round(42500 * 0.15 + (resultat_fiscal - 42500) * 0.25, 2)

    # Acomptes IS versés (déclarations IS de l'année)
    acomptes = db.query(Declaration).filter(
        Declaration.entreprise_id == eid,
        Declaration.type_decl == "IS",
        Declaration.periode_annee == annee,
        Declaration.statut.in_([StatutDeclaration.transmise, StatutDeclaration.validee]),
    ).all()
    total_acomptes = sum(float(a.montant or 0) for a in acomptes)

    return {
        "annee": annee,
        "chiffre_affaires_ht": round(ca_ht, 2),
        "charges_ht": round(charges_ht, 2),
        "resultat_fiscal": resultat_fiscal,
        "montant_is": montant_is,
        "acomptes_verses": round(total_acomptes, 2),
        "reste_a_payer": round(montant_is - total_acomptes, 2),
        "declarations": acomptes,
    }


# ─── URSSAF ───

@router.get("/urssaf")
def declarations_urssaf(
    annee: int = Query(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Déclarations URSSAF avec charges sociales mensuelles issues des bulletins de paie."""
    eid = current_user.entreprise_id

    declarations = db.query(Declaration).filter(
        Declaration.entreprise_id == eid,
        Declaration.type_decl == "URSSAF",
        Declaration.periode_annee == annee,
    ).order_by(Declaration.periode_mois).all()

    resultats = []
    total_salariales = 0
    total_patronales = 0

    for mois in range(1, 13):
        bulletins = db.query(BulletinPaie).filter(
            BulletinPaie.entreprise_id == eid,
            BulletinPaie.annee == annee,
            BulletinPaie.mois == mois,
        ).all()

        cotis_sal = sum(float(b.cotis_salariales or 0) for b in bulletins)
        cotis_pat = sum(float(b.cotis_patronales or 0) for b in bulletins)
        total_salariales += cotis_sal
        total_patronales += cotis_pat

        decl = next((d for d in declarations if d.periode_mois == mois), None)

        resultats.append({
            "mois": mois,
            "cotisations_salariales": round(cotis_sal, 2),
            "cotisations_patronales": round(cotis_pat, 2),
            "total_cotisations": round(cotis_sal + cotis_pat, 2),
            "declaration": decl,
        })

    return {
        "annee": annee,
        "total_cotisations_salariales": round(total_salariales, 2),
        "total_cotisations_patronales": round(total_patronales, 2),
        "total_cotisations": round(total_salariales + total_patronales, 2),
        "mois": resultats,
    }


# ─── DSN ───

@router.get("/dsn")
def declaration_dsn(
    annee: int = Query(...),
    mois: int = Query(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """DSN : données paie du mois avec détail par employé."""
    eid = current_user.entreprise_id

    bulletins = db.query(BulletinPaie).filter(
        BulletinPaie.entreprise_id == eid,
        BulletinPaie.annee == annee,
        BulletinPaie.mois == mois,
    ).all()

    employes_detail = []
    totaux = {
        "salaire_brut": 0, "cotis_salariales": 0, "cotis_patronales": 0,
        "net_imposable": 0, "retenue_pas": 0, "net_a_payer": 0, "cout_employeur": 0,
    }

    for b in bulletins:
        employe = db.query(Employe).filter(Employe.id == b.employe_id).first()
        detail = {
            "employe": f"{employe.prenom} {employe.nom}" if employe else f"ID {b.employe_id}",
            "poste": employe.poste if employe else None,
            "type_contrat": employe.type_contrat if employe else None,
            "salaire_brut": float(b.salaire_brut or 0),
            "cotis_salariales": float(b.cotis_salariales or 0),
            "cotis_patronales": float(b.cotis_patronales or 0),
            "net_imposable": float(b.net_imposable or 0),
            "retenue_pas": float(b.retenue_pas or 0),
            "net_a_payer": float(b.net_a_payer or 0),
            "cout_employeur": float(b.cout_employeur or 0),
            "dsn_transmis": b.dsn_transmis,
        }
        employes_detail.append(detail)
        for key in totaux:
            totaux[key] += detail[key] if isinstance(detail.get(key), (int, float)) else 0

    # Arrondir les totaux
    totaux = {k: round(v, 2) for k, v in totaux.items()}

    # Déclaration DSN associée
    decl = db.query(Declaration).filter(
        Declaration.entreprise_id == eid,
        Declaration.type_decl == "DSN",
        Declaration.periode_annee == annee,
        Declaration.periode_mois == mois,
    ).first()

    return {
        "annee": annee,
        "mois": mois,
        "nb_employes": len(employes_detail),
        "employes": employes_detail,
        "totaux": totaux,
        "declaration": decl,
    }


# ─── RAS (RETENUE À LA SOURCE / PAS) ───

@router.get("/ras")
def declaration_ras(
    annee: int = Query(...),
    mois: int = Query(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """RAS : retenues à la source employés + fournisseurs + historique."""
    from app.models.models import Fournisseur
    eid = current_user.entreprise_id

    # 1. RAS EMPLOYÉS — depuis bulletins de paie du mois courant
    bulletins = db.query(BulletinPaie).filter(
        BulletinPaie.entreprise_id == eid,
        BulletinPaie.annee == annee,
        BulletinPaie.mois == mois,
    ).all()

    employes_detail = []
    for b in bulletins:
        employe = db.query(Employe).filter(Employe.id == b.employe_id).first()
        employes_detail.append({
            "employe": f"{employe.prenom} {employe.nom}" if employe else f"ID {b.employe_id}",
            "poste": employe.poste if employe else None,
            "net_imposable": float(b.net_imposable or 0),
            "taux_pas": float(employe.taux_pas or 0) if employe else 0,
            "retenue_pas": float(b.retenue_pas or 0),
        })

    total_emp = sum(e["retenue_pas"] for e in employes_detail)
    total_emp_ni = sum(e["net_imposable"] for e in employes_detail)

    # 2. RAS FOURNISSEURS — démo basée sur fournisseurs étrangers
    # En réalité, cela viendrait de factures fournisseurs avec retenue.
    # Pour la démo, on génère depuis les fournisseurs existants
    fournisseurs_all = db.query(Fournisseur).filter(
        Fournisseur.entreprise_id == eid,
        Fournisseur.is_active == True,
    ).limit(3).all()

    fournisseurs_detail = []
    for i, f in enumerate(fournisseurs_all):
        # Simuler des montants HT et taux de retenue
        montant_ht = [5000.0, 3500.0, 2200.0][i % 3]
        taux = [15.0, 10.0, 25.0][i % 3]
        retenue = round(montant_ht * taux / 100, 2)
        fournisseurs_detail.append({
            "fournisseur": f.nom,
            "siret": f.siret,
            "montant_ht": montant_ht,
            "taux_ras": taux,
            "retenue_ras": retenue,
            "net_a_payer": round(montant_ht - retenue, 2),
        })
    total_four = sum(f["retenue_ras"] for f in fournisseurs_detail)

    # 3. HISTORIQUE — déclarations RAS précédentes de l'année
    historique_decl = db.query(Declaration).filter(
        Declaration.entreprise_id == eid,
        Declaration.type_decl == "RAS",
        Declaration.periode_annee == annee,
    ).order_by(Declaration.periode_mois).all()

    # Si peu de déclarations RAS, recalculer depuis les bulletins
    historique = []
    for m in range(1, 13):
        b_mois = db.query(BulletinPaie).filter(
            BulletinPaie.entreprise_id == eid,
            BulletinPaie.annee == annee,
            BulletinPaie.mois == m,
        ).all()
        if not b_mois:
            continue
        total_pas_mois = sum(float(b.retenue_pas or 0) for b in b_mois)
        if total_pas_mois == 0:
            continue
        decl = next((d for d in historique_decl if d.periode_mois == m), None)
        statut = "regle"
        if decl:
            if decl.statut == StatutDeclaration.validee or decl.statut == StatutDeclaration.transmise:
                statut = "regle"
            else:
                statut = "non_regle"
        else:
            # Si pas de déclaration et c'est le mois courant ou futur, c'est non réglé
            statut = "non_regle" if m >= mois else "regle"

        historique.append({
            "mois": m,
            "montant": round(total_pas_mois, 2),
            "statut": statut,
            "date_versement": decl.date_transmission.isoformat() if decl and decl.date_transmission else None,
        })

    # Total à payer ce mois (employés + fournisseurs)
    total_a_payer = total_emp + total_four

    # Statut du mois courant
    statut_mois_courant = next((h["statut"] for h in historique if h["mois"] == mois), "non_regle")

    return {
        "annee": annee,
        "mois": mois,
        # Mois courant
        "employes": {
            "nb": len(employes_detail),
            "detail": employes_detail,
            "total_net_imposable": round(total_emp_ni, 2),
            "total_retenue": round(total_emp, 2),
        },
        "fournisseurs": {
            "nb": len(fournisseurs_detail),
            "detail": fournisseurs_detail,
            "total_retenue": round(total_four, 2),
        },
        "total_a_payer_mois": round(total_a_payer, 2),
        "statut_mois_courant": statut_mois_courant,
        # Historique
        "historique": historique,
        # Compatibilité ancienne version
        "detail": employes_detail,
        "total_net_imposable": round(total_emp_ni, 2),
        "total_retenue_pas": round(total_emp, 2),
    }


# ─── BUDGET VS RÉEL ───

@router.get("/budget")
def budget_vs_reel(
    annee: int = Query(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Comparaison mensuelle revenus / dépenses pour l'année."""
    eid = current_user.entreprise_id

    mois_data = []
    total_revenus = 0
    total_depenses = 0

    for mois in range(1, 13):
        revenus = db.query(func.coalesce(func.sum(MouvementBancaire.montant), 0)).filter(
            MouvementBancaire.entreprise_id == eid,
            extract("year", MouvementBancaire.date_operation) == annee,
            extract("month", MouvementBancaire.date_operation) == mois,
            MouvementBancaire.montant > 0,
        ).scalar()

        depenses = db.query(func.coalesce(func.sum(MouvementBancaire.montant), 0)).filter(
            MouvementBancaire.entreprise_id == eid,
            extract("year", MouvementBancaire.date_operation) == annee,
            extract("month", MouvementBancaire.date_operation) == mois,
            MouvementBancaire.montant < 0,
        ).scalar()

        rev = float(revenus)
        dep = float(depenses)
        total_revenus += rev
        total_depenses += dep

        mois_data.append({
            "mois": mois,
            "revenus": round(rev, 2),
            "depenses": round(abs(dep), 2),
            "resultat": round(rev + dep, 2),
        })

    return {
        "annee": annee,
        "total_revenus": round(total_revenus, 2),
        "total_depenses": round(abs(total_depenses), 2),
        "resultat_annuel": round(total_revenus + total_depenses, 2),
        "mois": mois_data,
    }


# ─── BUDGET PRÉVISIONNEL ───

class BudgetLigneIn(BaseModel):
    annee: int
    mois: int
    categorie: str
    type_ligne: str  # recette ou depense
    libelle: Optional[str] = None
    montant_prevu: float
    notes: Optional[str] = None


class BudgetLigneUpdate(BaseModel):
    categorie: Optional[str] = None
    type_ligne: Optional[str] = None
    libelle: Optional[str] = None
    montant_prevu: Optional[float] = None
    notes: Optional[str] = None


@router.get("/budget-previsionnel")
def list_budget_previsionnel(
    annee: int = Query(...),
    mois: Optional[int] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Liste les lignes du budget prévisionnel pour une année (et optionnellement un mois)."""
    q = db.query(BudgetPrevisionnel).filter(
        BudgetPrevisionnel.entreprise_id == current_user.entreprise_id,
        BudgetPrevisionnel.annee == annee,
    )
    if mois:
        q = q.filter(BudgetPrevisionnel.mois == mois)
    lignes = q.order_by(BudgetPrevisionnel.mois, BudgetPrevisionnel.type_ligne, BudgetPrevisionnel.categorie).all()

    # Calculer les totaux
    total_recettes = sum(float(l.montant_prevu) for l in lignes if l.type_ligne == "recette")
    total_depenses = sum(float(l.montant_prevu) for l in lignes if l.type_ligne == "depense")

    return {
        "annee": annee,
        "mois": mois,
        "lignes": [{
            "id": l.id,
            "annee": l.annee,
            "mois": l.mois,
            "categorie": l.categorie,
            "type_ligne": l.type_ligne,
            "libelle": l.libelle,
            "montant_prevu": float(l.montant_prevu),
            "notes": l.notes,
        } for l in lignes],
        "total_recettes": total_recettes,
        "total_depenses": total_depenses,
        "resultat_previsionnel": total_recettes - total_depenses,
    }


@router.post("/budget-previsionnel")
def create_budget_ligne(
    data: BudgetLigneIn,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Créer une nouvelle ligne de budget prévisionnel."""
    if data.type_ligne not in ("recette", "depense"):
        raise HTTPException(400, "type_ligne doit être recette ou depense")
    if data.mois < 1 or data.mois > 12:
        raise HTTPException(400, "mois doit être entre 1 et 12")

    ligne = BudgetPrevisionnel(
        entreprise_id=current_user.entreprise_id,
        annee=data.annee,
        mois=data.mois,
        categorie=data.categorie,
        type_ligne=data.type_ligne,
        libelle=data.libelle,
        montant_prevu=data.montant_prevu,
        notes=data.notes,
    )
    db.add(ligne)
    db.commit()
    db.refresh(ligne)
    return {"id": ligne.id, "status": "ok"}


@router.patch("/budget-previsionnel/{ligne_id}")
def update_budget_ligne(
    ligne_id: int,
    data: BudgetLigneUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mettre à jour une ligne de budget prévisionnel."""
    ligne = db.query(BudgetPrevisionnel).filter(
        BudgetPrevisionnel.id == ligne_id,
        BudgetPrevisionnel.entreprise_id == current_user.entreprise_id,
    ).first()
    if not ligne:
        raise HTTPException(404, "Ligne introuvable")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ligne, field, value)
    db.commit()
    return {"status": "ok"}


@router.delete("/budget-previsionnel/{ligne_id}")
def delete_budget_ligne(
    ligne_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Supprimer une ligne de budget prévisionnel."""
    ligne = db.query(BudgetPrevisionnel).filter(
        BudgetPrevisionnel.id == ligne_id,
        BudgetPrevisionnel.entreprise_id == current_user.entreprise_id,
    ).first()
    if not ligne:
        raise HTTPException(404, "Ligne introuvable")
    db.delete(ligne)
    db.commit()
    return {"status": "ok"}
