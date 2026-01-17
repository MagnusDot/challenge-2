"""Script pour analyser pourquoi les fraudes manquées ne sont pas détectées."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


def analyze_transaction(fraud_info: Dict[str, Any], api_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse une transaction pour comprendre pourquoi elle n'est pas détectée."""
    
    transaction = api_data.get("transaction", {})
    sender = api_data.get("sender", {})
    sms_data = api_data.get("sender_sms", []) + api_data.get("recipient_sms", [])
    email_data = api_data.get("sender_emails", []) + api_data.get("recipient_emails", [])
    location_data = api_data.get("sender_locations", []) + api_data.get("recipient_locations", [])
    
    expected_signals = fraud_info.get("expected_signals", [])
    
    analysis = {
        "transaction_id": fraud_info["transaction_id"],
        "fraud_scenario": fraud_info["fraud_scenario"],
        "expected_signals": expected_signals,
        "issues": [],
        "detected_features": {},
    }
    
    # Analyser chaque signal attendu
    for signal in expected_signals:
        signal_analysis = analyze_signal(signal, transaction, sender, sms_data, email_data, location_data, api_data)
        analysis["detected_features"][signal] = signal_analysis
        
        if not signal_analysis.get("detected", False):
            analysis["issues"].append({
                "signal": signal,
                "reason": signal_analysis.get("reason", "Non détecté"),
                "details": signal_analysis.get("details", {})
            })
    
    return analysis


def analyze_signal(
    signal: str,
    transaction: Dict[str, Any],
    sender: Dict[str, Any],
    sms_data: List[Dict[str, Any]],
    email_data: List[Dict[str, Any]],
    location_data: List[Dict[str, Any]],
    api_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Analyse si un signal spécifique devrait être détecté."""
    
    result = {
        "detected": False,
        "reason": "",
        "details": {}
    }
    
    if signal == "new_merchant":
        # Vérifier si new_merchant devrait être détecté
        tx_type = transaction.get("transaction_type", "")
        description = transaction.get("description", "")
        other_transactions = sender.get("other_transactions", [])
        
        result["details"]["tx_type"] = tx_type
        result["details"]["description"] = description
        result["details"]["description_length"] = len(description)
        result["details"]["other_transactions_count"] = len(other_transactions)
        
        if tx_type not in ["e-commerce", "pagamento e-comm"]:
            result["reason"] = f"Type de transaction '{tx_type}' n'est pas e-commerce"
        elif not description:
            result["reason"] = "Description vide - impossible de détecter le merchant"
        else:
            # Vérifier si le merchant a déjà été vu
            seen_merchants = set()
            for other_tx in other_transactions:
                if other_tx.get("transaction_type", "") in ["e-commerce", "pagamento e-comm"]:
                    other_desc = other_tx.get("description", "").lower()
                    if other_desc:
                        merchant_name = other_desc.split()[0] if other_desc.split() else ""
                        if merchant_name:
                            seen_merchants.add(merchant_name)
            
            current_merchant = description.split()[0] if description.split() else ""
            result["details"]["current_merchant"] = current_merchant
            result["details"]["seen_merchants"] = list(seen_merchants)
            
            if current_merchant and current_merchant not in seen_merchants:
                result["detected"] = True
                result["reason"] = "Merchant jamais vu - devrait être détecté"
            else:
                result["reason"] = f"Merchant '{current_merchant}' déjà vu ou vide"
    
    elif signal == "time_correlation":
        # Vérifier si time_correlation devrait être détecté
        tx_timestamp = transaction.get("timestamp", "")
        result["details"]["tx_timestamp"] = tx_timestamp
        
        # Chercher des emails/SMS de phishing
        phishing_keywords = [
            "bank", "account", "verify", "locked", "security", "suspended",
            "subscription", "renewal", "payment", "update", "card",
            "delivery", "customs", "parcel", "fee", "dhl", "fedex", "ups", "courier",
            "identity", "id", "verification", "otp",
            "invoice", "urgent", "overdue", "accounting", "billing", "supplier",
        ]
        
        phishing_times = []
        for email in email_data:
            email_content = email.get("mail", "").lower()
            if any(kw in email_content for kw in phishing_keywords):
                email_time = email.get("date") or email.get("timestamp")
                if email_time:
                    phishing_times.append(email_time)
        
        for sms in sms_data:
            sms_content = sms.get("sms", "").lower()
            if any(kw in sms_content for kw in phishing_keywords):
                sms_time = sms.get("datetime") or sms.get("timestamp")
                if sms_time:
                    phishing_times.append(sms_time)
        
        result["details"]["phishing_times"] = phishing_times
        result["details"]["phishing_count"] = len(phishing_times)
        
        if not tx_timestamp:
            result["reason"] = "Timestamp de transaction manquant"
        elif not phishing_times:
            result["reason"] = "Aucun email/SMS de phishing trouvé"
        else:
            # Vérifier la corrélation temporelle
            try:
                tx_time = datetime.fromisoformat(tx_timestamp.replace('Z', '+00:00'))
                for phishing_time_str in phishing_times:
                    try:
                        if isinstance(phishing_time_str, str):
                            phishing_time = datetime.fromisoformat(phishing_time_str.replace('Z', '+00:00'))
                            time_diff = tx_time - phishing_time
                            hours_diff = time_diff.total_seconds() / 3600
                            result["details"]["time_diffs_hours"] = result["details"].get("time_diffs_hours", []) + [hours_diff]
                            
                            if 0 <= hours_diff <= 4:
                                result["detected"] = True
                                result["reason"] = f"Transaction dans les 4h après phishing ({hours_diff:.2f}h)"
                                break
                    except (ValueError, AttributeError):
                        continue
                
                if not result["detected"]:
                    result["reason"] = f"Transaction trop éloignée du phishing (diffs: {result['details'].get('time_diffs_hours', [])})"
            except (ValueError, AttributeError):
                result["reason"] = "Erreur de parsing des timestamps"
    
    elif signal == "location_anomaly" or signal == "impossible_travel":
        # Vérifier si location_anomaly/impossible_travel devrait être détecté
        tx_location = transaction.get("location", "")
        tx_lat = transaction.get("lat")
        tx_lng = transaction.get("lng")
        user_residence = sender.get("residence", {})
        user_lat = user_residence.get("lat")
        user_lng = user_residence.get("lng")
        
        result["details"]["tx_location"] = tx_location
        result["details"]["tx_lat"] = tx_lat
        result["details"]["tx_lng"] = tx_lng
        result["details"]["user_lat"] = user_lat
        result["details"]["user_lng"] = user_lng
        
        if not tx_lat or not tx_lng or not user_lat or not user_lng:
            result["reason"] = "Coordonnées GPS manquantes"
        else:
            # Calculer la distance
            import math
            lat_diff = abs(float(user_lat) - float(tx_lat))
            lng_diff = abs(float(user_lng) - float(tx_lng))
            distance_km = math.sqrt(lat_diff**2 + lng_diff**2) * 111
            
            result["details"]["distance_km"] = distance_km
            
            if signal == "impossible_travel":
                if distance_km > 1000:
                    result["detected"] = True
                    result["reason"] = f"Distance > 1000km ({distance_km:.2f}km)"
                else:
                    result["reason"] = f"Distance trop faible pour impossible_travel ({distance_km:.2f}km)"
            else:  # location_anomaly
                if distance_km > 100:
                    result["detected"] = True
                    result["reason"] = f"Distance > 100km ({distance_km:.2f}km)"
                else:
                    result["reason"] = f"Distance trop faible pour location_anomaly ({distance_km:.2f}km)"
    
    elif signal == "pattern_multiple_withdrawals":
        # Vérifier si pattern_multiple_withdrawals devrait être détecté
        tx_type = transaction.get("transaction_type", "")
        other_transactions = sender.get("other_transactions", [])
        
        result["details"]["tx_type"] = tx_type
        result["details"]["other_transactions_count"] = len(other_transactions)
        
        if tx_type != "prelievo" and tx_type != "withdrawal":
            result["reason"] = f"Type de transaction '{tx_type}' n'est pas un retrait"
        else:
            recent_withdrawals = [
                tx for tx in other_transactions
                if tx.get("transaction_type") in ["prelievo", "withdrawal"]
            ]
            result["details"]["recent_withdrawals_count"] = len(recent_withdrawals)
            
            if len(recent_withdrawals) >= 2:
                result["detected"] = True
                result["reason"] = f"{len(recent_withdrawals)} retraits récents détectés"
            else:
                result["reason"] = f"Pas assez de retraits récents ({len(recent_withdrawals)})"
    
    elif signal == "new_venue":
        # Vérifier si new_venue devrait être détecté
        tx_type = transaction.get("transaction_type", "")
        tx_location = transaction.get("location", "")
        other_transactions = sender.get("other_transactions", [])
        
        result["details"]["tx_type"] = tx_type
        result["details"]["tx_location"] = tx_location
        result["details"]["other_transactions_count"] = len(other_transactions)
        
        if tx_type != "pagamento fisico":
            result["reason"] = f"Type de transaction '{tx_type}' n'est pas pagamento fisico"
        elif not tx_location:
            result["reason"] = "Location manquante"
        else:
            seen_venues = set()
            for other_tx in other_transactions:
                if other_tx.get("transaction_type") == "pagamento fisico":
                    other_location = other_tx.get("location", "")
                    if other_location:
                        seen_venues.add(other_location.lower())
            
            result["details"]["seen_venues"] = list(seen_venues)
            
            if tx_location.lower() not in seen_venues:
                result["detected"] = True
                result["reason"] = "Lieu jamais vu - devrait être détecté"
            else:
                result["reason"] = f"Lieu '{tx_location}' déjà vu"
    
    elif signal == "post_withdrawal":
        # Vérifier si post_withdrawal devrait être détecté
        tx_type = transaction.get("transaction_type", "")
        other_transactions = sender.get("other_transactions", [])
        
        result["details"]["tx_type"] = tx_type
        result["details"]["other_transactions_count"] = len(other_transactions)
        
        if tx_type not in ["pagamento fisico", "e-commerce"]:
            result["reason"] = f"Type de transaction '{tx_type}' n'est pas pagamento/e-commerce"
        else:
            recent_withdrawals = [
                tx for tx in other_transactions
                if tx.get("transaction_type") in ["prelievo", "withdrawal"]
                and tx.get("amount", 0) > 200
            ]
            result["details"]["recent_withdrawals_count"] = len(recent_withdrawals)
            
            if recent_withdrawals:
                result["detected"] = True
                result["reason"] = f"{len(recent_withdrawals)} retraits récents > 200€ détectés"
            else:
                result["reason"] = "Aucun retrait récent > 200€"
    
    elif signal == "amount_anomaly":
        # Vérifier si amount_anomaly devrait être détecté
        tx_amount = transaction.get("amount", 0)
        sender_salary = sender.get("salary", 0)
        
        result["details"]["tx_amount"] = tx_amount
        result["details"]["sender_salary"] = sender_salary
        result["details"]["ratio"] = tx_amount / sender_salary if sender_salary > 0 else 0
        
        if sender_salary > 0 and tx_amount > sender_salary * 0.3:
            result["detected"] = True
            result["reason"] = f"Montant ({tx_amount}) > 30% du salaire ({sender_salary * 0.3})"
        else:
            result["reason"] = f"Montant ({tx_amount}) pas assez élevé par rapport au salaire ({sender_salary})"
    
    return result


def main():
    """Analyse les fraudes manquées."""
    input_file = Path("scripts/results/missing_frauds_data.json")
    
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    analyses = []
    for item in data:
        analysis = analyze_transaction(item["fraud_info"], item["api_data"])
        analyses.append(analysis)
    
    # Afficher les résultats
    print("=" * 80)
    print("ANALYSE DES FRAUDES MANQUÉES")
    print("=" * 80)
    
    for analysis in analyses:
        print(f"\n{'='*80}")
        print(f"Transaction: {analysis['transaction_id']}")
        print(f"Scénario: {analysis['fraud_scenario']}")
        print(f"Signaux attendus: {', '.join(analysis['expected_signals'])}")
        print(f"\nProblèmes détectés ({len(analysis['issues'])}):")
        
        for issue in analysis["issues"]:
            print(f"  ❌ {issue['signal']}: {issue['reason']}")
            if issue.get("details"):
                for key, value in issue["details"].items():
                    if isinstance(value, (list, dict)) and len(str(value)) > 100:
                        print(f"     {key}: {type(value).__name__} ({len(value) if isinstance(value, list) else 'dict'})")
                    else:
                        print(f"     {key}: {value}")
        
        print(f"\nSignaux détectés:")
        for signal, signal_analysis in analysis["detected_features"].items():
            status = "✅" if signal_analysis.get("detected") else "❌"
            print(f"  {status} {signal}: {signal_analysis.get('reason', 'N/A')}")
    
    # Sauvegarder l'analyse
    output_file = Path("scripts/results/missing_frauds_analysis.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(analyses, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n✅ Analyse sauvegardée dans {output_file}")


if __name__ == "__main__":
    main()
