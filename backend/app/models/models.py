"""
Modèles SQLAlchemy — Tables PostgreSQL pour Bras Droit
Chaque classe = une table dans la base de données
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    ForeignKey, Enum, Text, Numeric
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


# ─────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────

class RoleEnum(str, enum.Enum):
    admin = "admin"
    comptable = "comptable"
    rh = "rh"
    commercial = "commercial"

class StatutFacture(str, enum.Enum):
    brouillon = "brouillon"
    emise = "emise"
    envoyee = "envoyee"
    en_attente = "en_attente"
    en_retard = "en_retard"
    reglee = "reglee"
    judiciaire = "judiciaire"

class StatutBC(str, enum.Enum):
    brouillon = "brouillon"
    valide = "valide"
    converti = "converti"
    annule = "annule"

class TypeContrat(str, enum.Enum):
    cdi = "CDI"
    cdd = "CDD"
    alternance = "Alternance"
    stage = "Stage"

class StatutDeclaration(str, enum.Enum):
    a_preparer = "a_preparer"
    preparee = "preparee"
    transmise = "transmise"
    validee = "validee"


# ─────────────────────────────────────────
# ENTREPRISE
# ─────────────────────────────────────────

class Entreprise(Base):
    __tablename__ = "entreprises"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(200), nullable=False)
    siret = Column(String(14), unique=True)
    siren = Column(String(9))
    tva_intra = Column(String(13))
    adresse = Column(Text)
    code_postal = Column(String(5))
    ville = Column(String(100))
    telephone = Column(String(20))
    email = Column(String(150))
    forme_juridique = Column(String(50), default="SAS")
    capital = Column(Numeric(12, 2), default=1000)
    convention_collective = Column(String(100))
    code_ape = Column(String(6))
    exercice_debut = Column(Integer, default=1)   # mois début exercice (1=janvier)
    taux_tva_defaut = Column(Float, default=20.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relations
    users = relationship("User", back_populates="entreprise")
    clients = relationship("Client", back_populates="entreprise")
    fournisseurs = relationship("Fournisseur", back_populates="entreprise")
    ecritures = relationship("Ecriture", back_populates="entreprise")
    factures = relationship("Facture", back_populates="entreprise")
    bons_commande = relationship("BonCommande", back_populates="entreprise")
    employes = relationship("Employe", back_populates="entreprise")
    declarations = relationship("Declaration", back_populates="entreprise")


# ─────────────────────────────────────────
# UTILISATEURS
# ─────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    prenom = Column(String(80))
    nom = Column(String(80))
    role = Column(Enum(RoleEnum), default=RoleEnum.admin)
    is_active = Column(Boolean, default=True)
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))

    entreprise = relationship("Entreprise", back_populates="users")


# ─────────────────────────────────────────
# CLIENTS & FOURNISSEURS
# ─────────────────────────────────────────

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"), nullable=False)
    nom = Column(String(200), nullable=False)
    siret = Column(String(14))
    tva_intra = Column(String(13))
    adresse = Column(Text)
    code_postal = Column(String(5))
    ville = Column(String(100))
    email = Column(String(150))
    telephone = Column(String(20))
    delai_paiement = Column(Integer, default=30)  # jours
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    entreprise = relationship("Entreprise", back_populates="clients")
    factures = relationship("Facture", back_populates="client")
    bons_commande = relationship("BonCommande", back_populates="client")


class Fournisseur(Base):
    __tablename__ = "fournisseurs"

    id = Column(Integer, primary_key=True, index=True)
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"), nullable=False)
    nom = Column(String(200), nullable=False)
    siret = Column(String(14))
    tva_intra = Column(String(13))
    adresse = Column(Text)
    email = Column(String(150))
    delai_paiement = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    entreprise = relationship("Entreprise", back_populates="fournisseurs")
    ecritures = relationship("Ecriture", back_populates="fournisseur")


# ─────────────────────────────────────────
# COMPTABILITÉ
# ─────────────────────────────────────────

class CompteComptable(Base):
    __tablename__ = "comptes_comptables"

    id = Column(Integer, primary_key=True, index=True)
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"), nullable=False)
    numero = Column(String(10), nullable=False)
    libelle = Column(String(200), nullable=False)
    classe = Column(Integer)          # 1 à 7
    is_active = Column(Boolean, default=True)
    solde_debit = Column(Numeric(14, 2), default=0)
    solde_credit = Column(Numeric(14, 2), default=0)


class Ecriture(Base):
    __tablename__ = "ecritures"

    id = Column(Integer, primary_key=True, index=True)
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"), nullable=False)
    date_ecriture = Column(Date, nullable=False)
    numero_piece = Column(String(30))
    compte_debit = Column(String(10), nullable=False)
    compte_credit = Column(String(10), nullable=False)
    libelle = Column(String(300), nullable=False)
    montant = Column(Numeric(12, 2), nullable=False)
    fournisseur_id = Column(Integer, ForeignKey("fournisseurs.id"), nullable=True)
    facture_id = Column(Integer, ForeignKey("factures.id"), nullable=True)
    lettre = Column(String(2))           # Lettrage bancaire A, B, C...
    is_lettree = Column(Boolean, default=False)
    # Red flags IA
    flag_type = Column(String(50))       # "doublon", "compte_incorrect", "tva_risque"
    flag_message = Column(Text)
    flag_resolu = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    entreprise = relationship("Entreprise", back_populates="ecritures")
    fournisseur = relationship("Fournisseur", back_populates="ecritures")


# ─────────────────────────────────────────
# FACTURATION
# ─────────────────────────────────────────

class BonCommande(Base):
    __tablename__ = "bons_commande"

    id = Column(Integer, primary_key=True, index=True)
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    numero = Column(String(30), unique=True, nullable=False)  # BC-2026-001
    date_bc = Column(Date, nullable=False)
    objet = Column(Text)
    montant_ht = Column(Numeric(12, 2), nullable=False)
    taux_tva = Column(Float, default=20.0)
    montant_tva = Column(Numeric(12, 2))
    montant_ttc = Column(Numeric(12, 2))
    statut = Column(Enum(StatutBC), default=StatutBC.brouillon)
    facture_id = Column(Integer, ForeignKey("factures.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    entreprise = relationship("Entreprise", back_populates="bons_commande")
    client = relationship("Client", back_populates="bons_commande")


class Facture(Base):
    __tablename__ = "factures"

    id = Column(Integer, primary_key=True, index=True)
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    numero = Column(String(30), unique=True, nullable=False)  # FA-2026-001
    bc_origine = Column(String(30))
    date_facture = Column(Date, nullable=False)
    date_echeance = Column(Date, nullable=False)
    objet = Column(Text)
    montant_ht = Column(Numeric(12, 2), nullable=False)
    taux_tva = Column(Float, default=20.0)
    montant_tva = Column(Numeric(12, 2))
    montant_ttc = Column(Numeric(12, 2))
    statut = Column(Enum(StatutFacture), default=StatutFacture.brouillon)
    date_paiement = Column(Date)
    # Recouvrement
    nb_relances = Column(Integer, default=0)
    date_derniere_relance = Column(Date)
    phase_judiciaire = Column(Boolean, default=False)
    # Factur-X
    facturx_xml = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    entreprise = relationship("Entreprise", back_populates="factures")
    client = relationship("Client", back_populates="factures")
    relances = relationship("Relance", back_populates="facture")


class Relance(Base):
    __tablename__ = "relances"

    id = Column(Integer, primary_key=True, index=True)
    facture_id = Column(Integer, ForeignKey("factures.id"), nullable=False)
    type_relance = Column(String(10))   # R1, R2, R3, LR1, LR2, LR3
    date_envoi = Column(DateTime(timezone=True), server_default=func.now())
    objet = Column(String(300))
    corps = Column(Text)
    mail_lu = Column(Boolean, default=False)
    date_lecture = Column(DateTime(timezone=True))

    facture = relationship("Facture", back_populates="relances")


# ─────────────────────────────────────────
# RH & PAIE
# ─────────────────────────────────────────

class Employe(Base):
    __tablename__ = "employes"

    id = Column(Integer, primary_key=True, index=True)
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"), nullable=False)
    nom = Column(String(80), nullable=False)
    prenom = Column(String(80), nullable=False)
    email = Column(String(150))
    telephone = Column(String(20))
    date_naissance = Column(Date)
    nir = Column(String(15))           # Numéro Sécu
    type_contrat = Column(Enum(TypeContrat), default=TypeContrat.cdi)
    date_entree = Column(Date, nullable=False)
    date_sortie = Column(Date)
    poste = Column(String(150))
    salaire_brut = Column(Numeric(10, 2), nullable=False)
    taux_pas = Column(Float, default=0.0)   # Taux PAS DGFIP %
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    entreprise = relationship("Entreprise", back_populates="employes")
    bulletins = relationship("BulletinPaie", back_populates="employe")


class BulletinPaie(Base):
    __tablename__ = "bulletins_paie"

    id = Column(Integer, primary_key=True, index=True)
    employe_id = Column(Integer, ForeignKey("employes.id"), nullable=False)
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"), nullable=False)
    mois = Column(Integer, nullable=False)    # 1-12
    annee = Column(Integer, nullable=False)
    salaire_brut = Column(Numeric(10, 2))
    prime = Column(Numeric(10, 2), default=0)
    heures_sup = Column(Float, default=0)
    absences_jours = Column(Float, default=0)
    tickets_resto_jours = Column(Integer, default=0)
    # Cotisations salariales
    cotis_salariales = Column(Numeric(10, 2))
    # Cotisations patronales
    cotis_patronales = Column(Numeric(10, 2))
    # Résultats
    net_imposable = Column(Numeric(10, 2))
    retenue_pas = Column(Numeric(10, 2))
    net_a_payer = Column(Numeric(10, 2))
    cout_employeur = Column(Numeric(10, 2))
    # PDF généré
    pdf_path = Column(String(500))
    dsn_transmis = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employe = relationship("Employe", back_populates="bulletins")


# ─────────────────────────────────────────
# DÉCLARATIONS FISCALES
# ─────────────────────────────────────────

class Declaration(Base):
    __tablename__ = "declarations"

    id = Column(Integer, primary_key=True, index=True)
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"), nullable=False)
    type_decl = Column(String(20), nullable=False)  # TVA, IS, URSSAF, DSN, RAS
    periode_mois = Column(Integer)
    periode_annee = Column(Integer, nullable=False)
    montant = Column(Numeric(12, 2))
    date_echeance = Column(Date)
    date_transmission = Column(DateTime(timezone=True))
    statut = Column(Enum(StatutDeclaration), default=StatutDeclaration.a_preparer)
    reference_transmission = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    entreprise = relationship("Entreprise", back_populates="declarations")


# ─────────────────────────────────────────
# TRÉSORERIE
# ─────────────────────────────────────────

class MouvementBancaire(Base):
    __tablename__ = "mouvements_bancaires"

    id = Column(Integer, primary_key=True, index=True)
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"), nullable=False)
    date_operation = Column(Date, nullable=False)
    libelle = Column(String(300), nullable=False)
    montant = Column(Numeric(12, 2), nullable=False)  # + encaissement, - décaissement
    categorie = Column(String(100))    # Salaires, TVA, Fournisseur...
    compte_comptable = Column(String(10))
    is_lettree = Column(Boolean, default=False)
    lettre = Column(String(2))
    source = Column(String(20), default="nordigen")  # nordigen, import_csv, manuel
    nordigen_id = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ─────────────────────────────────────────
# BUDGET PRÉVISIONNEL
# ─────────────────────────────────────────

class BudgetPrevisionnel(Base):
    __tablename__ = "budgets_previsionnels"

    id = Column(Integer, primary_key=True, index=True)
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"), nullable=False)
    annee = Column(Integer, nullable=False)
    mois = Column(Integer, nullable=False)            # 1-12
    categorie = Column(String(100), nullable=False)   # Ventes, Achats, Salaires, etc.
    type_ligne = Column(String(20), nullable=False)   # "recette" ou "depense"
    libelle = Column(String(200))
    montant_prevu = Column(Numeric(12, 2), nullable=False, default=0)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
