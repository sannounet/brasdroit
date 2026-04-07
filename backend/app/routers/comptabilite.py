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


from pydantic import BaseModel as _BM

class _EcritureIn(_BM):
    date_ecriture: str
    compte_debit: str
    compte_credit: str
    libelle: str
    montant: float
    numero_piece: Optional[str] = None

@router.post("/ecritures")
def create_ecriture(
    data: _EcritureIn,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Créer une nouvelle écriture comptable."""
    e = Ecriture(
        entreprise_id=current_user.entreprise_id,
        date_ecriture=data.date_ecriture,
        numero_piece=data.numero_piece,
        compte_debit=data.compte_debit,
        compte_credit=data.compte_credit,
        libelle=data.libelle,
        montant=data.montant,
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


class _CompteIn(_BM):
    numero: str
    libelle: str
    classe: int

@router.post("/comptes")
def create_compte(
    data: _CompteIn,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Créer un nouveau compte comptable."""
    c = CompteComptable(
        entreprise_id=current_user.entreprise_id,
        numero=data.numero,
        libelle=data.libelle,
        classe=data.classe,
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
    """Bilan détaillé : actif et passif décomposés par compte avec libellés."""
    eid = current_user.entreprise_id

    ecritures = db.query(Ecriture).filter(
        Ecriture.entreprise_id == eid,
        extract("year", Ecriture.date_ecriture) == annee,
    ).all()

    comptes = db.query(CompteComptable).filter(
        CompteComptable.entreprise_id == eid
    ).all()
    compte_classe = {c.numero: c.classe for c in comptes}
    compte_libelle = {c.numero: c.libelle for c in comptes}

    # Détail par compte
    actif_detail = {}  # numero -> {libelle, classe, montant}
    passif_detail = {}

    actif_par_classe = {}
    passif_par_classe = {}

    for e in ecritures:
        montant = float(e.montant or 0)
        cd = e.compte_debit
        cc = e.compte_credit
        classe_d = compte_classe.get(cd) or _classe_from_numero(cd)
        classe_c = compte_classe.get(cc) or _classe_from_numero(cc)

        if classe_d and 1 <= classe_d <= 5:
            if cd not in actif_detail:
                actif_detail[cd] = {"numero": cd, "libelle": compte_libelle.get(cd, _libelle_default(cd)), "classe": classe_d, "montant": 0}
            actif_detail[cd]["montant"] += montant
            actif_par_classe[classe_d] = actif_par_classe.get(classe_d, 0) + montant

        if classe_c and 1 <= classe_c <= 5:
            if cc not in passif_detail:
                passif_detail[cc] = {"numero": cc, "libelle": compte_libelle.get(cc, _libelle_default(cc)), "classe": classe_c, "montant": 0}
            passif_detail[cc]["montant"] += montant
            passif_par_classe[classe_c] = passif_par_classe.get(classe_c, 0) + montant

    # Trier par numéro de compte
    actif_lignes = sorted(actif_detail.values(), key=lambda x: x["numero"])
    passif_lignes = sorted(passif_detail.values(), key=lambda x: x["numero"])

    return {
        "annee": annee,
        "actif": actif_par_classe,
        "passif": passif_par_classe,
        "actif_detail": actif_lignes,
        "passif_detail": passif_lignes,
        "total_actif": sum(actif_par_classe.values()),
        "total_passif": sum(passif_par_classe.values()),
    }


def _libelle_default(numero: str) -> str:
    """Libellé par défaut basé sur le numéro de compte PCG."""
    defaults = {
        "101": "Capital social", "106": "Réserves", "110": "Report à nouveau", "164": "Emprunts",
        "211": "Terrains", "213": "Constructions", "215": "Installations techniques",
        "218": "Autres immobilisations", "281": "Amortissements",
        "401": "Fournisseurs", "411": "Clients", "421": "Personnel - Rémunérations",
        "431": "URSSAF", "437": "Cotisations sociales", "445": "TVA",
        "447": "Autres impôts", "455": "Compte courant associés",
        "512": "Banque", "530": "Caisse",
    }
    prefix = numero[:3] if len(numero) >= 3 else numero
    return defaults.get(prefix, f"Compte {numero}")


# ─── COMPTE DE RESULTAT ───

@router.get("/resultat")
def resultat(
    annee: int = Query(..., description="Annee de l'exercice"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compte de résultat détaillé décomposé par sous-catégorie PCG."""
    eid = current_user.entreprise_id

    ecritures = db.query(Ecriture).filter(
        Ecriture.entreprise_id == eid,
        extract("year", Ecriture.date_ecriture) == annee,
    ).all()

    comptes = db.query(CompteComptable).filter(
        CompteComptable.entreprise_id == eid
    ).all()
    compte_libelle = {c.numero: c.libelle for c in comptes}

    # Grouper par compte
    charges_par_compte = {}
    produits_par_compte = {}

    for e in ecritures:
        montant = float(e.montant or 0)
        cd = e.compte_debit
        cc = e.compte_credit

        # Charges = debits classe 6
        if cd and cd[0] == "6":
            if cd not in charges_par_compte:
                charges_par_compte[cd] = {"numero": cd, "libelle": compte_libelle.get(cd, _libelle_compte_resultat(cd)), "montant": 0}
            charges_par_compte[cd]["montant"] += montant

        # Produits = credits classe 7
        if cc and cc[0] == "7":
            if cc not in produits_par_compte:
                produits_par_compte[cc] = {"numero": cc, "libelle": compte_libelle.get(cc, _libelle_compte_resultat(cc)), "montant": 0}
            produits_par_compte[cc]["montant"] += montant

    # Trier par numéro
    charges_lignes = sorted(charges_par_compte.values(), key=lambda x: x["numero"])
    produits_lignes = sorted(produits_par_compte.values(), key=lambda x: x["numero"])

    # Décomposition par sous-catégorie (basée sur les 2 premiers chiffres)
    def categoriser_charges(numero):
        prefix = numero[:2] if len(numero) >= 2 else numero
        cats = {
            "60": "Achats",
            "61": "Services extérieurs",
            "62": "Autres services extérieurs",
            "63": "Impôts et taxes",
            "64": "Charges de personnel",
            "65": "Autres charges de gestion",
            "66": "Charges financières",
            "67": "Charges exceptionnelles",
            "68": "Dotations aux amortissements",
            "69": "Impôts sur les bénéfices",
        }
        return cats.get(prefix, "Autres charges")

    def categoriser_produits(numero):
        prefix = numero[:2] if len(numero) >= 2 else numero
        cats = {
            "70": "Ventes de produits et services",
            "71": "Production stockée",
            "72": "Production immobilisée",
            "73": "Subventions",
            "74": "Subventions d'exploitation",
            "75": "Autres produits",
            "76": "Produits financiers",
            "77": "Produits exceptionnels",
            "78": "Reprises sur amortissements",
            "79": "Transferts de charges",
        }
        return cats.get(prefix, "Autres produits")

    # Sous-totaux par catégorie
    charges_par_cat = {}
    for l in charges_lignes:
        cat = categoriser_charges(l["numero"])
        if cat not in charges_par_cat:
            charges_par_cat[cat] = {"categorie": cat, "montant": 0, "lignes": []}
        charges_par_cat[cat]["montant"] += l["montant"]
        charges_par_cat[cat]["lignes"].append(l)

    produits_par_cat = {}
    for l in produits_lignes:
        cat = categoriser_produits(l["numero"])
        if cat not in produits_par_cat:
            produits_par_cat[cat] = {"categorie": cat, "montant": 0, "lignes": []}
        produits_par_cat[cat]["montant"] += l["montant"]
        produits_par_cat[cat]["lignes"].append(l)

    # Sous-totaux pour le résultat structuré
    charges_exploitation = sum(g["montant"] for c, g in charges_par_cat.items() if c in ("Achats","Services extérieurs","Autres services extérieurs","Impôts et taxes","Charges de personnel","Autres charges de gestion","Dotations aux amortissements"))
    charges_financieres = charges_par_cat.get("Charges financières", {}).get("montant", 0)
    charges_exceptionnelles = charges_par_cat.get("Charges exceptionnelles", {}).get("montant", 0)
    impots_benefices = charges_par_cat.get("Impôts sur les bénéfices", {}).get("montant", 0)

    produits_exploitation = sum(g["montant"] for c, g in produits_par_cat.items() if c in ("Ventes de produits et services","Production stockée","Production immobilisée","Subventions d'exploitation","Subventions","Autres produits","Reprises sur amortissements","Transferts de charges"))
    produits_financiers_total = produits_par_cat.get("Produits financiers", {}).get("montant", 0)
    produits_exceptionnels_total = produits_par_cat.get("Produits exceptionnels", {}).get("montant", 0)

    resultat_exploitation = produits_exploitation - charges_exploitation
    resultat_financier = produits_financiers_total - charges_financieres
    resultat_exceptionnel = produits_exceptionnels_total - charges_exceptionnelles
    resultat_courant = resultat_exploitation + resultat_financier
    resultat_net = resultat_courant + resultat_exceptionnel - impots_benefices

    total_charges = sum(l["montant"] for l in charges_lignes)
    total_produits = sum(l["montant"] for l in produits_lignes)

    return {
        "annee": annee,
        "charges": round(total_charges, 2),
        "produits": round(total_produits, 2),
        "resultat_net": round(resultat_net, 2),
        "charges_detail": charges_lignes,
        "produits_detail": produits_lignes,
        "charges_par_categorie": list(charges_par_cat.values()),
        "produits_par_categorie": list(produits_par_cat.values()),
        "soldes_intermediaires": {
            "produits_exploitation": round(produits_exploitation, 2),
            "charges_exploitation": round(charges_exploitation, 2),
            "resultat_exploitation": round(resultat_exploitation, 2),
            "produits_financiers": round(produits_financiers_total, 2),
            "charges_financieres": round(charges_financieres, 2),
            "resultat_financier": round(resultat_financier, 2),
            "resultat_courant": round(resultat_courant, 2),
            "produits_exceptionnels": round(produits_exceptionnels_total, 2),
            "charges_exceptionnelles": round(charges_exceptionnelles, 2),
            "resultat_exceptionnel": round(resultat_exceptionnel, 2),
            "impots_benefices": round(impots_benefices, 2),
            "resultat_net": round(resultat_net, 2),
        },
    }


def _libelle_compte_resultat(numero: str) -> str:
    """Libellés par défaut pour les comptes 6 et 7."""
    defaults = {
        "601": "Achats matières premières",
        "604": "Achats prestations de services",
        "606": "Fournitures non stockables",
        "607": "Achats marchandises",
        "611": "Sous-traitance",
        "613": "Locations",
        "615": "Entretien et réparations",
        "616": "Primes d'assurances",
        "618": "Documentation",
        "621": "Personnel extérieur",
        "622": "Honoraires",
        "623": "Publicité",
        "625": "Déplacements et missions",
        "626": "Frais postaux et télécom",
        "627": "Services bancaires",
        "631": "Impôts et taxes",
        "641": "Salaires et traitements",
        "645": "Cotisations sociales",
        "651": "Redevances",
        "661": "Charges d'intérêts",
        "671": "Charges exceptionnelles",
        "681": "Dotations amortissements",
        "695": "Impôt sur les bénéfices",
        "701": "Ventes de produits finis",
        "704": "Travaux",
        "706": "Prestations de services",
        "707": "Ventes de marchandises",
        "708": "Produits accessoires",
        "740": "Subventions d'exploitation",
        "751": "Redevances perçues",
        "758": "Produits divers",
        "761": "Produits financiers",
        "771": "Produits exceptionnels",
        "781": "Reprises sur amortissements",
        "791": "Transferts de charges",
    }
    prefix = numero[:3] if len(numero) >= 3 else numero
    return defaults.get(prefix, f"Compte {numero}")


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
    avec_ia: bool = Query(False, description="Inclure analyse Claude IA"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compare le budget previsionnel ligne par ligne avec le realise (mouvements + factures)."""
    from app.models.models import BudgetPrevisionnel
    eid = current_user.entreprise_id

    # 1. Charger toutes les lignes du budget previsionnel
    lignes_prev = db.query(BudgetPrevisionnel).filter(
        BudgetPrevisionnel.entreprise_id == eid,
        BudgetPrevisionnel.annee == annee,
    ).all()

    # 2. Charger les mouvements bancaires de l'annee
    mouvements = db.query(MouvementBancaire).filter(
        MouvementBancaire.entreprise_id == eid,
        extract("year", MouvementBancaire.date_operation) == annee,
    ).all()

    # 3. Pour chaque ligne previsionnelle, calculer le realise correspondant
    def normalize(s):
        return (s or "").lower().strip()

    comparaisons = []
    for ligne in lignes_prev:
        # Trouver les mouvements du meme mois et de la meme categorie
        mvts_mois = [m for m in mouvements if m.date_operation.month == ligne.mois]

        if ligne.type_ligne == "recette":
            mvts_match = [m for m in mvts_mois if float(m.montant) > 0 and normalize(m.categorie) == normalize(ligne.categorie)]
            realise = sum(float(m.montant) for m in mvts_match)
        else:
            mvts_match = [m for m in mvts_mois if float(m.montant) < 0 and normalize(m.categorie) == normalize(ligne.categorie)]
            realise = abs(sum(float(m.montant) for m in mvts_match))

        prevu = float(ligne.montant_prevu)
        ecart = realise - prevu
        ecart_pct = (ecart / prevu * 100) if prevu else 0

        # Statut
        if ligne.type_ligne == "recette":
            statut = "favorable" if ecart >= 0 else ("alerte" if ecart_pct < -20 else "ecart_leger")
        else:
            statut = "favorable" if ecart <= 0 else ("alerte" if ecart_pct > 20 else "ecart_leger")

        comparaisons.append({
            "id": ligne.id,
            "mois": ligne.mois,
            "categorie": ligne.categorie,
            "libelle": ligne.libelle,
            "type_ligne": ligne.type_ligne,
            "montant_prevu": round(prevu, 2),
            "montant_realise": round(realise, 2),
            "ecart": round(ecart, 2),
            "ecart_pct": round(ecart_pct, 1),
            "statut": statut,
            "nb_mouvements": len(mvts_match),
        })

    # 4. Totaux
    total_prevu_rec = sum(c["montant_prevu"] for c in comparaisons if c["type_ligne"] == "recette")
    total_realise_rec = sum(c["montant_realise"] for c in comparaisons if c["type_ligne"] == "recette")
    total_prevu_dep = sum(c["montant_prevu"] for c in comparaisons if c["type_ligne"] == "depense")
    total_realise_dep = sum(c["montant_realise"] for c in comparaisons if c["type_ligne"] == "depense")

    # 5. Lignes en alerte
    alertes_lignes = [c for c in comparaisons if c["statut"] == "alerte"]

    result = {
        "annee": annee,
        "comparaisons": comparaisons,
        "totaux": {
            "recettes_prevues": round(total_prevu_rec, 2),
            "recettes_realisees": round(total_realise_rec, 2),
            "depenses_prevues": round(total_prevu_dep, 2),
            "depenses_realisees": round(total_realise_dep, 2),
            "ecart_recettes": round(total_realise_rec - total_prevu_rec, 2),
            "ecart_depenses": round(total_realise_dep - total_prevu_dep, 2),
            "resultat_prevu": round(total_prevu_rec - total_prevu_dep, 2),
            "resultat_realise": round(total_realise_rec - total_realise_dep, 2),
        },
        "nb_alertes": len(alertes_lignes),
        "alertes": alertes_lignes,
        "analyse_ia": None,
    }

    # 6. Analyse IA (optionnelle, lente)
    if avec_ia and lignes_prev:
        from app.services.ia_service import question_ia
        contexte = {
            "annee": annee,
            "comparaisons": [{"mois": c["mois"], "cat": c["categorie"], "type": c["type_ligne"],
                              "prevu": c["montant_prevu"], "realise": c["montant_realise"],
                              "ecart_pct": c["ecart_pct"]} for c in comparaisons],
            "totaux": result["totaux"],
        }
        prompt = f"""Tu parles à un dirigeant d'entreprise qui n'a AUCUNE connaissance en comptabilité ni en informatique.
Tu dois analyser ses prévisions de budget pour {annee} et lui expliquer en FRANCAIS SIMPLE et CLAIR ce qui se passe.

Donnees: {contexte}

REGLES STRICTES:
- Pas de HTML, pas de markdown, pas de tableaux
- Pas de jargon technique (pas de "écart", "variance", "ratio", "DSO", etc.)
- Utilise des phrases courtes et simples
- Parle comme à un ami qui te demande conseil
- Donne des montants en euros arrondis (pas de centimes)
- Maximum 200 mots
- Structure ton texte en 3 paragraphes simples séparés par des sauts de ligne :

Paragraphe 1 — Comment ça va globalement (en 2-3 phrases simples). Exemple : "Cette année, votre entreprise a gagné 50 000 euros de plus que prévu, c'est une très bonne nouvelle."

Paragraphe 2 — Ce qui ne va pas (les choses à corriger, en termes simples). Exemple : "Par contre, vous avez dépensé 8 000 euros de plus que prévu en marketing. C'est probablement parce que..."

Paragraphe 3 — Ce que vous devriez faire maintenant (3 conseils concrets et simples). Exemple : "Pour améliorer la situation, vous pourriez : 1) Réduire vos dépenses marketing de moitié, 2) Demander à vos clients de payer plus vite, 3) Reporter l'achat de matériel."

Réponds uniquement avec le texte, sans introduction ni formules de politesse."""
        try:
            result["analyse_ia"] = question_ia(prompt, contexte)
            # Detection d'erreur retournée par le service
            if "credit balance is too low" in result["analyse_ia"].lower():
                result["analyse_ia"] = "⚠ Le crédit Anthropic est épuisé. L'administrateur doit recharger le compte sur console.anthropic.com pour activer l'analyse IA."
        except Exception as e:
            err = str(e)
            if "credit balance" in err.lower():
                result["analyse_ia"] = "⚠ Le crédit Anthropic est épuisé. L'administrateur doit recharger le compte sur console.anthropic.com pour activer l'analyse IA."
            else:
                result["analyse_ia"] = f"Erreur lors de l'analyse : {err[:200]}"

    return result


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
