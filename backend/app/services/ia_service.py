"""
Service IA — Analyse financière et suggestions via Claude
"""
import anthropic
from app.core.config import settings


def get_client():
    if not settings.ANTHROPIC_API_KEY:
        return None
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def analyser_ecritures(ecritures: list) -> dict:
    """Analyse les écritures comptables et détecte les anomalies."""
    flags = []
    
    # Détection doublons
    seen = {}
    for e in ecritures:
        key = f"{e.get('libelle','')[:30]}_{e.get('montant')}"
        if key in seen:
            flags.append({
                "type": "doublon",
                "message": f"Doublon probable avec l'écriture {seen[key]}",
                "ecriture_id": e.get("id"),
                "severite": "critique"
            })
        seen[key] = e.get("id")
    
    # Compte incorrect (achat > 500€ en charges au lieu d'immobilisation)
    for e in ecritures:
        if e.get("compte_debit", "").startswith("607") and float(e.get("montant", 0)) > 500:
            flags.append({
                "type": "compte_incorrect",
                "message": f"Achat {e.get('montant')}€ > 500€ : à immobiliser en 215xxx plutôt que 607xxx",
                "ecriture_id": e.get("id"),
                "severite": "critique",
                "correction_suggeree": "215400"
            })
    
    return {"flags": flags, "nb_anomalies": len(flags)}


def question_ia(question: str, contexte_financier: dict = None) -> str:
    """Répond à une question de gestion en langage naturel."""
    client = get_client()
    if not client:
        return "Clé API Anthropic non configurée."
    
    system = """Tu es le conseiller financier IA de Bras Droit, un logiciel de gestion pour PME françaises.
Tu analyses les données comptables, fiscales et RH de l'entreprise et tu donnes des conseils précis, chiffrés et actionnables.
Tu connais parfaitement le droit fiscal français (TVA, IS, liasse fiscale), le droit social (URSSAF, DSN, paie, conventions collectives) et la comptabilité PCG.
Réponds en français, de façon concise et professionnelle. Toujours chiffrer les impacts quand c'est possible."""
    
    user_content = question
    if contexte_financier:
        user_content = f"""Contexte financier de l'entreprise :
{contexte_financier}

Question : {question}"""
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=system,
        messages=[{"role": "user", "content": user_content}]
    )
    
    return message.content[0].text


def generer_relance(
    client_nom: str,
    facture_numero: str,
    montant: float,
    date_echeance: str,
    jours_retard: int,
    type_relance: str  # R1, R2, R3
) -> dict:
    """Génère un mail de relance personnalisé via IA."""
    client = get_client()
    if not client:
        # Fallback sans IA
        templates = {
            "R1": f"Bonjour,\n\nNous vous contactons concernant la facture {facture_numero} de {montant}€ TTC échue le {date_echeance}.\nPourriez-vous nous confirmer la date de règlement prévue?\n\nCordialement",
            "R2": f"Bonjour,\n\nMalgré notre premier rappel, la facture {facture_numero} de {montant}€ reste impayée ({jours_retard}j de retard).\nNous vous demandons de régler sous 8 jours.\n\nCordialement",
            "R3": f"Monsieur/Madame,\n\nNous vous mettons en DEMEURE de régler la facture {facture_numero} de {montant}€ + intérêts de retard sous 15 jours, faute de quoi une procédure judiciaire sera engagée."
        }
        return {
            "objet": f"{'Rappel' if type_relance=='R1' else 'Relance' if type_relance=='R2' else 'MISE EN DEMEURE'} — Facture {facture_numero}",
            "corps": templates.get(type_relance, templates["R1"])
        }
    
    prompt = f"""Génère un mail de relance {type_relance} pour :
- Client : {client_nom}
- Facture : {facture_numero}
- Montant : {montant}€ TTC
- Échéance : {date_echeance}
- Retard : {jours_retard} jours

Ton de la relance selon le type :
- R1 : cordial et professionnel (premier rappel)
- R2 : ferme mais respectueux (deuxième relance)
- R3 : mise en demeure avec mention de procédure judiciaire

Réponds uniquement avec un JSON contenant "objet" et "corps" du mail. Pas de markdown."""
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    import json
    try:
        return json.loads(message.content[0].text)
    except Exception:
        return {"objet": f"Relance {type_relance} — {facture_numero}", "corps": message.content[0].text}
