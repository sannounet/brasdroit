"""
Seed exercice 2026 — Données réalistes Q1 (jan-mars) + avril en cours
AgriSafe SAS — Croissance confirmée, objectif rentabilité
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import (
    Entreprise, Client, Fournisseur, Facture, BonCommande,
    Employe, BulletinPaie, Ecriture, Declaration, MouvementBancaire,
    StatutFacture, StatutBC, TypeContrat, StatutDeclaration
)


def seed_2026(db: Session, entreprise_id: int):
    """Ajoute les données 2026 sans toucher aux données existantes."""
    eid = entreprise_id
    entreprise = db.query(Entreprise).filter(Entreprise.id == eid).first()
    if not entreprise:
        raise ValueError(f"Entreprise {eid} introuvable")

    pfx = f"E{eid}-"

    # Récupérer les clients et employés existants
    clients = db.query(Client).filter(Client.entreprise_id == eid).all()
    employes = db.query(Employe).filter(Employe.entreprise_id == eid, Employe.is_active == True).all()
    fournisseurs = db.query(Fournisseur).filter(Fournisseur.entreprise_id == eid).all()

    if len(clients) < 6 or len(employes) < 4:
        raise ValueError("Données 2024-2025 manquantes. Lancez d'abord le seed principal.")

    # Supprimer les données 2026 existantes pour éviter les doublons
    db.query(Facture).filter(
        Facture.entreprise_id == eid,
        Facture.numero.like(f'{pfx}FA-2026%')
    ).delete(synchronize_session=False)
    db.query(BonCommande).filter(
        BonCommande.entreprise_id == eid,
        BonCommande.numero.like(f'{pfx}BC-2026%')
    ).delete(synchronize_session=False)
    db.query(BulletinPaie).filter(
        BulletinPaie.entreprise_id == eid,
        BulletinPaie.annee == 2026
    ).delete(synchronize_session=False)
    db.query(Declaration).filter(
        Declaration.entreprise_id == eid,
        Declaration.periode_annee == 2026
    ).delete(synchronize_session=False)
    db.query(MouvementBancaire).filter(
        MouvementBancaire.entreprise_id == eid,
        MouvementBancaire.date_operation >= date(2026, 1, 1)
    ).delete(synchronize_session=False)
    db.query(Ecriture).filter(
        Ecriture.entreprise_id == eid,
        Ecriture.date_ecriture >= date(2026, 1, 1)
    ).delete(synchronize_session=False)
    db.flush()

    # ══════════════════════════════════════════════
    # EXERCICE 2026 — Croissance forte, objectif bénéfice
    # CA cible : ~380k | Charges : ~290k | Résultat : +90k
    # ══════════════════════════════════════════════

    # ── FACTURES 2026 ──
    factures_2026 = [
        # Janvier — Bons contrats récurrents
        {"client_idx": 1, "numero": "FA-2026-001", "objet": "Plateforme coopérative — Maintenance annuelle 2026",
         "montant_ht": Decimal("18000.00"), "date_facture": date(2026, 1, 5), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2026, 2, 3)},
        {"client_idx": 0, "numero": "FA-2026-002", "objet": "Dashboard viticole — Évolutions V3 + IA prédictive",
         "montant_ht": Decimal("22000.00"), "date_facture": date(2026, 1, 15), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2026, 2, 18)},
        {"client_idx": 3, "numero": "FA-2026-003", "objet": "API traçabilité GMS — Support et évolutions Q1",
         "montant_ht": Decimal("12000.00"), "date_facture": date(2026, 1, 20), "jours": 60, "statut": StatutFacture.reglee, "date_paiement": date(2026, 3, 20)},

        # Février — Nouveaux contrats
        {"client_idx": 5, "numero": "FA-2026-004", "objet": "Plateforme formation — Module certifications en ligne",
         "montant_ht": Decimal("28000.00"), "date_facture": date(2026, 2, 1), "jours": 45, "statut": StatutFacture.reglee, "date_paiement": date(2026, 3, 15)},
        {"client_idx": 4, "numero": "FA-2026-005", "objet": "IoT capteurs — Déploiement 50 nouvelles parcelles",
         "montant_ht": Decimal("19500.00"), "date_facture": date(2026, 2, 10), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2026, 3, 12)},
        {"client_idx": 2, "numero": "FA-2026-006", "objet": "E-commerce vins — Module export international",
         "montant_ht": Decimal("15000.00"), "date_facture": date(2026, 2, 20), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2026, 3, 25)},

        # Mars — Gros contrat Euralis
        {"client_idx": 3, "numero": "FA-2026-007", "objet": "IA détection maladies vignes — Phase 1 R&D",
         "montant_ht": Decimal("45000.00"), "date_facture": date(2026, 3, 1), "jours": 60, "statut": StatutFacture.en_attente, "date_paiement": None},
        {"client_idx": 1, "numero": "FA-2026-008", "objet": "Plateforme coopérative — Module prévisions météo IA",
         "montant_ht": Decimal("16000.00"), "date_facture": date(2026, 3, 10), "jours": 45, "statut": StatutFacture.reglee, "date_paiement": date(2026, 4, 1)},
        {"client_idx": 0, "numero": "FA-2026-009", "objet": "Formation utilisateurs — 3 sessions sur site",
         "montant_ht": Decimal("7500.00"), "date_facture": date(2026, 3, 15), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2026, 4, 2)},

        # Avril — En cours
        {"client_idx": 5, "numero": "FA-2026-010", "objet": "Plateforme formation — App mobile iOS/Android",
         "montant_ht": Decimal("32000.00"), "date_facture": date(2026, 4, 1), "jours": 45, "statut": StatutFacture.emise, "date_paiement": None},
        {"client_idx": 4, "numero": "FA-2026-011", "objet": "Maintenance IoT — Abonnement Q2 2026",
         "montant_ht": Decimal("4800.00"), "date_facture": date(2026, 4, 1), "jours": 30, "statut": StatutFacture.emise, "date_paiement": None},
        {"client_idx": 2, "numero": "FA-2026-012", "objet": "SEO + campagne Ads — Lancement export",
         "montant_ht": Decimal("6500.00"), "date_facture": date(2026, 4, 2), "jours": 30, "statut": StatutFacture.emise, "date_paiement": None},

        # Impayé de 2025 toujours en retard
        {"client_idx": 3, "numero": "FA-2026-IMP", "objet": "Reliquat traçabilité 2025 — Litige en cours",
         "montant_ht": Decimal("8500.00"), "date_facture": date(2026, 1, 10), "jours": 30, "statut": StatutFacture.en_retard, "date_paiement": None},
    ]

    for fd in factures_2026:
        f = Facture(
            entreprise_id=eid,
            client_id=clients[fd["client_idx"]].id,
            numero=f"{pfx}{fd['numero']}",
            objet=fd["objet"],
            montant_ht=fd["montant_ht"],
            taux_tva=20.0,
            montant_tva=fd["montant_ht"] * Decimal("0.20"),
            montant_ttc=fd["montant_ht"] * Decimal("1.20"),
            date_facture=fd["date_facture"],
            date_echeance=fd["date_facture"] + timedelta(days=fd["jours"]),
            statut=fd["statut"],
            date_paiement=fd.get("date_paiement"),
            nb_relances=2 if fd["statut"] == StatutFacture.en_retard else 0,
        )
        db.add(f)

    # ── BONS DE COMMANDE 2026 ──
    bons_commande_2026 = [
        {"client_idx": 3, "numero": "BC-2026-001", "objet": "IA détection maladies vignes — Phase 1",
         "montant_ht": Decimal("45000.00"), "date_bc": date(2026, 1, 15), "statut": StatutBC.converti},
        {"client_idx": 5, "numero": "BC-2026-002", "objet": "App mobile formation",
         "montant_ht": Decimal("32000.00"), "date_bc": date(2026, 2, 20), "statut": StatutBC.converti},
        {"client_idx": 0, "numero": "BC-2026-003", "objet": "Migration cloud infrastructure viticole",
         "montant_ht": Decimal("18000.00"), "date_bc": date(2026, 3, 10), "statut": StatutBC.valide},
        {"client_idx": 1, "numero": "BC-2026-004", "objet": "Module blockchain traçabilité coopérative",
         "montant_ht": Decimal("55000.00"), "date_bc": date(2026, 4, 1), "statut": StatutBC.brouillon},
    ]
    for bc_data in bons_commande_2026:
        bc = BonCommande(
            entreprise_id=eid,
            client_id=clients[bc_data["client_idx"]].id,
            numero=f"{pfx}{bc_data['numero']}",
            objet=bc_data["objet"],
            montant_ht=bc_data["montant_ht"],
            taux_tva=20.0,
            montant_tva=bc_data["montant_ht"] * Decimal("0.20"),
            montant_ttc=bc_data["montant_ht"] * Decimal("1.20"),
            date_bc=bc_data["date_bc"],
            statut=bc_data["statut"],
        )
        db.add(bc)

    # ── BULLETINS DE PAIE 2026 (janv-mars finalisés, avril en cours) ──
    # Augmentations 2026
    paie_2026 = [
        {"emp_idx": 0, "brut": 5200, "cotis_sal": 1144, "cotis_pat": 2184, "net_imp": 4056, "pas": 446, "net": 3610, "cout": 7384},
        {"emp_idx": 1, "brut": 3800, "cotis_sal": 836, "cotis_pat": 1596, "net_imp": 2964, "pas": 222, "net": 2742, "cout": 5396},
        {"emp_idx": 2, "brut": 3200, "cotis_sal": 704, "cotis_pat": 1344, "net_imp": 2496, "pas": 125, "net": 2371, "cout": 4544},
        {"emp_idx": 3, "brut": 1400, "cotis_sal": 308, "cotis_pat": 588, "net_imp": 1092, "pas": 0, "net": 1092, "cout": 1988},
    ]
    for mois in range(1, 5):  # jan-avril
        for pd in paie_2026:
            prime = Decimal("800") if mois == 3 and pd["emp_idx"] == 0 else Decimal("0")  # Prime DG en mars
            brut = Decimal(str(pd["brut"])) + prime
            dsn = True if mois <= 3 else False
            db.add(BulletinPaie(
                employe_id=employes[pd["emp_idx"]].id, entreprise_id=eid,
                mois=mois, annee=2026,
                salaire_brut=brut, prime=prime,
                cotis_salariales=Decimal(str(pd["cotis_sal"])),
                cotis_patronales=Decimal(str(pd["cotis_pat"])),
                net_imposable=Decimal(str(pd["net_imp"])),
                retenue_pas=Decimal(str(pd["pas"])),
                net_a_payer=Decimal(str(pd["net"])),
                cout_employeur=Decimal(str(pd["cout"])),
                dsn_transmis=dsn,
            ))

    # ── DÉCLARATIONS 2026 ──
    # TVA mensuelle
    tva_montants = [3900, 4200, 5100, 0]  # Jan-Avr (avril pas encore déclaré)
    for mois in range(1, 5):
        statut = StatutDeclaration.validee if mois <= 2 else (StatutDeclaration.transmise if mois == 3 else StatutDeclaration.a_preparer)
        db.add(Declaration(
            entreprise_id=eid, type_decl="TVA",
            periode_mois=mois, periode_annee=2026,
            montant=Decimal(str(tva_montants[mois-1])),
            date_echeance=date(2026, mois + 1, 20) if mois < 12 else date(2027, 1, 20),
            statut=statut,
            date_transmission=datetime(2026, mois + 1, 18) if statut == StatutDeclaration.validee else None,
        ))

    # URSSAF mensuelle
    for mois in range(1, 5):
        statut = StatutDeclaration.validee if mois <= 3 else StatutDeclaration.a_preparer
        db.add(Declaration(
            entreprise_id=eid, type_decl="URSSAF",
            periode_mois=mois, periode_annee=2026,
            montant=Decimal("5712.00"),
            date_echeance=date(2026, mois, 15) if mois > 1 else date(2026, 1, 15),
            statut=statut,
            date_transmission=datetime(2026, mois, 13) if statut == StatutDeclaration.validee else None,
        ))

    # DSN mensuelle
    for mois in range(1, 5):
        statut = StatutDeclaration.transmise if mois <= 3 else StatutDeclaration.a_preparer
        db.add(Declaration(
            entreprise_id=eid, type_decl="DSN",
            periode_mois=mois, periode_annee=2026,
            montant=Decimal("0"),
            date_echeance=date(2026, mois, 5) + timedelta(days=30),
            statut=statut,
        ))

    # IS acomptes 2026
    for trim, mois_ech in [(1, 3), (2, 6)]:
        statut = StatutDeclaration.validee if trim == 1 else StatutDeclaration.a_preparer
        db.add(Declaration(
            entreprise_id=eid, type_decl="IS",
            periode_mois=trim, periode_annee=2026,
            montant=Decimal("3500.00"),
            date_echeance=date(2026, mois_ech, 15),
            statut=statut,
            date_transmission=datetime(2026, mois_ech, 13) if statut == StatutDeclaration.validee else None,
        ))

    # ── MOUVEMENTS BANCAIRES 2026 ──
    mouvements_2026 = [
        # Encaissements clients
        (date(2026, 2, 3), "Virement Maïsadour — FA-2026-001", Decimal("21600.00"), "Clients"),
        (date(2026, 2, 18), "Virement Château Margaux — FA-2026-002", Decimal("26400.00"), "Clients"),
        (date(2026, 3, 12), "Virement AgriTech — FA-2026-005", Decimal("23400.00"), "Clients"),
        (date(2026, 3, 15), "Virement Ch. Agriculture — FA-2026-004", Decimal("33600.00"), "Clients"),
        (date(2026, 3, 20), "Virement Euralis — FA-2026-003", Decimal("14400.00"), "Clients"),
        (date(2026, 3, 25), "Virement Vignobles Pomerol — FA-2026-006", Decimal("18000.00"), "Clients"),
        (date(2026, 4, 1), "Virement Maïsadour — FA-2026-008", Decimal("19200.00"), "Clients"),
        (date(2026, 4, 2), "Virement Château Margaux — FA-2026-009", Decimal("9000.00"), "Clients"),

        # Salaires nets (mensuel, 4 employés)
        (date(2026, 1, 31), "Salaires janvier 2026", Decimal("-9815.00"), "Salaires"),
        (date(2026, 2, 28), "Salaires février 2026", Decimal("-9815.00"), "Salaires"),
        (date(2026, 3, 31), "Salaires mars 2026 + prime DG", Decimal("-10615.00"), "Salaires"),
        (date(2026, 4, 3), "Salaires avril 2026 (acompte)", Decimal("-5000.00"), "Salaires"),

        # URSSAF
        (date(2026, 1, 15), "URSSAF janvier 2026", Decimal("-5712.00"), "URSSAF"),
        (date(2026, 2, 15), "URSSAF février 2026", Decimal("-5712.00"), "URSSAF"),
        (date(2026, 3, 15), "URSSAF mars 2026", Decimal("-5712.00"), "URSSAF"),

        # Loyer bureau
        (date(2026, 1, 5), "Loyer bureau janvier", Decimal("-1500.00"), "Loyer"),
        (date(2026, 2, 5), "Loyer bureau février", Decimal("-1500.00"), "Loyer"),
        (date(2026, 3, 5), "Loyer bureau mars", Decimal("-1500.00"), "Loyer"),
        (date(2026, 4, 5), "Loyer bureau avril", Decimal("-1500.00"), "Loyer"),

        # Fournisseurs
        (date(2026, 1, 15), "OVH Cloud — Hébergement Q1", Decimal("-580.00"), "Fournisseur"),
        (date(2026, 2, 10), "AWS — Services cloud", Decimal("-920.00"), "Fournisseur"),
        (date(2026, 3, 20), "Bureau Vallée — Fournitures", Decimal("-340.00"), "Fournisseur"),
        (date(2026, 1, 20), "AXA — Assurance RC Pro 2026", Decimal("-3200.00"), "Assurance"),
        (date(2026, 3, 31), "Cabinet Dupont — Honoraires EC Q1", Decimal("-2400.00"), "Fournisseur"),

        # TVA
        (date(2026, 2, 20), "TVA janvier 2026", Decimal("-3900.00"), "TVA"),
        (date(2026, 3, 20), "TVA février 2026", Decimal("-4200.00"), "TVA"),

        # IS acompte
        (date(2026, 3, 15), "IS — Acompte T1 2026", Decimal("-3500.00"), "IS"),

        # Investissement
        (date(2026, 2, 15), "LDLC — Station de travail IA + GPU", Decimal("-4500.00"), "Investissement"),
        (date(2026, 3, 1), "Licence Anthropic Claude — Abonnement annuel", Decimal("-1200.00"), "Fournisseur"),
    ]
    for d, lib, mt, cat in mouvements_2026:
        db.add(MouvementBancaire(
            entreprise_id=eid, date_operation=d, libelle=lib,
            montant=mt, categorie=cat, source="nordigen",
        ))

    # ── ÉCRITURES COMPTABLES 2026 ──
    ecritures_2026 = [
        # Ventes
        (date(2026, 1, 5), "VE-2026-001", "411000", "706000", "Maïsadour — Maintenance annuelle", Decimal("18000.00")),
        (date(2026, 1, 15), "VE-2026-002", "411000", "706000", "Château Margaux — Dashboard V3", Decimal("22000.00")),
        (date(2026, 1, 20), "VE-2026-003", "411000", "706000", "Euralis — Support API Q1", Decimal("12000.00")),
        (date(2026, 2, 1), "VE-2026-004", "411000", "706000", "Ch. Agriculture — Module certifications", Decimal("28000.00")),
        (date(2026, 2, 10), "VE-2026-005", "411000", "706000", "AgriTech — IoT 50 parcelles", Decimal("19500.00")),
        (date(2026, 2, 20), "VE-2026-006", "411000", "706000", "Vignobles Pomerol — Module export", Decimal("15000.00")),
        (date(2026, 3, 1), "VE-2026-007", "411000", "706000", "Euralis — IA détection Phase 1", Decimal("45000.00")),
        (date(2026, 3, 10), "VE-2026-008", "411000", "706000", "Maïsadour — Prévisions météo IA", Decimal("16000.00")),
        (date(2026, 3, 15), "VE-2026-009", "411000", "706000", "Château Margaux — Formation", Decimal("7500.00")),
        (date(2026, 4, 1), "VE-2026-010", "411000", "706000", "Ch. Agriculture — App mobile", Decimal("32000.00")),
        (date(2026, 4, 1), "VE-2026-011", "411000", "706000", "AgriTech — Maintenance IoT Q2", Decimal("4800.00")),
        (date(2026, 4, 2), "VE-2026-012", "411000", "706000", "Vignobles Pomerol — SEO/Ads", Decimal("6500.00")),

        # Salaires
        (date(2026, 1, 31), "SA-2026-01", "641000", "421000", "Salaires janvier 2026", Decimal("13600.00")),
        (date(2026, 1, 31), "CS-2026-01", "645000", "431000", "Charges sociales janvier 2026", Decimal("5712.00")),
        (date(2026, 2, 28), "SA-2026-02", "641000", "421000", "Salaires février 2026", Decimal("13600.00")),
        (date(2026, 2, 28), "CS-2026-02", "645000", "431000", "Charges sociales février 2026", Decimal("5712.00")),
        (date(2026, 3, 31), "SA-2026-03", "641000", "421000", "Salaires mars 2026 + prime", Decimal("14400.00")),
        (date(2026, 3, 31), "CS-2026-03", "645000", "431000", "Charges sociales mars 2026", Decimal("5712.00")),

        # Loyer
        (date(2026, 1, 5), "CH-2026-01", "613000", "512000", "Loyer bureau janvier 2026", Decimal("1500.00")),
        (date(2026, 2, 5), "CH-2026-02", "613000", "512000", "Loyer bureau février 2026", Decimal("1500.00")),
        (date(2026, 3, 5), "CH-2026-03", "613000", "512000", "Loyer bureau mars 2026", Decimal("1500.00")),

        # Fournisseurs
        (date(2026, 1, 15), "AC-2026-01", "604000", "401000", "OVH Cloud — Hébergement Q1", Decimal("580.00")),
        (date(2026, 2, 10), "AC-2026-02", "604000", "401000", "AWS — Services cloud", Decimal("920.00")),
        (date(2026, 2, 15), "AC-2026-03", "218300", "512000", "Station travail IA + GPU", Decimal("4500.00")),
        (date(2026, 3, 1), "AC-2026-04", "604000", "401000", "Licence Anthropic Claude", Decimal("1200.00")),
        (date(2026, 1, 20), "AC-2026-05", "616000", "512000", "AXA Assurance RC Pro 2026", Decimal("3200.00")),
    ]
    for d, num, debit, credit, lib, mt in ecritures_2026:
        db.add(Ecriture(
            entreprise_id=eid, date_ecriture=d, numero_piece=num,
            compte_debit=debit, compte_credit=credit, libelle=lib, montant=mt,
        ))

    db.commit()

    # Calculer les totaux
    ca_q1 = sum(f["montant_ht"] for f in factures_2026 if f["statut"] == StatutFacture.reglee)
    ca_avril = sum(f["montant_ht"] for f in factures_2026 if f["date_facture"].month == 4 and f["statut"] != StatutFacture.en_retard)

    return {
        "factures": len(factures_2026),
        "bons_commande": len(bons_commande_2026),
        "bulletins_paie": len(paie_2026) * 4,  # 4 mois
        "declarations": "TVA(4) + URSSAF(4) + DSN(4) + IS(2)",
        "mouvements_bancaires": len(mouvements_2026),
        "ecritures": len(ecritures_2026),
        "ca_q1_2026": float(ca_q1),
        "ca_avril_emis": float(ca_avril),
    }
