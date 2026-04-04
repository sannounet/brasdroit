"""
Routes API — Comptabilite (ecritures, bilan, resultat, ratios, lettrage, liasse, ecarts, optimisation)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Optional, List
from decimal import Decimal
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    Ecriture, CompteComptable, Facture, MouvementBancaire,
    StatutFacture, Employe,
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


@router.post("/ecritures")
def create_ecriture(
    date_ecriture: str = Query(...),
    compte_debit: str = Query(...),
    compte_credit: str = Query(...),
    libelle: str = Query(...),
    montant: float = Query(...),
    numero_piece: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Créer une nouvelle écriture comptable."""
    e = Ecriture(
        entreprise_id=current_user.entreprise_id,
        date_ecriture=date_ecriture,
        numero_piece=numero_piece,
        compte_debit=compte_debit,
        compte_credit=compte_credit,
        libelle=libelle,
        montant=montant,
        created_by=current_user.id,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


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


@router.post("/comptes")
def create_compte(
    numero: str = Query(...),
    libelle: str = Query(...),
    classe: int = Query(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Créer un nouveau compte comptable."""
    c = CompteComptable(
        entreprise_id=current_user.entreprise_id,
        numero=numero,
        libelle=libelle,
        classe=classe,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


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


# ─── LIASSE FISCALE ───

@router.get("/liasse")
def liasse_fiscale(
    annee: int = Query(..., description="Annee de l'exercice"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Liasse fiscale auto-remplie (cerfa 2050/2051/2052) a partir des ecritures."""
    eid = current_user.entreprise_id

    ecritures = db.query(Ecriture).filter(
        Ecriture.entreprise_id == eid,
        extract("year", Ecriture.date_ecriture) == annee,
    ).all()

    comptes = db.query(CompteComptable).filter(
        CompteComptable.entreprise_id == eid
    ).all()
    compte_classe = {c.numero: c.classe for c in comptes}

    # Accumulateurs pour 2050 (Actif)
    immobilisations = 0.0    # classe 2 debits
    stocks = 0.0             # classe 3
    creances_clients = 0.0   # classe 4 debits (411xxx)
    autres_creances = 0.0    # classe 4 debits (non 411)
    disponibilites = 0.0     # classe 5 debits

    # Accumulateurs pour 2051 (Passif)
    capitaux = 0.0           # classe 1 credits
    dettes_fournisseurs = 0.0  # classe 4 credits (401xxx)
    dettes_fiscales = 0.0    # classe 4 credits (non 401)

    # Accumulateurs pour 2052 (Resultat)
    produits_exploitation = 0.0   # classe 7 (70-75)
    produits_financiers = 0.0     # classe 7 (76)
    produits_exceptionnels = 0.0  # classe 7 (77)
    charges_exploitation = 0.0    # classe 6 (60-65)
    charges_financieres = 0.0     # classe 6 (66)
    charges_exceptionnelles = 0.0 # classe 6 (67)
    impots = 0.0                  # classe 6 (69)

    for e in ecritures:
        montant = float(e.montant or 0)
        classe_d = compte_classe.get(e.compte_debit) or _classe_from_numero(e.compte_debit)
        classe_c = compte_classe.get(e.compte_credit) or _classe_from_numero(e.compte_credit)

        # ACTIF (debits)
        if classe_d == 2:
            immobilisations += montant
        elif classe_d == 3:
            stocks += montant
        elif classe_d == 4:
            if e.compte_debit.startswith("411"):
                creances_clients += montant
            else:
                autres_creances += montant
        elif classe_d == 5:
            disponibilites += montant

        # PASSIF (credits)
        if classe_c == 1:
            capitaux += montant
        elif classe_c == 4:
            if e.compte_credit.startswith("401"):
                dettes_fournisseurs += montant
            else:
                dettes_fiscales += montant

        # CHARGES (debits classe 6)
        if classe_d == 6:
            prefix = e.compte_debit[:2] if len(e.compte_debit) >= 2 else ""
            if prefix in ("60", "61", "62", "63", "64", "65"):
                charges_exploitation += montant
            elif prefix == "66":
                charges_financieres += montant
            elif prefix == "67":
                charges_exceptionnelles += montant
            elif prefix == "69":
                impots += montant
            else:
                charges_exploitation += montant

        # PRODUITS (credits classe 7)
        if classe_c == 7:
            prefix = e.compte_credit[:2] if len(e.compte_credit) >= 2 else ""
            if prefix in ("70", "71", "72", "73", "74", "75"):
                produits_exploitation += montant
            elif prefix == "76":
                produits_financiers += montant
            elif prefix == "77":
                produits_exceptionnels += montant
            else:
                produits_exploitation += montant

    total_actif = immobilisations + stocks + creances_clients + autres_creances + disponibilites
    total_passif = capitaux + dettes_fournisseurs + dettes_fiscales
    total_charges = charges_exploitation + charges_financieres + charges_exceptionnelles + impots
    total_produits = produits_exploitation + produits_financiers + produits_exceptionnels
    resultat_net = total_produits - total_charges

    # Passif inclut le resultat pour equilibrer
    total_passif_equilibre = total_passif + resultat_net

    return {
        "annee": annee,
        "cerfa_2050_actif": {
            "AA_immobilisations_incorporelles": 0,
            "AB_immobilisations_corporelles": round(immobilisations, 2),
            "BJ_stocks_et_en_cours": round(stocks, 2),
            "BX_creances_clients": round(creances_clients, 2),
            "BY_autres_creances": round(autres_creances, 2),
            "CF_disponibilites": round(disponibilites, 2),
            "CO_total_actif": round(total_actif, 2),
        },
        "cerfa_2051_passif": {
            "DA_capital": round(capitaux, 2),
            "DI_resultat_exercice": round(resultat_net, 2),
            "DV_dettes_fournisseurs": round(dettes_fournisseurs, 2),
            "DW_dettes_fiscales_sociales": round(dettes_fiscales, 2),
            "EE_total_passif": round(total_passif_equilibre, 2),
        },
        "cerfa_2052_resultat": {
            "FA_ventes_marchandises": 0,
            "FC_production_vendue": round(produits_exploitation, 2),
            "GF_charges_exploitation": round(charges_exploitation, 2),
            "GG_resultat_exploitation": round(produits_exploitation - charges_exploitation, 2),
            "GP_produits_financiers": round(produits_financiers, 2),
            "GQ_charges_financieres": round(charges_financieres, 2),
            "GR_resultat_financier": round(produits_financiers - charges_financieres, 2),
            "HB_produits_exceptionnels": round(produits_exceptionnels, 2),
            "HC_charges_exceptionnelles": round(charges_exceptionnelles, 2),
            "HD_resultat_exceptionnel": round(produits_exceptionnels - charges_exceptionnelles, 2),
            "HK_impot_benefices": round(impots, 2),
            "HN_resultat_net": round(resultat_net, 2),
        },
    }


# ─── ECARTS BUDGET vs REEL ───

@router.get("/ecarts")
def ecarts_budget_reel(
    annee: int = Query(..., description="Annee de l'analyse"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Analyse mensuelle encaissements vs decaissements avec variance."""
    eid = current_user.entreprise_id

    mouvements = db.query(MouvementBancaire).filter(
        MouvementBancaire.entreprise_id == eid,
        extract("year", MouvementBancaire.date_operation) == annee,
    ).all()

    # Agreger par mois
    mois_data = {}
    for m in range(1, 13):
        mois_data[m] = {"encaissements": 0.0, "decaissements": 0.0}

    for mv in mouvements:
        mois = mv.date_operation.month
        montant = float(mv.montant or 0)
        if montant > 0:
            mois_data[mois]["encaissements"] += montant
        else:
            mois_data[mois]["decaissements"] += abs(montant)

    # Calculer moyennes pour reference budget (moyenne glissante)
    total_enc = sum(m["encaissements"] for m in mois_data.values())
    total_dec = sum(m["decaissements"] for m in mois_data.values())
    mois_actifs = sum(1 for m in mois_data.values() if m["encaissements"] > 0 or m["decaissements"] > 0)
    budget_enc = (total_enc / mois_actifs) if mois_actifs else 0
    budget_dec = (total_dec / mois_actifs) if mois_actifs else 0

    resultats = []
    alertes = []
    for mois_num in range(1, 13):
        d = mois_data[mois_num]
        solde = d["encaissements"] - d["decaissements"]

        # Variance par rapport a la moyenne
        var_enc = ((d["encaissements"] - budget_enc) / budget_enc * 100) if budget_enc else 0
        var_dec = ((d["decaissements"] - budget_dec) / budget_dec * 100) if budget_dec else 0

        # Flag si ecart > 20%
        alerte = None
        if abs(var_enc) > 20 and d["encaissements"] > 0:
            alerte = "encaissements" if var_enc < -20 else None
        if var_dec > 20 and d["decaissements"] > 0:
            alerte = "depassement_depenses"

        if alerte:
            alertes.append({"mois": mois_num, "type": alerte, "variance_pct": round(var_dec if alerte == "depassement_depenses" else var_enc, 1)})

        resultats.append({
            "mois": mois_num,
            "encaissements": round(d["encaissements"], 2),
            "decaissements": round(d["decaissements"], 2),
            "solde": round(solde, 2),
            "budget_encaissements": round(budget_enc, 2),
            "budget_decaissements": round(budget_dec, 2),
            "variance_enc_pct": round(var_enc, 1),
            "variance_dec_pct": round(var_dec, 1),
        })

    return {
        "annee": annee,
        "mois": resultats,
        "totaux": {
            "encaissements": round(total_enc, 2),
            "decaissements": round(total_dec, 2),
            "solde_annuel": round(total_enc - total_dec, 2),
        },
        "alertes": alertes,
    }


# ─── OPTIMISATION IA ───

@router.get("/optimisation")
def optimisation(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Suggestions d'optimisation basees sur l'analyse des donnees."""
    eid = current_user.entreprise_id
    today = date.today()
    suggestions = []

    # 1. Factures en retard > 30 jours → provision
    factures_retard = db.query(Facture).filter(
        Facture.entreprise_id == eid,
        Facture.statut == StatutFacture.en_retard,
    ).all()

    montant_retard_30j = 0.0
    for f in factures_retard:
        if f.date_echeance and (today - f.date_echeance).days > 30:
            montant_retard_30j += float(f.montant_ttc or 0)

    if montant_retard_30j > 0:
        provision = round(montant_retard_30j * 0.5, 2)
        suggestions.append({
            "titre": "Provisionner les creances douteuses",
            "description": f"{round(montant_retard_30j, 2)} EUR de factures en retard de plus de 30 jours. "
                           f"Provisionner 50% reduirait le risque fiscal et ameliorerait la sincerite du bilan.",
            "impact_euros": provision,
            "priorite": "haute",
            "action": "Passer une ecriture 681/491 pour provisionner les creances douteuses.",
        })

    # 2. DSO (delai moyen encaissement)
    factures_reglees = db.query(Facture).filter(
        Facture.entreprise_id == eid,
        Facture.statut == StatutFacture.reglee,
        Facture.date_paiement.isnot(None),
        extract("year", Facture.date_facture) == today.year,
    ).all()

    if factures_reglees:
        total_jours = 0
        for f in factures_reglees:
            total_jours += (f.date_paiement - f.date_facture).days
        dso = total_jours / len(factures_reglees)

        if dso > 45:
            gain = round(montant_retard_30j * 0.02, 2) if montant_retard_30j else 500
            suggestions.append({
                "titre": "Ameliorer le delai de paiement (DSO)",
                "description": f"DSO actuel : {round(dso, 1)} jours (objectif < 45 jours). "
                               f"Envisager l'affacturage ou des conditions d'escompte pour paiement anticipe.",
                "impact_euros": gain,
                "priorite": "haute",
                "action": "Proposer 2% d'escompte pour paiement sous 10 jours. Activer les relances automatiques.",
            })

    # 3. Reduction Fillon (salaire < 1.6x SMIC)
    smic_mensuel = 1766.92  # SMIC brut mensuel 2025/2026
    seuil_fillon = smic_mensuel * 1.6

    employes = db.query(Employe).filter(
        Employe.entreprise_id == eid,
        Employe.is_active == True,
    ).all()

    employes_eligibles = [e for e in employes if e.salaire_brut and float(e.salaire_brut) <= seuil_fillon]
    if employes_eligibles:
        # Estimation reduction annuelle moyenne par salarie eligible
        total_reduction = 0.0
        for e in employes_eligibles:
            salaire = float(e.salaire_brut)
            coeff = max(0, (0.3206 / 0.6) * ((1.6 * smic_mensuel / salaire) - 1))
            coeff = min(coeff, 0.3206)
            reduction_mensuelle = salaire * coeff
            total_reduction += reduction_mensuelle * 12

        suggestions.append({
            "titre": "Reduction Fillon applicable",
            "description": f"{len(employes_eligibles)} salarie(s) eligible(s) a la reduction Fillon "
                           f"(salaire brut < {round(seuil_fillon, 2)} EUR). "
                           f"Verifier que la reduction est bien appliquee sur les bulletins.",
            "impact_euros": round(total_reduction, 2),
            "priorite": "moyenne",
            "action": "Verifier les bulletins de paie et appliquer le coefficient Fillon sur les cotisations patronales.",
        })

    # 4. Tresorerie excedentaire → placement
    solde_tresorerie = db.query(
        func.coalesce(func.sum(MouvementBancaire.montant), 0)
    ).filter(
        MouvementBancaire.entreprise_id == eid,
    ).scalar()
    solde = float(solde_tresorerie)

    if solde > 50000:
        rendement = round(solde * 0.03, 2)  # 3% sur un CAT
        suggestions.append({
            "titre": "Placer l'excedent de tresorerie",
            "description": f"Solde bancaire de {round(solde, 2)} EUR. "
                           f"Placer l'excedent sur un compte a terme ou DAT pour generer des interets.",
            "impact_euros": rendement,
            "priorite": "basse",
            "action": "Ouvrir un compte a terme aupres de la banque pour l'excedent au-dela de 30 000 EUR.",
        })

    # 5. Ecritures avec anomalies non resolues
    flags_non_resolus = db.query(func.count(Ecriture.id)).filter(
        Ecriture.entreprise_id == eid,
        Ecriture.flag_type.isnot(None),
        Ecriture.flag_resolu == False,
    ).scalar()

    if flags_non_resolus and flags_non_resolus > 0:
        suggestions.append({
            "titre": "Corriger les anomalies comptables",
            "description": f"{flags_non_resolus} ecriture(s) avec anomalie(s) non resolue(s) "
                           f"(doublons, comptes incorrects, risques TVA). A traiter avant la cloture.",
            "impact_euros": 0,
            "priorite": "haute",
            "action": "Aller dans Comptabilite > Ecritures et traiter les flags rouges.",
        })

    # Trier par priorite
    ordre_priorite = {"haute": 0, "moyenne": 1, "basse": 2}
    suggestions.sort(key=lambda s: ordre_priorite.get(s["priorite"], 9))

    return {
        "suggestions": suggestions,
        "nb_suggestions": len(suggestions),
    }


# ─── HELPERS ───

def _classe_from_numero(numero: str) -> Optional[int]:
    """Deduit la classe comptable du premier chiffre du numero de compte."""
    if numero and numero[0].isdigit():
        return int(numero[0])
    return None
