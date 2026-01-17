"""Nodes de pré-scoring en parallèle."""

import math
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
    if tx_type in ["e-commerce", "pagamento e-comm"] and description:
        # Vérifier si ce merchant a déjà été utilisé
        seen_merchants = set()
        for other_tx in other_transactions:
            if other_tx.get("transaction_type", "") in ["e-commerce", "pagamento e-comm"]:
                other_desc = other_tx.get("description", "").lower()
                if other_desc:
                    # Extraire le nom du merchant (premiers mots de la description)
                    merchant_name = other_desc.split()[0] if other_desc.split() else ""
                    if merchant_name:
                        seen_merchants.add(merchant_name)
        
        current_merchant = description.split()[0] if description.split() else ""
        if current_merchant and current_merchant not in seen_merchants:
            new_merchant = 1
    
    # Détection de post_withdrawal (transaction après retrait suspect)
    post_withdrawal = 0
    if tx_type in ["pagamento fisico", "e-commerce"]:
        # Chercher des retraits récents (dernières 48h)
        recent_withdrawals = [
            tx for tx in other_transactions
            if tx.get("transaction_type") == "prelievo"
            and tx.get("amount", 0) > 200  # Retrait important
        ]
        if recent_withdrawals:
            post_withdrawal = 1
    
    # Détection de pattern_multiple_withdrawals (plusieurs retraits rapprochés)
    pattern_multiple_withdrawals = 0
    if tx_type == "prelievo":
        # Compter les retraits dans les dernières 24h
        recent_withdrawals = [
            tx for tx in other_transactions
            if tx.get("transaction_type") == "prelievo"
        ]
        if len(recent_withdrawals) >= 2:  # Au moins 2 retraits récents
            pattern_multiple_withdrawals = 1
    
    # Features montant et merchant
    features = {
        "account_drained": 1 if balance_after == 0.0 else 0,
        "balance_very_low": 1 if 0 < balance_after < 10 else 0,
        "abnormal_amount": 1 if sender_salary > 0 and tx_amount > sender_salary * 0.3 else 0,
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
    if tx_type == "pagamento fisico" and tx_location:
        # Vérifier si ce lieu a déjà été utilisé
        seen_venues = set()
        for other_tx in other_transactions:
            if other_tx.get("transaction_type") == "pagamento fisico":
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
    if location_data and user_residence:
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
        if any(kw in email_content for kw in PHISHING_KEYWORDS):
            suspicious_email_count += 1
            # Extraire timestamp si disponible
            email_time = email.get("date") or email.get("timestamp")
            if email_time:
                phishing_email_times.append(email_time)
    
    # Détection de time_correlation (transaction dans les 4h après phishing)
    if tx_timestamp and (phishing_sms_times or phishing_email_times):
        try:
            tx_time = datetime.fromisoformat(tx_timestamp.replace('Z', '+00:00'))
            
            # Vérifier tous les timestamps de phishing
            all_phishing_times = phishing_sms_times + phishing_email_times
            for phishing_time_str in all_phishing_times:
                try:
                    if isinstance(phishing_time_str, str):
                        phishing_time = datetime.fromisoformat(phishing_time_str.replace('Z', '+00:00'))
                    else:
                        continue
                    
                    time_diff = tx_time - phishing_time
                    # Transaction dans les 4 heures après phishing (240 minutes)
                    if timedelta(minutes=0) <= time_diff <= timedelta(hours=4):
                        time_correlation = 1
                        break
                except (ValueError, AttributeError):
                    continue
        except (ValueError, AttributeError):
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
