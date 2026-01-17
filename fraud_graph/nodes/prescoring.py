"""Nodes de pré-scoring en parallèle."""

import math
from email.utils import parsedate_to_datetime
from typing import List

from ..state import FraudState

PHISHING_KEYWORDS: List[str] = [
    "bank", "account", "verify", "locked", "security", "suspended",
    "subscription", "renewal", "payment", "update", "card",
    # Parcel customs
    "delivery", "customs", "parcel", "fee", "dhl", "fedex", "ups", "courier",
    # Identity verification
    "identity", "id", "verification", "otp",
    # BEC urgent invoice
    "invoice", "urgent", "overdue", "accounting", "billing", "supplier",
    # Generic
    "click here", "verify account", "account locked", "confirm", "fraud",
    "paypal", "urgente", "verifica", "conferma",
]


def analyze_amount_merchant(state: FraudState) -> FraudState:
    """Analyse du montant et du merchant (pré-scoring parallèle).
    
    Détecte les fraud signals: new_dest, new_merchant, amount_anomaly, post_withdrawal.
    
    Args:
        state: État actuel du graphe
        
    Returns:
        État mis à jour avec amount_merchant_features
    """
    transaction = state.get("transaction", {})
    user_profile = state.get("user_profile", {})
    
    if not transaction:
        return {
            "amount_merchant_features": {},
        }
    
    tx_amount = transaction.get("amount", 0)
    tx_type = transaction.get("transaction_type", "")
    balance_after = transaction.get("balance_after", 0)
    sender_salary = user_profile.get("salary", 0)
    description = transaction.get("description", "").lower()
    recipient_iban = transaction.get("recipient_iban", "")
    recipient_id = transaction.get("recipient_id", "")
    
    # Récupération de l'historique des transactions
    other_transactions = user_profile.get("other_transactions", [])
    
    # Détection de new_dest (nouveau destinataire jamais vu)
    new_dest = 0
    if recipient_iban or recipient_id:
        # Vérifier si ce destinataire a déjà été utilisé
        seen_recipients = set()
        for other_tx in other_transactions:
            other_iban = other_tx.get("recipient_iban", "")
            other_id = other_tx.get("recipient_id", "")
            if other_iban:
                seen_recipients.add(other_iban)
            if other_id:
                seen_recipients.add(other_id)
        
        current_recipient = recipient_iban or recipient_id
        if current_recipient and current_recipient not in seen_recipients:
            new_dest = 1
    
    # Détection de new_merchant (nouveau merchant e-commerce)
    new_merchant = 0
    if tx_type in ["e-commerce", "pagamento e-comm"]:
        # Utiliser description, recipient_id ou location comme identifiant du merchant
        merchant_identifier = None
        if description:
            merchant_identifier = description.split()[0].lower() if description.split() else None
        elif recipient_id:
            merchant_identifier = recipient_id.lower()
        elif transaction.get("location", ""):
            merchant_identifier = transaction.get("location", "").lower()
        
        if merchant_identifier:
            # Vérifier si ce merchant a déjà été utilisé
            seen_merchants = set()
            for other_tx in other_transactions:
                if other_tx.get("transaction_type", "") in ["e-commerce", "pagamento e-comm"]:
                    other_desc = other_tx.get("description", "").lower()
                    other_recipient = other_tx.get("recipient_id", "").lower()
                    other_location = other_tx.get("location", "").lower()
                    
                    # Utiliser le premier identifiant disponible
                    other_merchant = None
                    if other_desc:
                        other_merchant = other_desc.split()[0] if other_desc.split() else None
                    elif other_recipient:
                        other_merchant = other_recipient
                    elif other_location:
                        other_merchant = other_location
                    
                    if other_merchant:
                        seen_merchants.add(other_merchant)
            
            if merchant_identifier not in seen_merchants:
                new_merchant = 1
    
    # Détection de post_withdrawal (transaction après retrait suspect)
    post_withdrawal = 0
    if tx_type in ["pagamento fisico", "e-commerce", "in-person payment"]:
        # Chercher des retraits récents (dernières 48h)
        recent_withdrawals = [
            tx for tx in other_transactions
            if tx.get("transaction_type") in ["prelievo", "withdrawal"]
            and tx.get("amount", 0) > 200  # Retrait important
        ]
        if recent_withdrawals:
            post_withdrawal = 1
    
    # Détection de pattern_multiple_withdrawals (plusieurs retraits rapprochés)
    pattern_multiple_withdrawals = 0
    if tx_type in ["prelievo", "withdrawal"]:
        # Compter les retraits dans l'historique (inclure la transaction courante dans le compte)
        recent_withdrawals = [
            tx for tx in other_transactions
            if tx.get("transaction_type") in ["prelievo", "withdrawal"]
        ]
        # Si on a au moins 1 autre retrait, c'est un pattern multiple (la transaction courante + 1 autre = 2)
        if len(recent_withdrawals) >= 1:  # Au moins 1 autre retrait (donc 2 au total avec la courante)
            pattern_multiple_withdrawals = 1
    
    # Features montant et merchant
    features = {
        "account_drained": 1 if balance_after == 0.0 else 0,
        "balance_very_low": 1 if 0 < balance_after < 10 else 0,
        "abnormal_amount": 1 if sender_salary > 0 and tx_amount > sender_salary * 0.1 else 0,  # Réduit à 10% pour être plus permissif
        "high_amount": 1 if tx_amount > 500 else 0,
        "large_withdrawal": 1 if tx_type == "prelievo" and tx_amount > 300 else 0,
        "suspicious_type": 1 if tx_type in ["bonifico", "transfer"] else 0,
        "balance_ratio": balance_after / max(sender_salary / 12, 1) if sender_salary > 0 else 1.0,
        "unknown_merchant": 1 if not description or len(description) < 3 else 0,
        "suspicious_keywords": 1 if any(kw in description for kw in ["urgent", "verify", "suspended", "invoice", "security"]) else 0,
        # Nouveaux fraud signals
        "new_dest": new_dest,
        "new_merchant": new_merchant,
        "post_withdrawal": post_withdrawal,
        "pattern_multiple_withdrawals": pattern_multiple_withdrawals,
    }
    
    return {
        "amount_merchant_features": features,
    }


def analyze_country_travel(state: FraudState) -> FraudState:
    """Analyse du pays et des déplacements (pré-scoring parallèle).
    
    Détecte les fraud signals: location_anomaly, impossible_travel, new_venue.
    
    Args:
        state: État actuel du graphe
        
    Returns:
        État mis à jour avec country_travel_features
    """
    transaction = state.get("transaction", {})
    user_profile = state.get("user_profile", {})
    location_data = state.get("location_data", [])
    
    if not transaction:
        return {
            "country_travel_features": {},
        }
    
    tx_location = transaction.get("location", "")
    tx_type = transaction.get("transaction_type", "")
    user_residence = user_profile.get("residence", {})
    user_city = user_residence.get("city", "")
    tx_lat = transaction.get("lat")
    tx_lng = transaction.get("lng")
    
    # Récupération de l'historique des transactions
    other_transactions = user_profile.get("other_transactions", [])
    
    # Détection de new_venue (nouveau lieu physique jamais vu)
    new_venue = 0
    if tx_type in ["pagamento fisico", "in-person payment"] and tx_location:
        # Vérifier si ce lieu a déjà été utilisé
        seen_venues = set()
        for other_tx in other_transactions:
            if other_tx.get("transaction_type") in ["pagamento fisico", "in-person payment"]:
                other_location = other_tx.get("location", "")
                if other_location:
                    seen_venues.add(other_location.lower())
        
        if tx_location.lower() not in seen_venues:
            new_venue = 1
    
    # Features pays et voyage
    features = {
        "location_missing": 1 if not tx_location else 0,
        "location_mismatch": 1 if tx_location and user_city and tx_location.lower() != user_city.lower() else 0,
        "gps_available": 1 if tx_lat and tx_lng else 0,
        "gps_contradiction": 0,  # À calculer si on a les coordonnées utilisateur
        "new_venue": new_venue,
    }
    
    # Analyse des locations GPS
    # Si GPS disponible, utiliser GPS. Sinon, utiliser les noms de villes
    user_lat = user_residence.get("lat")
    user_lng = user_residence.get("lng")
    
    if user_lat and user_lng and tx_lat and tx_lng:
        # Calcul de distance approximative (simplifié)
        lat_diff = abs(float(user_lat) - float(tx_lat))
        lng_diff = abs(float(user_lng) - float(tx_lng))
        distance_km = math.sqrt(lat_diff**2 + lng_diff**2) * 111  # Approximation
        
        features["distance_from_residence"] = distance_km
        features["impossible_travel"] = 1 if distance_km > 1000 else 0  # > 1000km = impossible
        features["location_anomaly"] = 1 if distance_km > 100 else 0  # > 100km = anomalie
    elif tx_location and user_city:
        # Fallback : utiliser les noms de villes si GPS manquant
        # Extraire le nom de la ville de la location de transaction
        tx_city = tx_location.split(" - ")[0].strip().lower() if " - " in tx_location else tx_location.lower()
        user_city_lower = user_city.lower()
        
        # Si les villes sont différentes, c'est une anomalie de localisation
        if tx_city != user_city_lower:
            # Distance approximative basée sur les villes italiennes connues
            # Modena -> Genova ~150km, Modena -> Palermo ~1000km, etc.
            # On considère comme impossible_travel si les villes sont très éloignées
            # et location_anomaly si simplement différentes
            features["location_anomaly"] = 1
            # Pour impossible_travel, on se base sur des villes connues pour être très éloignées
            # (ex: Modena-Palermo, Milan-Palermo, etc.)
            major_cities_north = ["modena", "milano", "torino", "genova", "venezia", "bologna"]
            major_cities_south = ["palermo", "catania", "napoli", "bari"]
            
            tx_is_north = any(city in tx_city for city in major_cities_north)
            tx_is_south = any(city in tx_city for city in major_cities_south)
            user_is_north = any(city in user_city_lower for city in major_cities_north)
            user_is_south = any(city in user_city_lower for city in major_cities_south)
            
            # Si une transaction est au nord et l'autre au sud (ou vice versa), c'est impossible_travel
            if (tx_is_north and user_is_south) or (tx_is_south and user_is_north):
                features["impossible_travel"] = 1
            else:
                features["impossible_travel"] = 0
    
    return {
        "country_travel_features": features,
    }


def analyze_sms_email(state: FraudState) -> FraudState:
    """Analyse des SMS et emails (pré-scoring parallèle).
    
    Détecte les fraud signals: time_correlation (transaction peu après phishing).
    
    Args:
        state: État actuel du graphe
        
    Returns:
        État mis à jour avec sms_email_features
    """
    from datetime import datetime, timedelta
    
    sms_data = state.get("sms_data", [])
    email_data = state.get("email_data", [])
    transaction = state.get("transaction", {})
    
    tx_timestamp = transaction.get("timestamp", "")
    
    suspicious_sms_count = 0
    suspicious_email_count = 0
    time_correlation = 0  # Transaction peu après phishing
    
    # Analyse SMS
    phishing_sms_times = []
    for sms in sms_data:
        sms_content = sms.get("sms", "").lower()
        if any(kw in sms_content for kw in PHISHING_KEYWORDS):
            suspicious_sms_count += 1
            # Extraire timestamp si disponible
            sms_time = sms.get("datetime") or sms.get("timestamp")
            if sms_time:
                phishing_sms_times.append(sms_time)
    
    # Analyse Email
    phishing_email_times = []
    for email in email_data:
        email_content = email.get("mail", "").lower()
        # Vérifier les keywords de phishing (plus permissif)
        is_phishing = any(kw in email_content for kw in PHISHING_KEYWORDS)
        
        # Vérifier aussi les patterns spécifiques (parcel customs, identity verification, etc.)
        if not is_phishing:
            # Patterns spécifiques pour les scénarios de fraude
            if "customs" in email_content and "fee" in email_content:
                is_phishing = True
            elif "identity" in email_content and "verification" in email_content:
                is_phishing = True
            elif "parcel" in email_content and ("fee" in email_content or "customs" in email_content):
                is_phishing = True
            elif "unpaid" in email_content and ("customs" in email_content or "fee" in email_content):
                is_phishing = True
        
        if is_phishing:
            suspicious_email_count += 1
            # Extraire timestamp si disponible (chercher dans le contenu de l'email aussi)
            email_time = email.get("date") or email.get("timestamp")
            
            # Si pas de timestamp direct, essayer de l'extraire du contenu de l'email
            if not email_time and "date:" in email_content:
                try:
                    # Chercher "Date: ..." dans le contenu
                    date_line = [line for line in email_content.split("\n") if "date:" in line.lower()]
                    if date_line:
                        # Format: "Date: Fri, 19 Dec 2025 21:24:44 +0100"
                        date_str = date_line[0].split("date:")[-1].strip()
                        # parsedate_to_datetime retourne un datetime aware, on le convertit en string ISO
                        parsed_dt = parsedate_to_datetime(date_str)
                        # S'assurer que c'est en UTC
                        if parsed_dt.tzinfo is None:
                            from datetime import timezone
                            parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                        else:
                            parsed_dt = parsed_dt.astimezone(timezone.utc)
                        email_time = parsed_dt.isoformat()
                except Exception:
                    pass
            
            if email_time:
                phishing_email_times.append(email_time)
    
    # Détection de time_correlation (transaction dans les 4h après phishing)
    if tx_timestamp and (phishing_sms_times or phishing_email_times):
        try:
            from datetime import timezone
            
            # Parser le timestamp de la transaction en UTC
            tx_timestamp_clean = tx_timestamp.replace('Z', '+00:00') if tx_timestamp.endswith('Z') else tx_timestamp
            tx_time = datetime.fromisoformat(tx_timestamp_clean)
            # S'assurer que c'est en UTC
            if tx_time.tzinfo is None:
                tx_time = tx_time.replace(tzinfo=timezone.utc)
            else:
                tx_time = tx_time.astimezone(timezone.utc)
            
            # Vérifier tous les timestamps de phishing
            all_phishing_times = phishing_sms_times + phishing_email_times
            for phishing_time_str in all_phishing_times:
                try:
                    if isinstance(phishing_time_str, str):
                        # Nettoyer le timestamp
                        phishing_time_clean = phishing_time_str.replace('Z', '+00:00') if phishing_time_str.endswith('Z') else phishing_time_str
                        phishing_time = datetime.fromisoformat(phishing_time_clean)
                        # S'assurer que c'est en UTC
                        if phishing_time.tzinfo is None:
                            phishing_time = phishing_time.replace(tzinfo=timezone.utc)
                        else:
                            phishing_time = phishing_time.astimezone(timezone.utc)
                    else:
                        continue
                    
                    time_diff = tx_time - phishing_time
                    # Transaction dans les 4 heures après phishing (240 minutes)
                    if timedelta(minutes=0) <= time_diff <= timedelta(hours=4):
                        time_correlation = 1
                        break
                except (ValueError, AttributeError, TypeError) as e:
                    # Ignorer les erreurs de parsing
                    continue
        except (ValueError, AttributeError, TypeError):
            pass
    
    features = {
        "has_sms": 1 if sms_data else 0,
        "has_email": 1 if email_data else 0,
        "suspicious_sms_count": suspicious_sms_count,
        "suspicious_email_count": suspicious_email_count,
        "phishing_indicators": 1 if suspicious_sms_count > 0 or suspicious_email_count > 0 else 0,
        "total_communications": len(sms_data) + len(email_data),
        "time_correlation": time_correlation,  # Nouveau fraud signal
    }
    
    return {
        "sms_email_features": features,
    }
