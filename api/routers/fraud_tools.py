"""Outils API spécialisés pour l'aide à la détection de fraude."""

import logging
import math
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

from api.utils.data_loader import (
    load_transactions,
    load_users,
    load_emails,
    load_sms,
    load_locations
)
from api.utils.response_formatter import format_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fraud-tools", tags=["fraud-detection"])


# Modèles Pydantic pour les requêtes
class TimeCorrelationRequest(BaseModel):
    transaction_id: str
    time_window_hours: float = 4.0


class NewMerchantRequest(BaseModel):
    transaction_id: str


class LocationAnomalyRequest(BaseModel):
    transaction_id: str
    use_city_fallback: bool = True


class WithdrawalPatternRequest(BaseModel):
    transaction_id: str
    time_window_hours: float = 2.0


class PhishingIndicatorsRequest(BaseModel):
    transaction_id: str
    time_window_hours: float = 4.0


# Distances approximatives entre villes italiennes principales (en km)
ITALIAN_CITY_DISTANCES = {
    ("Roma", "Milano"): 570,
    ("Roma", "Napoli"): 220,
    ("Roma", "Torino"): 670,
    ("Roma", "Palermo"): 530,
    ("Roma", "Genova"): 500,
    ("Roma", "Bologna"): 380,
    ("Roma", "Firenze"): 280,
    ("Roma", "Bari"): 450,
    ("Roma", "Catania"): 530,
    ("Milano", "Napoli"): 780,
    ("Milano", "Torino"): 140,
    ("Milano", "Genova"): 150,
    ("Milano", "Bologna"): 210,
    ("Milano", "Firenze"): 300,
    ("Napoli", "Bari"): 250,
    ("Napoli", "Palermo"): 420,
    ("Firenze", "Bologna"): 100,
    ("Firenze", "Genova"): 270,
    ("Modena", "Genova"): 150,
    ("Modena", "Bologna"): 40,
    ("Modena", "Milano"): 180,
    ("Modena", "Firenze"): 100,
    ("Sant'Agata di Militello", "Roma"): 700,
    ("Sant'Agata di Militello", "Milano"): 1100,
    ("Sant'Agata di Militello", "Napoli"): 500,
    ("Sant'Agata di Militello", "Palermo"): 150,
    ("Sant'Agata di Militello", "Catania"): 100,
    ("Sant'Agata di Militello", "Bari"): 400,
    ("Sant'Agata di Militello", "Genova"): 1000,
    ("Sant'Agata di Militello", "Bologna"): 900,
    ("Sant'Agata di Militello", "Firenze"): 850,
    ("Sant'Agata di Militello", "Modena"): 900,
}


def calculate_city_distance(city1: str, city2: str) -> Optional[float]:
    """Calcule la distance approximative entre deux villes italiennes."""
    if not city1 or not city2:
        return None
    
    city1_clean = city1.split(" - ")[0].strip()  # Enlever les détails après " - "
    city2_clean = city2.split(" - ")[0].strip()
    
    if city1_clean == city2_clean:
        return 0.0
    
    # Chercher dans les deux sens
    distance = ITALIAN_CITY_DISTANCES.get((city1_clean, city2_clean))
    if distance is None:
        distance = ITALIAN_CITY_DISTANCES.get((city2_clean, city1_clean))
    
    return distance


def calculate_gps_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calcule la distance en km entre deux coordonnées GPS (formule de Haversine)."""
    R = 6371  # Rayon de la Terre en km
    
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


@router.post("/check-time-correlation")
async def check_time_correlation(request: TimeCorrelationRequest):
    """Vérifie la corrélation temporelle entre emails/SMS de phishing et une transaction."""
    try:
        transactions = load_transactions()
        emails = load_emails()
        sms_list = load_sms()
        users = load_users()
        
        transaction = next((t for t in transactions if t.transaction_id == request.transaction_id), None)
        if not transaction:
            raise HTTPException(status_code=404, detail=f"Transaction {request.transaction_id} not found")
        
        # Trouver l'utilisateur
        sender = None
        if transaction.sender_id:
            sender = next((u for u in users if u.biotag == transaction.sender_id), None)
        
        if not sender:
            return {
                "transaction_id": request.transaction_id,
                "time_correlation": False,
                "reason": "Sender not found",
                "phishing_events": []
            }
        
        # Mots-clés de phishing
        phishing_keywords = [
            "bank", "account", "verify", "locked", "security", "suspended",
            "subscription", "renewal", "payment", "update", "card",
            "delivery", "customs", "parcel", "fee", "dhl", "fedex", "ups", "courier",
            "identity", "id", "verification", "otp",
            "invoice", "urgent", "overdue", "accounting", "billing", "supplier",
        ]
        
        # Chercher les emails/SMS de phishing
        phishing_events = []
        tx_timestamp = transaction.timestamp
        
        if tx_timestamp:
            try:
                tx_time = datetime.fromisoformat(tx_timestamp.replace('Z', '+00:00'))
            except:
                tx_time = None
        else:
            tx_time = None
        
        # Chercher dans les emails
        for email in emails:
            email_content = email.mail.lower()
            if any(kw in email_content for kw in phishing_keywords):
                # Extraire le timestamp de l'email
                email_time = None
                for line in email.mail.split('\n'):
                    if line.lower().startswith('date:'):
                        try:
                            date_str = line.split(':', 1)[1].strip()
                            email_time = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        except:
                            pass
                        break
                
                if email_time and tx_time:
                    time_diff = (tx_time - email_time).total_seconds() / 3600
                    if 0 <= time_diff <= request.time_window_hours:
                        phishing_events.append({
                            "type": "email",
                            "time": email_time.isoformat(),
                            "time_diff_hours": round(time_diff, 2),
                            "preview": email_content[:200]
                        })
        
        # Chercher dans les SMS
        for sms in sms_list:
            if sender.biotag and sender.biotag.lower() in sms.id_user.lower():
                sms_content = sms.sms.lower()
                if any(kw in sms_content for kw in phishing_keywords):
                    sms_time = None
                    if hasattr(sms, 'datetime') and sms.datetime:
                        try:
                            sms_time = datetime.fromisoformat(sms.datetime.replace('Z', '+00:00'))
                        except:
                            pass
                    
                    if sms_time and tx_time:
                        time_diff = (tx_time - sms_time).total_seconds() / 3600
                        if 0 <= time_diff <= request.time_window_hours:
                            phishing_events.append({
                                "type": "sms",
                                "time": sms_time.isoformat(),
                                "time_diff_hours": round(time_diff, 2),
                                "preview": sms_content[:200]
                            })
        
        has_correlation = len(phishing_events) > 0
        
        return {
            "transaction_id": request.transaction_id,
            "time_correlation": has_correlation,
            "time_window_hours": request.time_window_hours,
            "phishing_events": phishing_events,
            "phishing_events_count": len(phishing_events)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking time correlation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/check-new-merchant")
async def check_new_merchant(request: NewMerchantRequest):
    """Vérifie si un merchant/recipient est nouveau pour l'utilisateur."""
    try:
        transactions = load_transactions()
        users = load_users()
        
        transaction = next((t for t in transactions if t.transaction_id == request.transaction_id), None)
        if not transaction:
            raise HTTPException(status_code=404, detail=f"Transaction {request.transaction_id} not found")
        
        # Trouver l'utilisateur
        sender = None
        if transaction.sender_id:
            sender = next((u for u in users if u.biotag == transaction.sender_id), None)
        
        if not sender:
            return {
                "transaction_id": request.transaction_id,
                "is_new_merchant": False,
                "reason": "Sender not found"
            }
        
        # Récupérer toutes les transactions de l'utilisateur
        user_transactions = [t for t in transactions if t.sender_id == sender.biotag]
        
        # Vérifier si le recipient_id ou recipient_iban a déjà été utilisé
        recipient_id = transaction.recipient_id
        recipient_iban = transaction.recipient_iban
        description = transaction.description or ""
        
        is_new = True
        seen_in = []
        
        for other_tx in user_transactions:
            if other_tx.transaction_id == transaction.transaction_id:
                continue
            
            # Vérifier recipient_id
            if recipient_id and other_tx.recipient_id and recipient_id == other_tx.recipient_id:
                is_new = False
                seen_in.append({
                    "transaction_id": other_tx.transaction_id,
                    "match_type": "recipient_id",
                    "timestamp": other_tx.timestamp
                })
            
            # Vérifier recipient_iban
            if recipient_iban and other_tx.recipient_iban and recipient_iban == other_tx.recipient_iban:
                is_new = False
                seen_in.append({
                    "transaction_id": other_tx.transaction_id,
                    "match_type": "recipient_iban",
                    "timestamp": other_tx.timestamp
                })
            
            # Vérifier description (si disponible)
            if description and other_tx.description:
                # Extraire le nom du merchant (premier mot)
                current_merchant = description.split()[0].lower() if description.split() else ""
                other_merchant = other_tx.description.split()[0].lower() if other_tx.description.split() else ""
                if current_merchant and other_merchant and current_merchant == other_merchant:
                    is_new = False
                    seen_in.append({
                        "transaction_id": other_tx.transaction_id,
                        "match_type": "description",
                        "timestamp": other_tx.timestamp
                    })
        
        return {
            "transaction_id": request.transaction_id,
            "is_new_merchant": is_new,
            "transaction_type": transaction.transaction_type,
            "recipient_id": recipient_id,
            "recipient_iban": recipient_iban,
            "description": description[:100] if description else "",
            "seen_in_transactions": seen_in,
            "total_user_transactions": len(user_transactions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking new merchant: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/check-location-anomaly")
async def check_location_anomaly(request: LocationAnomalyRequest):
    """Vérifie les anomalies de localisation pour une transaction."""
    try:
        transactions = load_transactions()
        users = load_users()
        locations = load_locations()
        
        transaction = next((t for t in transactions if t.transaction_id == request.transaction_id), None)
        if not transaction:
            raise HTTPException(status_code=404, detail=f"Transaction {request.transaction_id} not found")
        
        # Trouver l'utilisateur
        sender = None
        if transaction.sender_id:
            sender = next((u for u in users if u.biotag == transaction.sender_id), None)
        
        if not sender:
            return {
                "transaction_id": request.transaction_id,
                "has_location_anomaly": False,
                "reason": "Sender not found"
            }
        
        tx_location = transaction.location or ""
        user_residence = sender.residence
        
        # Chercher les coordonnées GPS dans les locations associées à la transaction
        tx_lat = None
        tx_lng = None
        
        # Chercher dans les locations du sender autour de la date de la transaction
        if transaction.sender_id and transaction.timestamp:
            sender_locations = [
                loc for loc in locations 
                if loc.biotag == transaction.sender_id
            ]
            
            # Filtrer par timestamp si disponible
            if transaction.timestamp:
                from datetime import datetime, timedelta
                try:
                    tx_time = datetime.fromisoformat(transaction.timestamp.replace('Z', '+00:00'))
                    time_window = timedelta(hours=24)
                    
                    for loc in sender_locations:
                        if loc.timestamp:
                            try:
                                loc_time = datetime.fromisoformat(loc.timestamp.replace('Z', '+00:00'))
                                if abs((loc_time - tx_time).total_seconds()) <= time_window.total_seconds():
                                    if hasattr(loc, 'lat') and hasattr(loc, 'lng'):
                                        tx_lat = getattr(loc, 'lat', None)
                                        tx_lng = getattr(loc, 'lng', None)
                                        if tx_lat and tx_lng:
                                            break
                            except:
                                continue
                except:
                    # Si pas de timestamp valide, prendre la première location avec GPS
                    for loc in sender_locations:
                        if hasattr(loc, 'lat') and hasattr(loc, 'lng'):
                            tx_lat = getattr(loc, 'lat', None)
                            tx_lng = getattr(loc, 'lng', None)
                            if tx_lat and tx_lng:
                                break
        
        # Extraire la ville de la transaction
        tx_city = None
        if tx_location:
            tx_city = tx_location.split(" - ")[0].strip()
        
        # Si use_city_fallback=True, utiliser la méthode "city" en priorité (plus fiable)
        if request.use_city_fallback and tx_city:
            residence_city = user_residence.city or ""
            
            if tx_city and residence_city and tx_city != residence_city:
                # Vérifier si l'utilisateur a déjà été dans cette ville
                user_locations = [loc for loc in locations if loc.biotag == sender.biotag]
                seen_cities = set()
                for loc in user_locations:
                    if hasattr(loc, 'city') and loc.city:
                        seen_cities.add(loc.city)
                
                # Calculer la distance entre les villes
                city_distance = calculate_city_distance(tx_city, residence_city)
                
                has_anomaly = tx_city not in seen_cities and (city_distance is None or city_distance > 100)
                
                return {
                    "transaction_id": request.transaction_id,
                    "has_location_anomaly": has_anomaly,
                    "method": "city",
                    "transaction_city": tx_city,
                    "residence_city": residence_city,
                    "city_distance_km": city_distance,
                    "user_has_been_there": tx_city in seen_cities,
                    "seen_cities": list(seen_cities)
                }
        
        # Méthode GPS si use_city_fallback=False et GPS disponible
        if not request.use_city_fallback and tx_lat and tx_lng and user_residence and user_residence.lat and user_residence.lng:
            try:
                distance_km = calculate_gps_distance(
                    float(user_residence.lat),
                    float(user_residence.lng),
                    float(tx_lat),
                    float(tx_lng)
                )
                
                has_anomaly = distance_km > 100  # Plus de 100km de la résidence
                
                return {
                    "transaction_id": request.transaction_id,
                    "has_location_anomaly": has_anomaly,
                    "method": "gps",
                    "distance_km": round(distance_km, 2),
                    "transaction_location": tx_location,
                    "residence_city": user_residence.city,
                    "threshold_km": 100
                }
            except:
                pass
        
        return {
            "transaction_id": request.transaction_id,
            "has_location_anomaly": False,
            "reason": "Insufficient location data"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking location anomaly: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/check-withdrawal-pattern")
async def check_withdrawal_pattern(request: WithdrawalPatternRequest):
    """Vérifie les patterns de retraits multiples."""
    try:
        transactions = load_transactions()
        users = load_users()
        
        transaction = next((t for t in transactions if t.transaction_id == request.transaction_id), None)
        if not transaction:
            raise HTTPException(status_code=404, detail=f"Transaction {request.transaction_id} not found")
        
        # Vérifier que c'est un retrait
        if transaction.transaction_type not in ["prelievo", "withdrawal"]:
            return {
                "transaction_id": request.transaction_id,
                "has_pattern": False,
                "reason": "Not a withdrawal transaction"
            }
        
        # Trouver l'utilisateur
        sender = None
        if transaction.sender_id:
            sender = next((u for u in users if u.biotag == transaction.sender_id), None)
        
        if not sender:
            return {
                "transaction_id": request.transaction_id,
                "has_pattern": False,
                "reason": "Sender not found"
            }
        
        # Récupérer toutes les transactions de l'utilisateur
        user_transactions = [t for t in transactions if t.sender_id == sender.biotag]
        
        tx_timestamp = transaction.timestamp
        if not tx_timestamp:
            return {
                "transaction_id": request.transaction_id,
                "has_pattern": False,
                "reason": "Transaction timestamp missing"
            }
        
        try:
            tx_time = datetime.fromisoformat(tx_timestamp.replace('Z', '+00:00'))
        except:
            return {
                "transaction_id": request.transaction_id,
                "has_pattern": False,
                "reason": "Invalid transaction timestamp"
            }
        
        # Chercher les retraits dans la fenêtre temporelle
        recent_withdrawals = []
        for other_tx in user_transactions:
            if other_tx.transaction_id == transaction.transaction_id:
                continue
            
            if other_tx.transaction_type in ["prelievo", "withdrawal"]:
                if other_tx.timestamp:
                    try:
                        other_time = datetime.fromisoformat(other_tx.timestamp.replace('Z', '+00:00'))
                        time_diff_hours = abs((tx_time - other_time).total_seconds() / 3600)
                        if time_diff_hours <= request.time_window_hours:
                            recent_withdrawals.append({
                                "transaction_id": other_tx.transaction_id,
                                "timestamp": other_tx.timestamp,
                                "amount": other_tx.amount,
                                "location": other_tx.location,
                                "time_diff_hours": round(time_diff_hours, 2)
                            })
                    except:
                        pass
        
        has_pattern = len(recent_withdrawals) >= 1  # Au moins 1 autre retrait + celui-ci = 2 minimum
        
        return {
            "transaction_id": request.transaction_id,
            "has_pattern": has_pattern,
            "time_window_hours": request.time_window_hours,
            "recent_withdrawals": recent_withdrawals,
            "total_withdrawals_in_window": len(recent_withdrawals) + 1  # +1 pour la transaction actuelle
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking withdrawal pattern: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/check-phishing-indicators")
async def check_phishing_indicators(request: PhishingIndicatorsRequest):
    """Vérifie la présence d'indicateurs de phishing dans les emails/SMS."""
    try:
        transactions = load_transactions()
        emails = load_emails()
        sms_list = load_sms()
        users = load_users()
        
        transaction = next((t for t in transactions if t.transaction_id == request.transaction_id), None)
        if not transaction:
            raise HTTPException(status_code=404, detail=f"Transaction {request.transaction_id} not found")
        
        # Trouver l'utilisateur
        sender = None
        if transaction.sender_id:
            sender = next((u for u in users if u.biotag == transaction.sender_id), None)
        
        if not sender:
            return {
                "transaction_id": request.transaction_id,
                "has_phishing_indicators": False,
                "reason": "Sender not found"
            }
        
        # Mots-clés de phishing par catégorie
        phishing_categories = {
            "parcel_customs": ["delivery", "customs", "parcel", "fee", "dhl", "fedex", "ups", "courier", "dogana", "consegna", "pacco"],
            "identity_verification": ["identity", "id", "verification", "otp", "verifica", "identit"],
            "bank_fraud_alert": ["bank", "account", "verify", "locked", "security", "suspended", "bancar", "conto", "blocco"],
            "bec_invoice": ["invoice", "urgent", "overdue", "accounting", "billing", "supplier", "fattura", "pagamento", "fornitore"],
            "subscription": ["subscription", "renewal", "abbonamento", "rinnovo"]
        }
        
        tx_timestamp = transaction.timestamp
        tx_time = None
        if tx_timestamp:
            try:
                tx_time = datetime.fromisoformat(tx_timestamp.replace('Z', '+00:00'))
            except:
                pass
        
        phishing_events = []
        
        # Chercher dans les emails
        for email in emails:
            email_content = email.mail.lower()
            
            # Détecter la catégorie
            detected_categories = []
            for category, keywords in phishing_categories.items():
                if any(kw in email_content for kw in keywords):
                    detected_categories.append(category)
            
            if detected_categories:
                # Extraire le timestamp
                email_time = None
                for line in email.mail.split('\n'):
                    if line.lower().startswith('date:'):
                        try:
                            date_str = line.split(':', 1)[1].strip()
                            email_time = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        except:
                            pass
                        break
                
                time_diff_hours = None
                if email_time and tx_time:
                    time_diff_hours = (tx_time - email_time).total_seconds() / 3600
                
                phishing_events.append({
                    "type": "email",
                    "categories": detected_categories,
                    "time": email_time.isoformat() if email_time else None,
                    "time_diff_hours": round(time_diff_hours, 2) if time_diff_hours else None,
                    "preview": email_content[:300]
                })
        
        # Chercher dans les SMS
        for sms in sms_list:
            if sender.biotag and sender.biotag.lower() in sms.id_user.lower():
                sms_content = sms.sms.lower()
                
                detected_categories = []
                for category, keywords in phishing_categories.items():
                    if any(kw in sms_content for kw in keywords):
                        detected_categories.append(category)
                
                if detected_categories:
                    sms_time = None
                    if hasattr(sms, 'datetime') and sms.datetime:
                        try:
                            sms_time = datetime.fromisoformat(sms.datetime.replace('Z', '+00:00'))
                        except:
                            pass
                    
                    time_diff_hours = None
                    if sms_time and tx_time:
                        time_diff_hours = (tx_time - sms_time).total_seconds() / 3600
                    
                    phishing_events.append({
                        "type": "sms",
                        "categories": detected_categories,
                        "time": sms_time.isoformat() if sms_time else None,
                        "time_diff_hours": round(time_diff_hours, 2) if time_diff_hours else None,
                        "preview": sms_content[:300]
                    })
        
        # Filtrer par fenêtre temporelle
        relevant_events = []
        for event in phishing_events:
            if event["time_diff_hours"] is not None:
                if 0 <= event["time_diff_hours"] <= request.time_window_hours:
                    relevant_events.append(event)
            else:
                # Inclure même sans timestamp si le contenu est clairement du phishing
                relevant_events.append(event)
        
        return {
            "transaction_id": request.transaction_id,
            "has_phishing_indicators": len(relevant_events) > 0,
            "time_window_hours": request.time_window_hours,
            "phishing_events": relevant_events,
            "total_events": len(relevant_events)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking phishing indicators: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
