"""
Routes API — RH et Paie
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Employe, BulletinPaie
from app.schemas.schemas import EmployeCreate, EmployeOut, BulletinRequest, BulletinOut
from app.services.paie_service import calculer_bulletin

router = APIRouter(prefix="/api/paie", tags=["RH et Paie"])


# ─── EMPLOYÉS ───

@router.get("/employes", response_model=List[EmployeOut])
def list_employes(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Employe).filter(
        Employe.entreprise_id == current_user.entreprise_id,
        Employe.is_active == True
    ).order_by(Employe.nom).all()


@router.post("/employes", response_model=EmployeOut, status_code=201)
def create_employe(data: EmployeCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    employe = Employe(**data.model_dump(), entreprise_id=current_user.entreprise_id)
    db.add(employe)
    db.commit()
    db.refresh(employe)
    return employe


@router.patch("/employes/{emp_id}")
def update_employe(emp_id: int, data: dict, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    emp = db.query(Employe).filter(
        Employe.id == emp_id,
        Employe.entreprise_id == current_user.entreprise_id
    ).first()
    if not emp:
        raise HTTPException(404, "Employé introuvable")
    for k, v in data.items():
        if hasattr(emp, k):
            setattr(emp, k, v)
    db.commit()
    return {"message": "Employé mis à jour"}


# ─── BULLETINS DE PAIE ───

@router.post("/bulletins/calculer")
def calculer(data: BulletinRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Calcule un bulletin en temps réel sans l'enregistrer."""
    emp = db.query(Employe).filter(
        Employe.id == data.employe_id,
        Employe.entreprise_id == current_user.entreprise_id
    ).first()
    if not emp:
        raise HTTPException(404, "Employé introuvable")
    
    result = calculer_bulletin(
        salaire_brut=float(emp.salaire_brut),
        taux_pas=emp.taux_pas,
        prime=data.prime,
        heures_sup=data.heures_sup,
        absences_jours=data.absences_jours,
        tickets_resto_jours=data.tickets_resto_jours,
    )
    
    return {
        "employe": {"id": emp.id, "nom": emp.nom, "prenom": emp.prenom},
        "brut_total": float(result.brut_total),
        "cotisations_salariales": float(result.total_cotis_s),
        "net_imposable": float(result.net_imposable),
        "retenue_pas": float(result.retenue_pas),
        "net_a_payer": float(result.net_a_payer),
        "charges_patronales": float(result.total_cotis_p),
        "cout_employeur": float(result.cout_employeur),
        "reduction_fillon": float(result.reduction_fillon),
        "flag_smic": result.flag_smic,
        "flag_fillon_applicable": result.flag_fillon_applicable,
        "detail": {
            "maladie_s": float(result.cotis_maladie_s),
            "cnav_s": float(result.cotis_cnav_s),
            "arrco_s": float(result.cotis_arrco_s),
            "csg_ded": float(result.cotis_csg_ded),
            "csg_nd": float(result.cotis_csg_nd),
            "maladie_p": float(result.cotis_maladie_p),
            "cnav_p": float(result.cotis_cnav_p),
            "chomage_p": float(result.cotis_chomage_p),
            "arrco_p": float(result.cotis_arrco_p),
        }
    }


@router.post("/bulletins/valider", response_model=BulletinOut, status_code=201)
def valider_bulletin(data: BulletinRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Calcule et enregistre définitivement le bulletin en base."""
    # Vérifier doublon
    existing = db.query(BulletinPaie).filter(
        BulletinPaie.employe_id == data.employe_id,
        BulletinPaie.mois == data.mois,
        BulletinPaie.annee == data.annee
    ).first()
    if existing:
        raise HTTPException(400, f"Bulletin {data.mois}/{data.annee} déjà généré pour cet employé")
    
    emp = db.query(Employe).filter(
        Employe.id == data.employe_id,
        Employe.entreprise_id == current_user.entreprise_id
    ).first()
    if not emp:
        raise HTTPException(404, "Employé introuvable")
    
    result = calculer_bulletin(
        salaire_brut=float(emp.salaire_brut),
        taux_pas=emp.taux_pas,
        prime=data.prime,
        heures_sup=data.heures_sup,
        absences_jours=data.absences_jours,
        tickets_resto_jours=data.tickets_resto_jours,
    )
    
    bulletin = BulletinPaie(
        employe_id=data.employe_id,
        entreprise_id=current_user.entreprise_id,
        mois=data.mois,
        annee=data.annee,
        salaire_brut=result.brut_total,
        prime=data.prime,
        heures_sup=data.heures_sup,
        absences_jours=data.absences_jours,
        tickets_resto_jours=data.tickets_resto_jours,
        cotis_salariales=result.total_cotis_s,
        cotis_patronales=result.total_cotis_p,
        net_imposable=result.net_imposable,
        retenue_pas=result.retenue_pas,
        net_a_payer=result.net_a_payer,
        cout_employeur=result.cout_employeur,
    )
    db.add(bulletin)
    db.commit()
    db.refresh(bulletin)
    return bulletin


@router.get("/bulletins/{annee}/{mois}")
def bulletins_du_mois(annee: int, mois: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Résumé DSN-ready de tous les bulletins d'un mois avec details."""
    bulletins = db.query(BulletinPaie).filter(
        BulletinPaie.entreprise_id == current_user.entreprise_id,
        BulletinPaie.annee == annee,
        BulletinPaie.mois == mois
    ).all()

    # Charger les employés pour avoir leurs noms
    emp_ids = list(set(b.employe_id for b in bulletins))
    emps = {e.id: e for e in db.query(Employe).filter(Employe.id.in_(emp_ids)).all()} if emp_ids else {}

    total_brut = sum(float(b.salaire_brut or 0) for b in bulletins)
    total_charges = sum(float(b.cotis_patronales or 0) for b in bulletins)
    total_cot_sal = sum(float(b.cotis_salariales or 0) for b in bulletins)
    total_pas = sum(float(b.retenue_pas or 0) for b in bulletins)
    total_net = sum(float(b.net_a_payer or 0) for b in bulletins)
    total_net_imp = sum(float(b.net_imposable or 0) for b in bulletins)

    return {
        "periode": f"{mois:02d}/{annee}",
        "nb_employes": len(bulletins),
        "masse_salariale_brute": total_brut,
        "charges_patronales": total_charges,
        "cotis_salariales_total": total_cot_sal,
        "cout_total_employeur": total_brut + total_charges,
        "pas_total": total_pas,
        "net_total": total_net,
        "net_imposable_total": total_net_imp,
        "bulletins": [{
            "id": b.id,
            "employe_id": b.employe_id,
            "employe_nom": f"{emps[b.employe_id].prenom} {emps[b.employe_id].nom}" if b.employe_id in emps else "",
            "salaire_brut": float(b.salaire_brut or 0),
            "cotis_salariales": float(b.cotis_salariales or 0),
            "cotis_patronales": float(b.cotis_patronales or 0),
            "net_imposable": float(b.net_imposable or 0),
            "retenue_pas": float(b.retenue_pas or 0),
            "net_a_payer": float(b.net_a_payer or 0),
            "cout_employeur": float(b.cout_employeur or 0),
            "dsn_transmis": b.dsn_transmis,
        } for b in bulletins],
        "dsn_pret": all(b.dsn_transmis for b in bulletins) if bulletins else False,
    }
