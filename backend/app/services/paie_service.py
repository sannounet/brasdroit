"""
Service de calcul de paie — Moteur complet 2026
Taux URSSAF, réduction Fillon, PAS, tickets restaurant
"""
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass


# ─── Taux 2026 ───
PMSS = Decimal("3864.00")      # Plafond Mensuel Sécurité Sociale
SMIC_BRUT = Decimal("1801.80")
SMIC_NET = Decimal("1383.00")
TR_VALEUR = Decimal("11.38")   # Valeur ticket restaurant
TR_PART_PAT = Decimal("0.60")  # Part patronale 60%

# Cotisations salariales
T_MALADIE_S = Decimal("0.004")
T_CNAV_S = Decimal("0.069")
T_ARRCO_S = Decimal("0.0315")
T_CSG_DED = Decimal("0.068")
T_CSG_ND = Decimal("0.029")

# Cotisations patronales
T_MALADIE_P = Decimal("0.13")
T_CNAV_P = Decimal("0.0855")
T_CHOMAGE_P = Decimal("0.0405")
T_FNAL = Decimal("0.005")
T_ARRCO_P = Decimal("0.0472")
T_FORMA = Decimal("0.011")     # Formation professionnelle
T_PREVOY = Decimal("0.015")    # Prévoyance cadres (Syntec)


@dataclass
class ResultatPaie:
    brut_total: Decimal
    brut_plafonne: Decimal
    # Salariales
    cotis_maladie_s: Decimal
    cotis_cnav_s: Decimal
    cotis_arrco_s: Decimal
    cotis_csg_ded: Decimal
    cotis_csg_nd: Decimal
    total_cotis_s: Decimal
    # Net
    net_imposable: Decimal
    retenue_pas: Decimal
    ticket_resto: Decimal
    net_a_payer: Decimal
    # Patronales
    cotis_maladie_p: Decimal
    cotis_cnav_p: Decimal
    cotis_chomage_p: Decimal
    cotis_fnal: Decimal
    cotis_arrco_p: Decimal
    cotis_formation: Decimal
    reduction_fillon: Decimal
    total_cotis_p: Decimal
    cout_employeur: Decimal
    # Flags
    flag_smic: bool
    flag_fillon_applicable: bool


def calculer_reduction_fillon(brut: Decimal, pmss: Decimal) -> Decimal:
    """
    Réduction Fillon (réduction générale de cotisations patronales)
    Applicable si brut <= 1.6 x SMIC
    """
    seuil = SMIC_BRUT * Decimal("1.6")
    if brut > seuil:
        return Decimal("0")
    
    # Coefficient Fillon
    coeff = (Decimal("0.3214") / Decimal("0.6")) * (
        (Decimal("1.6") * SMIC_BRUT * 12 / (brut * 12)) - 1
    )
    coeff = min(coeff, Decimal("0.3214"))
    coeff = max(coeff, Decimal("0"))
    
    return (brut * coeff).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculer_bulletin(
    salaire_brut: float,
    taux_pas: float,
    prime: float = 0.0,
    heures_sup: float = 0.0,
    absences_jours: float = 0.0,
    tickets_resto_jours: int = 21,
    syntec: bool = False,
) -> ResultatPaie:
    """
    Calcule un bulletin de paie complet.
    
    Args:
        salaire_brut: Salaire mensuel brut de base
        taux_pas: Taux PAS individuel (%)
        prime: Prime mensuelle
        heures_sup: Heures supplémentaires (25% de majoration)
        absences_jours: Jours d'absence non payés
        tickets_resto_jours: Nombre de jours TR ce mois
        syntec: Convention Syntec (prévoyance cadre)
    
    Returns:
        ResultatPaie avec tous les montants calculés
    """
    r = lambda x: Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    brut_base = r(salaire_brut)
    prime_d = r(prime)
    
    # Déduction absences
    deduction_abs = r(salaire_brut / 21.67 * absences_jours) if absences_jours > 0 else Decimal("0")
    
    # Heures sup (majoration 25%)
    taux_horaire = r(salaire_brut / 151.67)
    hs_montant = r(float(taux_horaire) * heures_sup * 1.25)
    
    # Brut total
    brut_total = brut_base + prime_d + hs_montant - deduction_abs
    brut_plafonne = min(brut_total, PMSS)
    
    # Base CSG = 98.25% du brut
    base_csg = r(float(brut_total) * 0.9825)
    
    # ─ Cotisations salariales ─
    cotis_maladie_s = r(float(brut_total) * float(T_MALADIE_S))
    cotis_cnav_s = r(float(brut_plafonne) * float(T_CNAV_S))
    cotis_arrco_s = r(float(brut_plafonne) * float(T_ARRCO_S))
    cotis_csg_ded = r(float(base_csg) * float(T_CSG_DED))
    cotis_csg_nd = r(float(base_csg) * float(T_CSG_ND))
    
    total_cotis_s = cotis_maladie_s + cotis_cnav_s + cotis_arrco_s + cotis_csg_ded
    
    # ─ Net imposable ─
    net_imposable = brut_total - total_cotis_s
    
    # ─ PAS ─
    retenue_pas = r(float(net_imposable) * taux_pas / 100)
    
    # ─ Ticket restaurant (part patronale = gain salarié) ─
    ticket_resto = r(float(TR_VALEUR) * tickets_resto_jours * float(TR_PART_PAT))
    
    # ─ Net à payer ─
    net_a_payer = net_imposable - cotis_csg_nd - retenue_pas + ticket_resto
    
    # ─ Cotisations patronales ─
    cotis_maladie_p = r(float(brut_total) * float(T_MALADIE_P))
    cotis_cnav_p = r(float(brut_plafonne) * float(T_CNAV_P))
    cotis_chomage_p = r(float(brut_total) * float(T_CHOMAGE_P))
    cotis_fnal = r(float(brut_total) * float(T_FNAL))
    cotis_arrco_p = r(float(brut_plafonne) * float(T_ARRCO_P))
    cotis_formation = r(float(brut_total) * float(T_FORMA))
    cotis_prevoy = r(float(brut_total) * float(T_PREVOY)) if syntec else Decimal("0")
    
    # Réduction Fillon
    reduction_fillon = calculer_reduction_fillon(brut_total, PMSS)
    
    total_cotis_p = (
        cotis_maladie_p + cotis_cnav_p + cotis_chomage_p +
        cotis_fnal + cotis_arrco_p + cotis_formation + cotis_prevoy
        - reduction_fillon
    )
    
    cout_employeur = brut_total + total_cotis_p
    
    return ResultatPaie(
        brut_total=brut_total,
        brut_plafonne=brut_plafonne,
        cotis_maladie_s=cotis_maladie_s,
        cotis_cnav_s=cotis_cnav_s,
        cotis_arrco_s=cotis_arrco_s,
        cotis_csg_ded=cotis_csg_ded,
        cotis_csg_nd=cotis_csg_nd,
        total_cotis_s=total_cotis_s,
        net_imposable=net_imposable,
        retenue_pas=retenue_pas,
        ticket_resto=ticket_resto,
        net_a_payer=net_a_payer,
        cotis_maladie_p=cotis_maladie_p,
        cotis_cnav_p=cotis_cnav_p,
        cotis_chomage_p=cotis_chomage_p,
        cotis_fnal=cotis_fnal,
        cotis_arrco_p=cotis_arrco_p,
        cotis_formation=cotis_formation,
        reduction_fillon=reduction_fillon,
        total_cotis_p=total_cotis_p,
        cout_employeur=cout_employeur,
        flag_smic=net_a_payer < SMIC_NET,
        flag_fillon_applicable=brut_total <= SMIC_BRUT * Decimal("1.6"),
    )
