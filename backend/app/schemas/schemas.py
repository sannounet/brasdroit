"""
Schemas Pydantic — Validation des données entrantes et sortantes
"""
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from app.models.models import RoleEnum, StatutFacture, StatutBC, TypeContrat


# ─────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    prenom: str
    nom: str
    # Entreprise à créer
    entreprise_nom: str
    entreprise_siret: Optional[str] = None

    @field_validator("password")
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Le mot de passe doit faire au moins 8 caractères")
        return v


class LoginRequest(BaseModel):
    username: str   # email
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    prenom: str
    entreprise_id: int
    entreprise_nom: str


class UserOut(BaseModel):
    id: int
    email: str
    prenom: str
    nom: str
    role: RoleEnum
    entreprise_id: int
    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# ENTREPRISE
# ─────────────────────────────────────────

class EntrepriseUpdate(BaseModel):
    nom: Optional[str] = None
    siret: Optional[str] = None
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    convention_collective: Optional[str] = None
    taux_tva_defaut: Optional[float] = None


class EntrepriseOut(BaseModel):
    id: int
    nom: str
    siret: Optional[str]
    forme_juridique: str
    capital: Optional[Decimal]
    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# CLIENTS
# ─────────────────────────────────────────

class ClientCreate(BaseModel):
    nom: str
    siret: Optional[str] = None
    email: Optional[str] = None
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    telephone: Optional[str] = None
    delai_paiement: int = 30


class ClientOut(ClientCreate):
    id: int
    is_active: bool
    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# FACTURES
# ─────────────────────────────────────────

class FactureCreate(BaseModel):
    client_id: int
    objet: str
    montant_ht: Decimal
    taux_tva: float = 20.0
    date_facture: date
    date_echeance: date
    bc_origine: Optional[str] = None


class FactureOut(BaseModel):
    id: int
    numero: str
    client_id: int
    objet: Optional[str]
    montant_ht: Decimal
    montant_ttc: Optional[Decimal]
    statut: StatutFacture
    date_facture: date
    date_echeance: date
    nb_relances: int
    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# BON DE COMMANDE
# ─────────────────────────────────────────

class BCCreate(BaseModel):
    client_id: int
    objet: str
    montant_ht: Decimal
    taux_tva: float = 20.0
    date_bc: date


class BCOut(BaseModel):
    id: int
    numero: str
    client_id: int
    objet: Optional[str]
    montant_ht: Decimal
    montant_ttc: Optional[Decimal]
    statut: StatutBC
    date_bc: date
    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# ÉCRITURES
# ─────────────────────────────────────────

class EcritureCreate(BaseModel):
    date_ecriture: date
    numero_piece: Optional[str] = None
    compte_debit: str
    compte_credit: str
    libelle: str
    montant: Decimal
    fournisseur_id: Optional[int] = None
    facture_id: Optional[int] = None


class EcritureOut(EcritureCreate):
    id: int
    lettre: Optional[str]
    is_lettree: bool
    flag_type: Optional[str]
    flag_message: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# EMPLOYÉS & PAIE
# ─────────────────────────────────────────

class EmployeCreate(BaseModel):
    nom: str
    prenom: str
    email: Optional[str] = None
    telephone: Optional[str] = None
    date_naissance: Optional[date] = None
    nir: Optional[str] = None
    type_contrat: TypeContrat = TypeContrat.cdi
    date_entree: date
    poste: Optional[str] = None
    salaire_brut: Decimal
    taux_pas: float = 0.0


class EmployeOut(EmployeCreate):
    id: int
    is_active: bool
    class Config:
        from_attributes = True


class BulletinRequest(BaseModel):
    employe_id: int
    mois: int
    annee: int
    prime: float = 0.0
    heures_sup: float = 0.0
    absences_jours: float = 0.0
    tickets_resto_jours: int = 21


class BulletinOut(BaseModel):
    id: int
    employe_id: int
    mois: int
    annee: int
    salaire_brut: Optional[Decimal]
    net_imposable: Optional[Decimal]
    retenue_pas: Optional[Decimal]
    net_a_payer: Optional[Decimal]
    cout_employeur: Optional[Decimal]
    dsn_transmis: bool
    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────

class DashboardStats(BaseModel):
    ca_mois: float
    tresorerie: float
    impayes: float
    obligations_mois: float
    nb_alertes_urgentes: int
    nb_factures_en_retard: int
    score_sante: int


# ─────────────────────────────────────────
# IA
# ─────────────────────────────────────────

class IAQuestion(BaseModel):
    question: str
    contexte: Optional[str] = None
