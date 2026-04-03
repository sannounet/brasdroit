"""
Seed de démonstration — Données réalistes 2024 (bilan négatif) + 2025 (bilan positif)
Entreprise : AgriSafe SAS — Solutions digitales pour l'agriculture
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.models import (
    Entreprise, Client, Fournisseur, Facture, BonCommande,
    Employe, BulletinPaie, Ecriture, Declaration, MouvementBancaire,
    CompteComptable, StatutFacture, StatutBC, TypeContrat, StatutDeclaration
)


def seed_demo(db: Session, entreprise_id: int):
    """Remplit la base avec des données de démo réalistes."""

    eid = entreprise_id

    # Vérifier que l'entreprise existe
    entreprise = db.query(Entreprise).filter(Entreprise.id == eid).first()
    if not entreprise:
        raise ValueError(f"Entreprise {eid} introuvable")

    # Mettre à jour les infos entreprise
    entreprise.siret = "92345678900014"
    entreprise.siren = "923456789"
    entreprise.tva_intra = "FR56923456789"
    entreprise.adresse = "12 rue des Vignes"
    entreprise.code_postal = "33000"
    entreprise.ville = "Bordeaux"
    entreprise.telephone = "05 56 12 34 56"
    entreprise.email = "contact@agrisafe.fr"
    entreprise.forme_juridique = "SAS"
    entreprise.capital = Decimal("10000.00")
    entreprise.convention_collective = "SYNTEC"
    entreprise.code_ape = "6201Z"
    db.flush()

    # ── CLIENTS ──
    clients_data = [
        {"nom": "Domaine Château Margaux", "siret": "31234567800012", "email": "compta@chateau-margaux.fr",
         "adresse": "1 Cours du Médoc", "code_postal": "33460", "ville": "Margaux", "telephone": "05 57 88 83 83", "delai_paiement": 30},
        {"nom": "Coopérative Maïsadour", "siret": "42345678900015", "email": "facturation@maisadour.com",
         "adresse": "Avenue Léon Blum", "code_postal": "40001", "ville": "Mont-de-Marsan", "telephone": "05 58 05 87 00", "delai_paiement": 45},
        {"nom": "EARL Vignobles Pomerol", "siret": "53456789000018", "email": "gestion@vignobles-pomerol.fr",
         "adresse": "8 Lieu-dit Le Bourg", "code_postal": "33500", "ville": "Pomerol", "telephone": "05 57 51 78 96", "delai_paiement": 30},
        {"nom": "SA Groupe Euralis", "siret": "64567890100021", "email": "achats@euralis.com",
         "adresse": "Avenue Gaston Phoebus", "code_postal": "64231", "ville": "Lescar", "telephone": "05 59 92 38 38", "delai_paiement": 60},
        {"nom": "SARL AgriTech Solutions", "siret": "75678901200024", "email": "direction@agritech-solutions.fr",
         "adresse": "ZI Bel Air", "code_postal": "47000", "ville": "Agen", "telephone": "05 53 47 12 00", "delai_paiement": 30},
        {"nom": "Chambre d'Agriculture Gironde", "siret": "13456789000025", "email": "contact@gironde.chambagri.fr",
         "adresse": "17 cours Xavier Arnozan", "code_postal": "33000", "ville": "Bordeaux", "telephone": "05 56 79 64 00", "delai_paiement": 45},
    ]
    clients = []
    for c in clients_data:
        client = Client(entreprise_id=eid, **c)
        db.add(client)
        clients.append(client)
    db.flush()

    # ── FOURNISSEURS ──
    fournisseurs_data = [
        {"nom": "OVH Cloud", "siret": "42476141900045", "email": "facturation@ovhcloud.com", "delai_paiement": 30},
        {"nom": "AWS France", "siret": "83129984200016", "email": "billing@amazon.fr", "delai_paiement": 30},
        {"nom": "Bureau Vallée Bordeaux", "siret": "38912345600012", "email": "bordeaux@bureau-vallee.fr", "delai_paiement": 30},
        {"nom": "Cabinet Dupont & Associés (Expert-comptable)", "siret": "45678912300019", "email": "contact@dupont-ec.fr", "delai_paiement": 30},
        {"nom": "AXA Assurances Pro", "siret": "57214567800023", "email": "pro@axa.fr", "delai_paiement": 30},
    ]
    fournisseurs = []
    for f in fournisseurs_data:
        fournisseur = Fournisseur(entreprise_id=eid, **f)
        db.add(fournisseur)
        fournisseurs.append(fournisseur)
    db.flush()

    # ── EMPLOYÉS ──
    employes_data = [
        {"nom": "Darghouth", "prenom": "Sami", "email": "s.darghouth@agrisafe.fr",
         "type_contrat": TypeContrat.cdi, "date_entree": date(2023, 3, 1), "poste": "Directeur Général",
         "salaire_brut": Decimal("4500.00"), "taux_pas": 11.0,
         "date_naissance": date(1988, 6, 15), "nir": "188066933012345"},
        {"nom": "Martin", "prenom": "Julie", "email": "j.martin@agrisafe.fr",
         "type_contrat": TypeContrat.cdi, "date_entree": date(2023, 9, 1), "poste": "Développeuse Full-Stack",
         "salaire_brut": Decimal("3200.00"), "taux_pas": 7.5,
         "date_naissance": date(1995, 2, 20), "nir": "295023375012345"},
        {"nom": "Dubois", "prenom": "Marc", "email": "m.dubois@agrisafe.fr",
         "type_contrat": TypeContrat.cdi, "date_entree": date(2024, 1, 15), "poste": "Commercial Terrain",
         "salaire_brut": Decimal("2800.00"), "taux_pas": 5.0,
         "date_naissance": date(1991, 11, 3), "nir": "191113312012345"},
        {"nom": "Petit", "prenom": "Clara", "email": "c.petit@agrisafe.fr",
         "type_contrat": TypeContrat.alternance, "date_entree": date(2024, 9, 1), "poste": "Assistante Marketing",
         "salaire_brut": Decimal("1200.00"), "taux_pas": 0.0,
         "date_naissance": date(2002, 8, 25), "nir": "202083312012345"},
    ]
    employes = []
    for e in employes_data:
        employe = Employe(entreprise_id=eid, **e)
        db.add(employe)
        employes.append(employe)
    db.flush()

    # ── PLAN COMPTABLE ──
    comptes_data = [
        ("101000", "Capital social", 1), ("164000", "Emprunts", 1),
        ("211000", "Terrains", 2), ("218300", "Matériel informatique", 2),
        ("281830", "Amort. matériel info", 2),
        ("401000", "Fournisseurs", 4), ("411000", "Clients", 4),
        ("431000", "URSSAF", 4), ("445710", "TVA collectée", 4), ("445660", "TVA déductible", 4),
        ("512000", "Banque BNP", 5), ("530000", "Caisse", 5),
        ("601000", "Achats matières", 6), ("604000", "Achats prestations", 6),
        ("613000", "Loyers", 6), ("616000", "Assurances", 6),
        ("621000", "Personnel extérieur", 6), ("623000", "Publicité", 6),
        ("625000", "Déplacements", 6), ("626000", "Télécom & Internet", 6),
        ("627000", "Banque frais", 6), ("641000", "Salaires bruts", 6),
        ("645000", "Charges sociales", 6), ("681000", "Dotations amort.", 6),
        ("706000", "Prestations de services", 7), ("707000", "Ventes logiciels", 7),
        ("708000", "Revenus accessoires", 7), ("791000", "Transferts charges", 7),
    ]
    for numero, libelle, classe in comptes_data:
        db.add(CompteComptable(entreprise_id=eid, numero=numero, libelle=libelle, classe=classe))
    db.flush()

    # ══════════════════════════════════════════════
    # EXERCICE 2024 — BILAN NÉGATIF (année de lancement)
    # CA : ~142 000 € | Charges : ~185 000 € | Résultat : -43 000 €
    # ══════════════════════════════════════════════

    factures_2024 = [
        # T1 2024 — Début lent, 1 seul client
        {"client_idx": 0, "numero": "FA-2024-001", "objet": "Audit digitalisation exploitation viticole",
         "montant_ht": Decimal("4500.00"), "date_facture": date(2024, 1, 15), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2024, 2, 18)},
        {"client_idx": 0, "numero": "FA-2024-002", "objet": "Développement module suivi parcellaire - Phase 1",
         "montant_ht": Decimal("8500.00"), "date_facture": date(2024, 2, 28), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2024, 4, 2)},
        {"client_idx": 4, "numero": "FA-2024-003", "objet": "Consulting IoT capteurs agricoles",
         "montant_ht": Decimal("3200.00"), "date_facture": date(2024, 3, 20), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2024, 4, 25)},

        # T2 2024 — Quelques nouveaux contrats
        {"client_idx": 1, "numero": "FA-2024-004", "objet": "Étude de faisabilité plateforme coopérative",
         "montant_ht": Decimal("6000.00"), "date_facture": date(2024, 4, 10), "jours": 45, "statut": StatutFacture.reglee, "date_paiement": date(2024, 6, 1)},
        {"client_idx": 0, "numero": "FA-2024-005", "objet": "Développement module suivi parcellaire - Phase 2",
         "montant_ht": Decimal("12000.00"), "date_facture": date(2024, 5, 15), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2024, 6, 20)},
        {"client_idx": 2, "numero": "FA-2024-006", "objet": "Site vitrine + référencement SEO",
         "montant_ht": Decimal("3800.00"), "date_facture": date(2024, 6, 5), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2024, 7, 10)},

        # T3 2024 — Été calme
        {"client_idx": 3, "numero": "FA-2024-007", "objet": "POC application mobile traçabilité",
         "montant_ht": Decimal("15000.00"), "date_facture": date(2024, 7, 1), "jours": 60, "statut": StatutFacture.reglee, "date_paiement": date(2024, 9, 15)},
        {"client_idx": 4, "numero": "FA-2024-008", "objet": "Maintenance annuelle plateforme IoT",
         "montant_ht": Decimal("2400.00"), "date_facture": date(2024, 8, 1), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2024, 9, 5)},
        {"client_idx": 5, "numero": "FA-2024-009", "objet": "Formation digitalisation exploitants agricoles",
         "montant_ht": Decimal("7500.00"), "date_facture": date(2024, 9, 15), "jours": 45, "statut": StatutFacture.reglee, "date_paiement": date(2024, 11, 5)},

        # T4 2024 — Tentative de rattraper, un impayé
        {"client_idx": 1, "numero": "FA-2024-010", "objet": "Dev plateforme coopérative - Module adhérents",
         "montant_ht": Decimal("18000.00"), "date_facture": date(2024, 10, 1), "jours": 45, "statut": StatutFacture.reglee, "date_paiement": date(2024, 12, 10)},
        {"client_idx": 0, "numero": "FA-2024-011", "objet": "Intégration données météo en temps réel",
         "montant_ht": Decimal("9500.00"), "date_facture": date(2024, 11, 5), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2024, 12, 20)},
        {"client_idx": 3, "numero": "FA-2024-012", "objet": "Application mobile traçabilité - Phase 2",
         "montant_ht": Decimal("22000.00"), "date_facture": date(2024, 11, 20), "jours": 60, "statut": StatutFacture.en_retard, "date_paiement": None},
        {"client_idx": 2, "numero": "FA-2024-013", "objet": "Refonte site e-commerce vins",
         "montant_ht": Decimal("5800.00"), "date_facture": date(2024, 12, 10), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2025, 1, 15)},
        {"client_idx": 5, "numero": "FA-2024-014", "objet": "Dashboard statistiques régionales",
         "montant_ht": Decimal("8200.00"), "date_facture": date(2024, 12, 15), "jours": 45, "statut": StatutFacture.reglee, "date_paiement": date(2025, 2, 3)},
    ]

    for fd in factures_2024:
        f = Facture(
            entreprise_id=eid,
            client_id=clients[fd["client_idx"]].id,
            numero=fd["numero"],
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

    # ══════════════════════════════════════════════
    # EXERCICE 2025 — BILAN POSITIF (montée en puissance)
    # CA : ~285 000 € | Charges : ~210 000 € | Résultat : +75 000 €
    # ══════════════════════════════════════════════

    factures_2025 = [
        # T1 2025 — Bons contrats récurrents
        {"client_idx": 1, "numero": "FA-2025-001", "objet": "Plateforme coopérative - Module stocks & logistique",
         "montant_ht": Decimal("24000.00"), "date_facture": date(2025, 1, 10), "jours": 45, "statut": StatutFacture.reglee, "date_paiement": date(2025, 2, 28)},
        {"client_idx": 0, "numero": "FA-2025-002", "objet": "Maintenance annuelle + évolutions suivi parcellaire",
         "montant_ht": Decimal("12000.00"), "date_facture": date(2025, 1, 15), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2025, 2, 18)},
        {"client_idx": 5, "numero": "FA-2025-003", "objet": "Plateforme formation en ligne - Lot 1",
         "montant_ht": Decimal("18500.00"), "date_facture": date(2025, 2, 1), "jours": 45, "statut": StatutFacture.reglee, "date_paiement": date(2025, 3, 20)},
        {"client_idx": 4, "numero": "FA-2025-004", "objet": "Refonte complète plateforme IoT + dashboard",
         "montant_ht": Decimal("15000.00"), "date_facture": date(2025, 3, 1), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2025, 4, 5)},

        # T2 2025 — Gros contrat Euralis
        {"client_idx": 3, "numero": "FA-2025-005", "objet": "App mobile traçabilité - Déploiement national",
         "montant_ht": Decimal("35000.00"), "date_facture": date(2025, 4, 1), "jours": 60, "statut": StatutFacture.reglee, "date_paiement": date(2025, 6, 5)},
        {"client_idx": 2, "numero": "FA-2025-006", "objet": "E-commerce vins - Module abonnements",
         "montant_ht": Decimal("8500.00"), "date_facture": date(2025, 4, 15), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2025, 5, 20)},
        {"client_idx": 1, "numero": "FA-2025-007", "objet": "Plateforme coopérative - Module facturation adhérents",
         "montant_ht": Decimal("16000.00"), "date_facture": date(2025, 5, 10), "jours": 45, "statut": StatutFacture.reglee, "date_paiement": date(2025, 7, 1)},
        {"client_idx": 0, "numero": "FA-2025-008", "objet": "IA prédiction rendements — Module météo avancé",
         "montant_ht": Decimal("22000.00"), "date_facture": date(2025, 6, 1), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2025, 7, 5)},

        # T3 2025 — Croissance soutenue
        {"client_idx": 3, "numero": "FA-2025-009", "objet": "Formation utilisateurs app traçabilité (5 sessions)",
         "montant_ht": Decimal("12500.00"), "date_facture": date(2025, 7, 15), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2025, 8, 18)},
        {"client_idx": 5, "numero": "FA-2025-010", "objet": "Plateforme formation en ligne - Lot 2 + app mobile",
         "montant_ht": Decimal("21000.00"), "date_facture": date(2025, 8, 1), "jours": 45, "statut": StatutFacture.reglee, "date_paiement": date(2025, 9, 18)},
        {"client_idx": 4, "numero": "FA-2025-011", "objet": "Maintenance IoT + capteurs nouvelles parcelles",
         "montant_ht": Decimal("6500.00"), "date_facture": date(2025, 9, 1), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2025, 10, 5)},
        {"client_idx": 2, "numero": "FA-2025-012", "objet": "Refonte identité visuelle + site vitrine premium",
         "montant_ht": Decimal("9800.00"), "date_facture": date(2025, 9, 15), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2025, 10, 20)},

        # T4 2025 — Fin d'année forte + quelques factures en cours
        {"client_idx": 1, "numero": "FA-2025-013", "objet": "Plateforme coopérative - Module prévisionnel récoltes",
         "montant_ht": Decimal("28000.00"), "date_facture": date(2025, 10, 1), "jours": 45, "statut": StatutFacture.reglee, "date_paiement": date(2025, 11, 20)},
        {"client_idx": 3, "numero": "FA-2025-014", "objet": "API traçabilité — Intégration GMS (Leclerc, Carrefour)",
         "montant_ht": Decimal("32000.00"), "date_facture": date(2025, 11, 1), "jours": 60, "statut": StatutFacture.reglee, "date_paiement": date(2025, 12, 28)},
        {"client_idx": 0, "numero": "FA-2025-015", "objet": "Dashboard vinification 2025 + alertes automatisées",
         "montant_ht": Decimal("14500.00"), "date_facture": date(2025, 11, 15), "jours": 30, "statut": StatutFacture.reglee, "date_paiement": date(2025, 12, 18)},
        {"client_idx": 5, "numero": "FA-2025-016", "objet": "Support & maintenance plateforme formation 2026",
         "montant_ht": Decimal("9600.00"), "date_facture": date(2025, 12, 1), "jours": 45, "statut": StatutFacture.envoyee, "date_paiement": None},
        {"client_idx": 4, "numero": "FA-2025-017", "objet": "Contrat maintenance IoT 2026",
         "montant_ht": Decimal("7200.00"), "date_facture": date(2025, 12, 15), "jours": 30, "statut": StatutFacture.en_attente, "date_paiement": None},
    ]

    for fd in factures_2025:
        f = Facture(
            entreprise_id=eid,
            client_id=clients[fd["client_idx"]].id,
            numero=fd["numero"],
            objet=fd["objet"],
            montant_ht=fd["montant_ht"],
            taux_tva=20.0,
            montant_tva=fd["montant_ht"] * Decimal("0.20"),
            montant_ttc=fd["montant_ht"] * Decimal("1.20"),
            date_facture=fd["date_facture"],
            date_echeance=fd["date_facture"] + timedelta(days=fd["jours"]),
            statut=fd["statut"],
            date_paiement=fd.get("date_paiement"),
            nb_relances=0,
        )
        db.add(f)

    # ── BONS DE COMMANDE ──
    bons_commande = [
        {"client_idx": 3, "numero": "BC-2025-001", "objet": "API traçabilité GMS", "montant_ht": Decimal("32000.00"),
         "date_bc": date(2025, 9, 15), "statut": StatutBC.converti},
        {"client_idx": 1, "numero": "BC-2025-002", "objet": "Module prévisionnel récoltes", "montant_ht": Decimal("28000.00"),
         "date_bc": date(2025, 8, 20), "statut": StatutBC.converti},
        {"client_idx": 0, "numero": "BC-2026-001", "objet": "Migration cloud infrastructure viticole", "montant_ht": Decimal("18000.00"),
         "date_bc": date(2026, 1, 10), "statut": StatutBC.valide},
        {"client_idx": 3, "numero": "BC-2026-002", "objet": "Module IA détection maladies vignes", "montant_ht": Decimal("45000.00"),
         "date_bc": date(2026, 2, 1), "statut": StatutBC.brouillon},
    ]
    for bc_data in bons_commande:
        bc = BonCommande(
            entreprise_id=eid,
            client_id=clients[bc_data["client_idx"]].id,
            numero=bc_data["numero"],
            objet=bc_data["objet"],
            montant_ht=bc_data["montant_ht"],
            taux_tva=20.0,
            montant_tva=bc_data["montant_ht"] * Decimal("0.20"),
            montant_ttc=bc_data["montant_ht"] * Decimal("1.20"),
            date_bc=bc_data["date_bc"],
            statut=bc_data["statut"],
        )
        db.add(bc)

    # ── BULLETINS DE PAIE 2024 (12 mois × 3 employés, Clara arrive en sept) ──
    paie_data_2024 = [
        # Sami — DG
        {"emp_idx": 0, "brut": 4500, "cotis_sal": 990, "cotis_pat": 1890, "net_imp": 3510, "pas": 386, "net": 3124, "cout": 6390},
        # Julie — Dev
        {"emp_idx": 1, "brut": 3200, "cotis_sal": 704, "cotis_pat": 1344, "net_imp": 2496, "pas": 187, "net": 2309, "cout": 4544},
        # Marc — Commercial
        {"emp_idx": 2, "brut": 2800, "cotis_sal": 616, "cotis_pat": 1176, "net_imp": 2184, "pas": 109, "net": 2075, "cout": 3976},
    ]
    for mois in range(1, 13):
        for pd in paie_data_2024:
            prime = Decimal("500") if mois == 12 else Decimal("0")
            brut = Decimal(str(pd["brut"])) + prime
            db.add(BulletinPaie(
                employe_id=employes[pd["emp_idx"]].id, entreprise_id=eid,
                mois=mois, annee=2024,
                salaire_brut=brut, prime=prime,
                cotis_salariales=Decimal(str(pd["cotis_sal"])),
                cotis_patronales=Decimal(str(pd["cotis_pat"])),
                net_imposable=Decimal(str(pd["net_imp"])),
                retenue_pas=Decimal(str(pd["pas"])),
                net_a_payer=Decimal(str(pd["net"])),
                cout_employeur=Decimal(str(pd["cout"])),
                dsn_transmis=True,
            ))
        # Clara — Alternance (à partir de septembre 2024)
        if mois >= 9:
            db.add(BulletinPaie(
                employe_id=employes[3].id, entreprise_id=eid,
                mois=mois, annee=2024,
                salaire_brut=Decimal("1200"), prime=Decimal("0"),
                cotis_salariales=Decimal("264"),
                cotis_patronales=Decimal("504"),
                net_imposable=Decimal("936"),
                retenue_pas=Decimal("0"),
                net_a_payer=Decimal("936"),
                cout_employeur=Decimal("1704"),
                dsn_transmis=True,
            ))

    # ── BULLETINS DE PAIE 2025 (4 employés × 12 mois) ──
    paie_data_2025 = [
        {"emp_idx": 0, "brut": 4800, "cotis_sal": 1056, "cotis_pat": 2016, "net_imp": 3744, "pas": 412, "net": 3332, "cout": 6816},
        {"emp_idx": 1, "brut": 3500, "cotis_sal": 770, "cotis_pat": 1470, "net_imp": 2730, "pas": 205, "net": 2525, "cout": 4970},
        {"emp_idx": 2, "brut": 3000, "cotis_sal": 660, "cotis_pat": 1260, "net_imp": 2340, "pas": 117, "net": 2223, "cout": 4260},
        {"emp_idx": 3, "brut": 1200, "cotis_sal": 264, "cotis_pat": 504, "net_imp": 936, "pas": 0, "net": 936, "cout": 1704},
    ]
    for mois in range(1, 13):
        for pd in paie_data_2025:
            prime = Decimal("1000") if mois == 12 and pd["emp_idx"] < 3 else Decimal("0")
            brut = Decimal(str(pd["brut"])) + prime
            db.add(BulletinPaie(
                employe_id=employes[pd["emp_idx"]].id, entreprise_id=eid,
                mois=mois, annee=2025,
                salaire_brut=brut, prime=prime,
                cotis_salariales=Decimal(str(pd["cotis_sal"])),
                cotis_patronales=Decimal(str(pd["cotis_pat"])),
                net_imposable=Decimal(str(pd["net_imp"])),
                retenue_pas=Decimal(str(pd["pas"])),
                net_a_payer=Decimal(str(pd["net"])),
                cout_employeur=Decimal(str(pd["cout"])),
                dsn_transmis=True if mois <= 11 else False,
            ))

    # ── DÉCLARATIONS FISCALES ──
    # TVA trimestrielle
    for annee in [2024, 2025]:
        for trimestre, mois_decl, echeance_jour in [(1, 4, 20), (2, 7, 20), (3, 10, 20), (4, 1, 20)]:
            echeance_annee = annee if trimestre < 4 else annee + 1
            statut = StatutDeclaration.validee if annee == 2024 else (
                StatutDeclaration.validee if trimestre <= 3 else StatutDeclaration.a_preparer
            )
            tva_collectee = Decimal("7100") if annee == 2024 else Decimal("14200")
            tva_deductible = Decimal("3200") if annee == 2024 else Decimal("4800")
            db.add(Declaration(
                entreprise_id=eid, type_decl="TVA",
                periode_mois=trimestre, periode_annee=annee,
                montant=tva_collectee - tva_deductible,
                date_echeance=date(echeance_annee, mois_decl, echeance_jour),
                statut=statut,
                date_transmission=datetime(echeance_annee, mois_decl, echeance_jour - 2) if statut == StatutDeclaration.validee else None,
            ))

    # URSSAF mensuelle 2025
    for mois in range(1, 13):
        statut = StatutDeclaration.validee if mois <= 11 else StatutDeclaration.a_preparer
        db.add(Declaration(
            entreprise_id=eid, type_decl="URSSAF",
            periode_mois=mois, periode_annee=2025,
            montant=Decimal("5250.00"),
            date_echeance=date(2025, mois, 15) if mois < 12 else date(2026, 1, 15),
            statut=statut,
            date_transmission=datetime(2025, mois, 13) if statut == StatutDeclaration.validee else None,
        ))

    # IS 2024 et 2025
    db.add(Declaration(
        entreprise_id=eid, type_decl="IS", periode_annee=2024,
        montant=Decimal("0"),  # Pas d'IS car résultat négatif
        date_echeance=date(2025, 5, 15),
        statut=StatutDeclaration.validee,
        date_transmission=datetime(2025, 5, 12),
    ))
    db.add(Declaration(
        entreprise_id=eid, type_decl="IS", periode_annee=2025,
        montant=Decimal("11250.00"),  # 15% sur 75k de résultat
        date_echeance=date(2026, 5, 15),
        statut=StatutDeclaration.a_preparer,
    ))

    # DSN mensuelle 2025
    for mois in range(1, 13):
        statut = StatutDeclaration.transmise if mois <= 11 else StatutDeclaration.a_preparer
        db.add(Declaration(
            entreprise_id=eid, type_decl="DSN",
            periode_mois=mois, periode_annee=2025,
            montant=Decimal("0"),
            date_echeance=date(2025, mois, 5) + timedelta(days=30),
            statut=statut,
        ))

    # ── MOUVEMENTS BANCAIRES ──
    # 2024 — Solde final négatif (découvert)
    mouvements_2024 = [
        # Encaissements clients 2024
        (date(2024, 2, 18), "Virement Château Margaux — FA-2024-001", Decimal("5400.00"), "Clients"),
        (date(2024, 4, 2), "Virement Château Margaux — FA-2024-002", Decimal("10200.00"), "Clients"),
        (date(2024, 4, 25), "Virement AgriTech — FA-2024-003", Decimal("3840.00"), "Clients"),
        (date(2024, 6, 1), "Virement Maïsadour — FA-2024-004", Decimal("7200.00"), "Clients"),
        (date(2024, 6, 20), "Virement Château Margaux — FA-2024-005", Decimal("14400.00"), "Clients"),
        (date(2024, 7, 10), "Virement Vignobles Pomerol — FA-2024-006", Decimal("4560.00"), "Clients"),
        (date(2024, 9, 15), "Virement Euralis — FA-2024-007", Decimal("18000.00"), "Clients"),
        (date(2024, 9, 5), "Virement AgriTech — FA-2024-008", Decimal("2880.00"), "Clients"),
        (date(2024, 11, 5), "Virement Ch. Agriculture — FA-2024-009", Decimal("9000.00"), "Clients"),
        (date(2024, 12, 10), "Virement Maïsadour — FA-2024-010", Decimal("21600.00"), "Clients"),
        (date(2024, 12, 20), "Virement Château Margaux — FA-2024-011", Decimal("11400.00"), "Clients"),
        # Salaires nets 2024 (mensuel)
        (date(2024, 1, 31), "Salaires janvier 2024", Decimal("-7508.00"), "Salaires"),
        (date(2024, 2, 28), "Salaires février 2024", Decimal("-7508.00"), "Salaires"),
        (date(2024, 3, 31), "Salaires mars 2024", Decimal("-7508.00"), "Salaires"),
        (date(2024, 4, 30), "Salaires avril 2024", Decimal("-7508.00"), "Salaires"),
        (date(2024, 5, 31), "Salaires mai 2024", Decimal("-7508.00"), "Salaires"),
        (date(2024, 6, 30), "Salaires juin 2024", Decimal("-7508.00"), "Salaires"),
        (date(2024, 7, 31), "Salaires juillet 2024", Decimal("-7508.00"), "Salaires"),
        (date(2024, 8, 31), "Salaires août 2024", Decimal("-7508.00"), "Salaires"),
        (date(2024, 9, 30), "Salaires septembre 2024", Decimal("-8444.00"), "Salaires"),
        (date(2024, 10, 31), "Salaires octobre 2024", Decimal("-8444.00"), "Salaires"),
        (date(2024, 11, 30), "Salaires novembre 2024", Decimal("-8444.00"), "Salaires"),
        (date(2024, 12, 31), "Salaires décembre 2024 + primes", Decimal("-9944.00"), "Salaires"),
        # Charges sociales patronales (trimestriel)
        (date(2024, 4, 15), "URSSAF T1 2024", Decimal("-13230.00"), "URSSAF"),
        (date(2024, 7, 15), "URSSAF T2 2024", Decimal("-13230.00"), "URSSAF"),
        (date(2024, 10, 15), "URSSAF T3 2024", Decimal("-14742.00"), "URSSAF"),
        (date(2024, 12, 15), "URSSAF T4 2024", Decimal("-14742.00"), "URSSAF"),
        # Loyer bureau
        (date(2024, 1, 5), "Loyer bureau janvier", Decimal("-1200.00"), "Loyer"),
        (date(2024, 2, 5), "Loyer bureau février", Decimal("-1200.00"), "Loyer"),
        (date(2024, 3, 5), "Loyer bureau mars", Decimal("-1200.00"), "Loyer"),
        (date(2024, 4, 5), "Loyer bureau avril", Decimal("-1200.00"), "Loyer"),
        (date(2024, 5, 5), "Loyer bureau mai", Decimal("-1200.00"), "Loyer"),
        (date(2024, 6, 5), "Loyer bureau juin", Decimal("-1200.00"), "Loyer"),
        (date(2024, 7, 5), "Loyer bureau juillet", Decimal("-1200.00"), "Loyer"),
        (date(2024, 8, 5), "Loyer bureau août", Decimal("-1200.00"), "Loyer"),
        (date(2024, 9, 5), "Loyer bureau septembre", Decimal("-1200.00"), "Loyer"),
        (date(2024, 10, 5), "Loyer bureau octobre", Decimal("-1200.00"), "Loyer"),
        (date(2024, 11, 5), "Loyer bureau novembre", Decimal("-1200.00"), "Loyer"),
        (date(2024, 12, 5), "Loyer bureau décembre", Decimal("-1200.00"), "Loyer"),
        # Fournisseurs
        (date(2024, 1, 15), "OVH Cloud — Hébergement serveurs", Decimal("-320.00"), "Fournisseur"),
        (date(2024, 4, 15), "OVH Cloud — Hébergement T2", Decimal("-320.00"), "Fournisseur"),
        (date(2024, 7, 15), "OVH Cloud — Hébergement T3", Decimal("-320.00"), "Fournisseur"),
        (date(2024, 10, 15), "OVH Cloud — Hébergement T4", Decimal("-320.00"), "Fournisseur"),
        (date(2024, 3, 20), "Bureau Vallée — Fournitures", Decimal("-450.00"), "Fournisseur"),
        (date(2024, 9, 20), "Bureau Vallée — Fournitures", Decimal("-380.00"), "Fournisseur"),
        (date(2024, 6, 30), "Cabinet Dupont — Honoraires EC S1", Decimal("-3600.00"), "Fournisseur"),
        (date(2024, 12, 31), "Cabinet Dupont — Honoraires EC S2", Decimal("-3600.00"), "Fournisseur"),
        (date(2024, 1, 20), "AXA — Assurance RC Pro", Decimal("-2400.00"), "Assurance"),
        # TVA reversée
        (date(2024, 4, 20), "TVA T1 2024", Decimal("-3900.00"), "TVA"),
        (date(2024, 7, 20), "TVA T2 2024", Decimal("-3900.00"), "TVA"),
        (date(2024, 10, 20), "TVA T3 2024", Decimal("-3900.00"), "TVA"),
        # Achat matériel
        (date(2024, 3, 10), "LDLC — MacBook Pro développement", Decimal("-2800.00"), "Investissement"),
        (date(2024, 9, 1), "LDLC — Écrans + périphériques Clara", Decimal("-950.00"), "Investissement"),
    ]
    for d, lib, mt, cat in mouvements_2024:
        db.add(MouvementBancaire(entreprise_id=eid, date_operation=d, libelle=lib, montant=mt, categorie=cat, source="import_csv"))

    # 2025 — Solde positif
    mouvements_2025 = [
        # Encaissements clients 2025
        (date(2025, 1, 15), "Virement Vignobles Pomerol — FA-2024-013", Decimal("6960.00"), "Clients"),
        (date(2025, 2, 3), "Virement Ch. Agriculture — FA-2024-014", Decimal("9840.00"), "Clients"),
        (date(2025, 2, 18), "Virement Château Margaux — FA-2025-002", Decimal("14400.00"), "Clients"),
        (date(2025, 2, 28), "Virement Maïsadour — FA-2025-001", Decimal("28800.00"), "Clients"),
        (date(2025, 3, 20), "Virement Ch. Agriculture — FA-2025-003", Decimal("22200.00"), "Clients"),
        (date(2025, 4, 5), "Virement AgriTech — FA-2025-004", Decimal("18000.00"), "Clients"),
        (date(2025, 5, 20), "Virement Vignobles Pomerol — FA-2025-006", Decimal("10200.00"), "Clients"),
        (date(2025, 6, 5), "Virement Euralis — FA-2025-005", Decimal("42000.00"), "Clients"),
        (date(2025, 7, 1), "Virement Maïsadour — FA-2025-007", Decimal("19200.00"), "Clients"),
        (date(2025, 7, 5), "Virement Château Margaux — FA-2025-008", Decimal("26400.00"), "Clients"),
        (date(2025, 8, 18), "Virement Euralis — FA-2025-009", Decimal("15000.00"), "Clients"),
        (date(2025, 9, 18), "Virement Ch. Agriculture — FA-2025-010", Decimal("25200.00"), "Clients"),
        (date(2025, 10, 5), "Virement AgriTech — FA-2025-011", Decimal("7800.00"), "Clients"),
        (date(2025, 10, 20), "Virement Vignobles Pomerol — FA-2025-012", Decimal("11760.00"), "Clients"),
        (date(2025, 11, 20), "Virement Maïsadour — FA-2025-013", Decimal("33600.00"), "Clients"),
        (date(2025, 12, 18), "Virement Château Margaux — FA-2025-015", Decimal("17400.00"), "Clients"),
        (date(2025, 12, 28), "Virement Euralis — FA-2025-014", Decimal("38400.00"), "Clients"),
        # Salaires nets 2025 (mensuel, 4 employés)
        (date(2025, 1, 31), "Salaires janvier 2025", Decimal("-9016.00"), "Salaires"),
        (date(2025, 2, 28), "Salaires février 2025", Decimal("-9016.00"), "Salaires"),
        (date(2025, 3, 31), "Salaires mars 2025", Decimal("-9016.00"), "Salaires"),
        (date(2025, 4, 30), "Salaires avril 2025", Decimal("-9016.00"), "Salaires"),
        (date(2025, 5, 31), "Salaires mai 2025", Decimal("-9016.00"), "Salaires"),
        (date(2025, 6, 30), "Salaires juin 2025", Decimal("-9016.00"), "Salaires"),
        (date(2025, 7, 31), "Salaires juillet 2025", Decimal("-9016.00"), "Salaires"),
        (date(2025, 8, 31), "Salaires août 2025", Decimal("-9016.00"), "Salaires"),
        (date(2025, 9, 30), "Salaires septembre 2025", Decimal("-9016.00"), "Salaires"),
        (date(2025, 10, 31), "Salaires octobre 2025", Decimal("-9016.00"), "Salaires"),
        (date(2025, 11, 30), "Salaires novembre 2025", Decimal("-9016.00"), "Salaires"),
        (date(2025, 12, 31), "Salaires décembre 2025 + primes", Decimal("-12016.00"), "Salaires"),
        # URSSAF mensuel 2025
        (date(2025, 1, 15), "URSSAF janvier 2025", Decimal("-5250.00"), "URSSAF"),
        (date(2025, 2, 15), "URSSAF février 2025", Decimal("-5250.00"), "URSSAF"),
        (date(2025, 3, 15), "URSSAF mars 2025", Decimal("-5250.00"), "URSSAF"),
        (date(2025, 4, 15), "URSSAF avril 2025", Decimal("-5250.00"), "URSSAF"),
        (date(2025, 5, 15), "URSSAF mai 2025", Decimal("-5250.00"), "URSSAF"),
        (date(2025, 6, 15), "URSSAF juin 2025", Decimal("-5250.00"), "URSSAF"),
        (date(2025, 7, 15), "URSSAF juillet 2025", Decimal("-5250.00"), "URSSAF"),
        (date(2025, 8, 15), "URSSAF août 2025", Decimal("-5250.00"), "URSSAF"),
        (date(2025, 9, 15), "URSSAF septembre 2025", Decimal("-5250.00"), "URSSAF"),
        (date(2025, 10, 15), "URSSAF octobre 2025", Decimal("-5250.00"), "URSSAF"),
        (date(2025, 11, 15), "URSSAF novembre 2025", Decimal("-5250.00"), "URSSAF"),
        (date(2025, 12, 15), "URSSAF décembre 2025", Decimal("-5250.00"), "URSSAF"),
        # Loyer bureau (augmenté en 2025)
        (date(2025, 1, 5), "Loyer bureau janvier", Decimal("-1350.00"), "Loyer"),
        (date(2025, 2, 5), "Loyer bureau février", Decimal("-1350.00"), "Loyer"),
        (date(2025, 3, 5), "Loyer bureau mars", Decimal("-1350.00"), "Loyer"),
        (date(2025, 4, 5), "Loyer bureau avril", Decimal("-1350.00"), "Loyer"),
        (date(2025, 5, 5), "Loyer bureau mai", Decimal("-1350.00"), "Loyer"),
        (date(2025, 6, 5), "Loyer bureau juin", Decimal("-1350.00"), "Loyer"),
        (date(2025, 7, 5), "Loyer bureau juillet", Decimal("-1350.00"), "Loyer"),
        (date(2025, 8, 5), "Loyer bureau août", Decimal("-1350.00"), "Loyer"),
        (date(2025, 9, 5), "Loyer bureau septembre", Decimal("-1350.00"), "Loyer"),
        (date(2025, 10, 5), "Loyer bureau octobre", Decimal("-1350.00"), "Loyer"),
        (date(2025, 11, 5), "Loyer bureau novembre", Decimal("-1350.00"), "Loyer"),
        (date(2025, 12, 5), "Loyer bureau décembre", Decimal("-1350.00"), "Loyer"),
        # Fournisseurs
        (date(2025, 1, 15), "OVH Cloud — Hébergement T1", Decimal("-480.00"), "Fournisseur"),
        (date(2025, 4, 15), "OVH Cloud — Hébergement T2", Decimal("-480.00"), "Fournisseur"),
        (date(2025, 7, 15), "OVH Cloud — Hébergement T3", Decimal("-480.00"), "Fournisseur"),
        (date(2025, 10, 15), "OVH Cloud — Hébergement T4", Decimal("-480.00"), "Fournisseur"),
        (date(2025, 2, 10), "AWS — Services cloud dev", Decimal("-650.00"), "Fournisseur"),
        (date(2025, 5, 10), "AWS — Services cloud dev", Decimal("-720.00"), "Fournisseur"),
        (date(2025, 8, 10), "AWS — Services cloud dev", Decimal("-780.00"), "Fournisseur"),
        (date(2025, 11, 10), "AWS — Services cloud dev", Decimal("-850.00"), "Fournisseur"),
        (date(2025, 3, 20), "Bureau Vallée — Fournitures", Decimal("-520.00"), "Fournisseur"),
        (date(2025, 9, 20), "Bureau Vallée — Fournitures", Decimal("-410.00"), "Fournisseur"),
        (date(2025, 6, 30), "Cabinet Dupont — Honoraires EC S1", Decimal("-4200.00"), "Fournisseur"),
        (date(2025, 12, 31), "Cabinet Dupont — Honoraires EC S2", Decimal("-4200.00"), "Fournisseur"),
        (date(2025, 1, 20), "AXA — Assurance RC Pro 2025", Decimal("-2800.00"), "Assurance"),
        # TVA reversée
        (date(2025, 4, 20), "TVA T1 2025", Decimal("-9400.00"), "TVA"),
        (date(2025, 7, 20), "TVA T2 2025", Decimal("-9400.00"), "TVA"),
        (date(2025, 10, 20), "TVA T3 2025", Decimal("-9400.00"), "TVA"),
        # IS acomptes
        (date(2025, 3, 15), "IS — Acompte 1", Decimal("-2800.00"), "IS"),
        (date(2025, 6, 15), "IS — Acompte 2", Decimal("-2800.00"), "IS"),
        (date(2025, 9, 15), "IS — Acompte 3", Decimal("-2800.00"), "IS"),
        (date(2025, 12, 15), "IS — Acompte 4", Decimal("-2800.00"), "IS"),
    ]
    for d, lib, mt, cat in mouvements_2025:
        db.add(MouvementBancaire(entreprise_id=eid, date_operation=d, libelle=lib, montant=mt, categorie=cat, source="nordigen"))

    # ── ÉCRITURES COMPTABLES (exemples clés) ──
    ecritures_data = [
        # Ventes 2024
        (date(2024, 1, 15), "VE-001", "411000", "706000", "Château Margaux — Audit digitalisation", Decimal("4500.00")),
        (date(2024, 5, 15), "VE-005", "411000", "706000", "Château Margaux — Suivi parcellaire Ph.2", Decimal("12000.00")),
        (date(2024, 10, 1), "VE-010", "411000", "706000", "Maïsadour — Module adhérents", Decimal("18000.00")),
        # Ventes 2025
        (date(2025, 1, 10), "VE-015", "411000", "706000", "Maïsadour — Stocks & logistique", Decimal("24000.00")),
        (date(2025, 4, 1), "VE-019", "411000", "706000", "Euralis — Déploiement national", Decimal("35000.00")),
        (date(2025, 11, 1), "VE-028", "411000", "706000", "Euralis — API traçabilité GMS", Decimal("32000.00")),
        # Charges
        (date(2024, 1, 31), "SA-001", "641000", "421000", "Salaires janvier 2024", Decimal("10500.00")),
        (date(2024, 1, 31), "SA-002", "645000", "431000", "Charges sociales janvier 2024", Decimal("4410.00")),
        (date(2025, 1, 31), "SA-013", "641000", "421000", "Salaires janvier 2025", Decimal("12500.00")),
        (date(2025, 1, 31), "SA-014", "645000", "431000", "Charges sociales janvier 2025", Decimal("5250.00")),
        # Loyer
        (date(2024, 1, 5), "CH-001", "613000", "512000", "Loyer bureau janvier 2024", Decimal("1200.00")),
        (date(2025, 1, 5), "CH-013", "613000", "512000", "Loyer bureau janvier 2025", Decimal("1350.00")),
        # Fournisseurs
        (date(2024, 1, 15), "AC-001", "604000", "401000", "OVH Cloud — Hébergement T1", Decimal("320.00")),
        (date(2025, 6, 30), "AC-020", "604000", "401000", "Cabinet Dupont — Honoraires S1", Decimal("4200.00")),
    ]
    for d, num, debit, credit, lib, mt in ecritures_data:
        db.add(Ecriture(
            entreprise_id=eid, date_ecriture=d, numero_piece=num,
            compte_debit=debit, compte_credit=credit, libelle=lib, montant=mt,
        ))

    db.commit()
    return {
        "clients": len(clients_data),
        "fournisseurs": len(fournisseurs_data),
        "employes": len(employes_data),
        "factures_2024": len(factures_2024),
        "factures_2025": len(factures_2025),
        "bons_commande": len(bons_commande),
        "declarations": "TVA + URSSAF + IS + DSN",
        "mouvements_bancaires": len(mouvements_2024) + len(mouvements_2025),
        "ecritures": len(ecritures_data),
    }
