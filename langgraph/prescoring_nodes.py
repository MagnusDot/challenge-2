"""Nodes de pré-scoring en parallèle."""

from typing import Dict, Any, List
import re

from .state import FraudState


def analyze_amount_merchant(state: FraudState) -> FraudState:
    """Analyse du montant et du merchant (pré-scoring parallèle).
    
    Args:
        state: État actuel du graphe
        
    Returns:
        État mis à jour avec amount_merchant_features
    """
    transaction = state.get("transaction", {})
    user_profile = state.get("user_profile", {})
    
    if not transaction:
        return {
            **state,
            "amount_merchant_features": {},
        }
    
    tx_amount = transaction.get("amount", 0)
    tx_type = transaction.get("transaction_type", "")
    balance_after = transaction.get("balance_after", 0)
    sender_salary = user_profile.get("salary", 0)
    description = transaction.get("description", "").lower()
    
    # Features montant et merchant
    features = {
        "account_drained": 1 if balance_after == 0.0 else 0,
        "balance_very_low": 1 if 0 < balance_after < 10 else 0,
        "abnormal_amount": 1 if sender_salary > 0 and tx_amount > sender_salary * 0.3 else 0,
        "high_amount": 1 if tx_amount > 500 else 0,
        "large_withdrawal": 1 if tx_type == "prelievo" and tx_amount > 300 else 0,
        "suspicious_type": 1 if tx_type in ["bonifico", "transfer"] else 0,
        "balance_ratio": balance_after / max(sender_salary / 12, 1) if sender_salary > 0 else 1.0,
        # Merchant analysis
        "unknown_merchant": 1 if not description or len(description) < 3 else 0,
        "suspicious_keywords": 1 if any(kw in description for kw in ["urgent", "verify", "suspended"]) else 0,
    }
    
    return {
        **state,
        "amount_merchant_features": features,
    }


def analyze_country_travel(state: FraudState) -> FraudState:
    """Analyse du pays et des déplacements (pré-scoring parallèle).
    
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
            **state,
            "country_travel_features": {},
        }
    
    tx_location = transaction.get("location", "")
    user_residence = user_profile.get("residence", {})
    user_city = user_residence.get("city", "")
    tx_lat = transaction.get("lat")
    tx_lng = transaction.get("lng")
    
    # Features pays et voyage
    features = {
        "location_missing": 1 if not tx_location else 0,
        "location_mismatch": 1 if tx_location and user_city and tx_location.lower() != user_city.lower() else 0,
        # GPS analysis
        "gps_available": 1 if tx_lat and tx_lng else 0,
        "gps_contradiction": 0,  # À calculer si on a les coordonnées utilisateur
    }
    
    # Analyse des locations GPS
    if location_data and user_residence:
        user_lat = user_residence.get("lat")
        user_lng = user_residence.get("lng")
        
        if user_lat and user_lng and tx_lat and tx_lng:
            # Calcul de distance approximative (simplifié)
            import math
            lat_diff = abs(float(user_lat) - float(tx_lat))
            lng_diff = abs(float(user_lng) - float(tx_lng))
            distance_km = math.sqrt(lat_diff**2 + lng_diff**2) * 111  # Approximation
            
            features["distance_from_residence"] = distance_km
            features["impossible_travel"] = 1 if distance_km > 1000 else 0  # > 1000km = impossible
    
    return {
        **state,
        "country_travel_features": features,
    }


def analyze_sms_email(state: FraudState) -> FraudState:
    """Analyse des SMS et emails (pré-scoring parallèle).
    
    Args:
        state: État actuel du graphe
        
    Returns:
        État mis à jour avec sms_email_features
    """
    sms_data = state.get("sms_data", [])
    email_data = state.get("email_data", [])
    
    # Mots-clés suspects dans SMS/Email
    phishing_keywords = [
        "verify", "suspended", "urgent", "click here", "verify account",
        "account locked", "confirm", "update", "security", "fraud",
        "paypal", "bank", "urgente", "verifica", "conferma"
    ]
    
    suspicious_sms_count = 0
    suspicious_email_count = 0
    
    # Analyse SMS
    for sms in sms_data:
        sms_content = sms.get("sms", "").lower()
        if any(kw in sms_content for kw in phishing_keywords):
            suspicious_sms_count += 1
    
    # Analyse Email
    for email in email_data:
        email_content = email.get("mail", "").lower()
        if any(kw in email_content for kw in phishing_keywords):
            suspicious_email_count += 1
    
    features = {
        "has_sms": 1 if sms_data else 0,
        "has_email": 1 if email_data else 0,
        "suspicious_sms_count": suspicious_sms_count,
        "suspicious_email_count": suspicious_email_count,
        "phishing_indicators": 1 if suspicious_sms_count > 0 or suspicious_email_count > 0 else 0,
        "total_communications": len(sms_data) + len(email_data),
    }
    
    return {
        **state,
        "sms_email_features": features,
    }
