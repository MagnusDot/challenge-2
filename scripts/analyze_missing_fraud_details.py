#!/usr/bin/env python3
"""Analyse détaillée des fraudes manquées pour comprendre pourquoi elles ne sont pas détectées."""

import csv
import json
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from Agent.helpers.http_client import make_api_request


async def fetch_transaction_data(transaction_id: str) -> Dict[str, Any]:
    """Récupère les données agrégées d'une transaction."""
    try:
        endpoint = f'/transactions/{transaction_id}'
        data = await make_api_request('GET', endpoint, response_format='json')
        return data
    except Exception as e:
        print(f"Erreur pour {transaction_id}: {e}")
        return {}


def analyze_signal_detection(
    signal: str,
    transaction: Dict[str, Any],
    sender: Dict[str, Any],
    sms_data: List[Dict[str, Any]],
    email_data: List[Dict[str, Any]],
    location_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Analyse si un signal devrait être détectable."""
    
    result = {
        "detectable": False,
        "reason": "",
        "data_available": {},
        "issues": []
    }
    
    if signal == "new_merchant":
        tx_type = transaction.get("transaction_type", "")
        description = transaction.get("description", "")
        other_transactions = sender.get("other_transactions", []) if sender else []
        
        result["data_available"] = {
            "tx_type": tx_type,
            "has_description": bool(description),
            "description_preview": description[:50] if description else "",
            "other_tx_count": len(other_transactions)
        }
        
        if tx_type not in ["e-commerce", "pagamento e-comm"]:
            result["issues"].append(f"Type '{tx_type}' n'est pas e-commerce")
        elif not description:
            result["issues"].append("Description vide - impossible de détecter le merchant")
        else:
            # Vérifier si le merchant a déjà été vu
            seen_merchants = set()
            for other_tx in other_transactions:
                if other_tx.get("transaction_type", "") in ["e-commerce", "pagamento e-comm"]:
                    other_desc = other_tx.get("description", "").lower()
                    if other_desc:
                        # Extraire le nom du merchant (premier mot ou partie avant certains séparateurs)
                        merchant_name = other_desc.split()[0] if other_desc.split() else ""
                        if merchant_name:
                            seen_merchants.add(merchant_name)
            
            current_merchant = description.split()[0] if description.split() else ""
            result["data_available"]["current_merchant"] = current_merchant
            result["data_available"]["seen_merchants"] = list(seen_merchants)
            
            if current_merchant and current_merchant.lower() not in [m.lower() for m in seen_merchants]:
                result["detectable"] = True
                result["reason"] = f"Merchant '{current_merchant}' jamais vu dans l'historique"
            else:
                result["issues"].append(f"Merchant '{current_merchant}' déjà vu ou vide")
    
    elif signal == "time_correlation":
        tx_timestamp = transaction.get("timestamp", "")
        result["data_available"]["tx_timestamp"] = tx_timestamp
        
        # Chercher des emails/SMS de phishing
        phishing_keywords = [
            "bank", "account", "verify", "locked", "security", "suspended",
            "subscription", "renewal", "payment", "update", "card",
            "delivery", "customs", "parcel", "fee", "dhl", "fedex", "ups", "courier",
            "identity", "id", "verification", "otp",
            "invoice", "urgent", "overdue", "accounting", "billing", "supplier",
        ]
        
        phishing_events = []
        for email in email_data:
            email_content = email.get("mail", "").lower()
            if any(kw in email_content for kw in phishing_keywords):
                email_time = email.get("date") or email.get("timestamp")
                if email_time:
                    phishing_events.append({
                        "type": "email",
                        "time": email_time,
                        "preview": email_content[:100]
                    })
        
        for sms in sms_data:
            sms_content = sms.get("sms", "").lower()
            if any(kw in sms_content for kw in phishing_keywords):
                sms_time = sms.get("datetime") or sms.get("timestamp")
                if sms_time:
                    phishing_events.append({
                        "type": "sms",
                        "time": sms_time,
                        "preview": sms_content[:100]
                    })
        
        result["data_available"]["phishing_events"] = phishing_events
        result["data_available"]["phishing_count"] = len(phishing_events)
        
        if not tx_timestamp:
            result["issues"].append("Timestamp de transaction manquant")
        elif not phishing_events:
            result["issues"].append("Aucun email/SMS de phishing trouvé")
        else:
            # Vérifier la corrélation temporelle
            try:
                tx_time = datetime.fromisoformat(tx_timestamp.replace('Z', '+00:00'))
                time_diffs = []
                for event in phishing_events:
                    try:
                        if isinstance(event["time"], str):
                            event_time = datetime.fromisoformat(event["time"].replace('Z', '+00:00'))
                            time_diff = tx_time - event_time
                            hours_diff = time_diff.total_seconds() / 3600
                            time_diffs.append(hours_diff)
                            
                            if 0 <= hours_diff <= 4:
                                result["detectable"] = True
                                result["reason"] = f"Transaction dans les 4h après phishing ({hours_diff:.2f}h)"
                                break
                    except (ValueError, AttributeError):
                        continue
                
                if not result["detectable"]:
                    result["issues"].append(f"Transaction trop éloignée du phishing (diffs: {time_diffs})")
            except (ValueError, AttributeError) as e:
                result["issues"].append(f"Erreur de parsing des timestamps: {e}")
    
    elif signal in ["location_anomaly", "impossible_travel"]:
        tx_location = transaction.get("location", "")
        tx_lat = transaction.get("lat")
        tx_lng = transaction.get("lng")
        user_residence = sender.get("residence", {}) if sender else {}
        user_lat = user_residence.get("lat")
        user_lng = user_residence.get("lng")
        
        result["data_available"] = {
            "tx_location": tx_location,
            "tx_lat": tx_lat,
            "tx_lng": tx_lng,
            "user_lat": user_lat,
            "user_lng": user_lng,
            "location_data_count": len(location_data)
        }
        
        if not tx_lat or not tx_lng:
            result["issues"].append("Coordonnées GPS de transaction manquantes")
        elif not user_lat or not user_lng:
            result["issues"].append("Coordonnées GPS de résidence manquantes")
        else:
            # Calculer la distance
            import math
            lat_diff = abs(float(user_lat) - float(tx_lat))
            lng_diff = abs(float(user_lng) - float(tx_lng))
            distance_km = math.sqrt(lat_diff**2 + lng_diff**2) * 111
            
            result["data_available"]["distance_km"] = distance_km
            
            if signal == "impossible_travel":
                # Pour impossible_travel, on doit aussi vérifier le temps depuis la dernière location GPS
                if location_data:
                    last_location = max(location_data, key=lambda x: x.get("timestamp", ""))
                    last_loc_time = last_location.get("timestamp", "")
                    if last_loc_time:
                        try:
                            last_time = datetime.fromisoformat(last_loc_time.replace('Z', '+00:00'))
                            tx_time = datetime.fromisoformat(tx_timestamp.replace('Z', '+00:00'))
                            time_diff_hours = (tx_time - last_time).total_seconds() / 3600
                            result["data_available"]["time_since_last_location_hours"] = time_diff_hours
                            
                            if distance_km > 1000 and time_diff_hours < 2:
                                result["detectable"] = True
                                result["reason"] = f"Distance > 1000km ({distance_km:.2f}km) en {time_diff_hours:.2f}h"
                            else:
                                result["issues"].append(f"Distance {distance_km:.2f}km ou temps {time_diff_hours:.2f}h insuffisant")
                        except:
                            result["issues"].append("Erreur de calcul du temps depuis dernière location")
                else:
                    result["issues"].append("Aucune donnée de location GPS disponible")
            else:  # location_anomaly
                if distance_km > 100:
                    result["detectable"] = True
                    result["reason"] = f"Distance > 100km depuis résidence ({distance_km:.2f}km)"
                else:
                    result["issues"].append(f"Distance trop faible ({distance_km:.2f}km)")
    
    elif signal == "pattern_multiple_withdrawals":
        tx_type = transaction.get("transaction_type", "")
        other_transactions = sender.get("other_transactions", []) if sender else []
        
        result["data_available"] = {
            "tx_type": tx_type,
            "other_tx_count": len(other_transactions)
        }
        
        if tx_type not in ["prelievo", "withdrawal"]:
            result["issues"].append(f"Type '{tx_type}' n'est pas un retrait")
        else:
            # Chercher les retraits dans les 1-2h
            tx_timestamp = transaction.get("timestamp", "")
            if tx_timestamp:
                try:
                    tx_time = datetime.fromisoformat(tx_timestamp.replace('Z', '+00:00'))
                    recent_withdrawals = []
                    for other_tx in other_transactions:
                        if other_tx.get("transaction_type") in ["prelievo", "withdrawal"]:
                            other_tx_time = other_tx.get("timestamp", "")
                            if other_tx_time:
                                try:
                                    other_time = datetime.fromisoformat(other_tx_time.replace('Z', '+00:00'))
                                    time_diff_hours = abs((tx_time - other_time).total_seconds() / 3600)
                                    if time_diff_hours <= 2:
                                        recent_withdrawals.append({
                                            "transaction_id": other_tx.get("transaction_id"),
                                            "time_diff_hours": time_diff_hours
                                        })
                                except:
                                    pass
                    
                    result["data_available"]["recent_withdrawals"] = recent_withdrawals
                    result["data_available"]["recent_withdrawals_count"] = len(recent_withdrawals)
                    
                    if len(recent_withdrawals) >= 1:  # Au moins 1 autre retrait + celui-ci = 2 minimum
                        result["detectable"] = True
                        result["reason"] = f"{len(recent_withdrawals) + 1} retraits dans les 2h"
                    else:
                        result["issues"].append(f"Pas assez de retraits récents ({len(recent_withdrawals)})")
                except:
                    result["issues"].append("Erreur de parsing du timestamp")
            else:
                result["issues"].append("Timestamp de transaction manquant")
    
    elif signal == "new_venue":
        tx_type = transaction.get("transaction_type", "")
        tx_location = transaction.get("location", "")
        other_transactions = sender.get("other_transactions", []) if sender else []
        
        result["data_available"] = {
            "tx_type": tx_type,
            "tx_location": tx_location,
            "other_tx_count": len(other_transactions)
        }
        
        if tx_type not in ["pagamento fisico", "in-person payment"]:
            result["issues"].append(f"Type '{tx_type}' n'est pas pagamento fisico")
        elif not tx_location:
            result["issues"].append("Location manquante")
        else:
            seen_venues = set()
            for other_tx in other_transactions:
                if other_tx.get("transaction_type") in ["pagamento fisico", "in-person payment"]:
                    other_location = other_tx.get("location", "")
                    if other_location:
                        seen_venues.add(other_location.lower())
            
            result["data_available"]["seen_venues"] = list(seen_venues)
            
            if tx_location.lower() not in seen_venues:
                result["detectable"] = True
                result["reason"] = f"Lieu '{tx_location}' jamais vu"
            else:
                result["issues"].append(f"Lieu '{tx_location}' déjà vu")
    
    elif signal == "post_withdrawal":
        tx_type = transaction.get("transaction_type", "")
        other_transactions = sender.get("other_transactions", []) if sender else []
        
        result["data_available"] = {
            "tx_type": tx_type,
            "other_tx_count": len(other_transactions)
        }
        
        if tx_type not in ["pagamento fisico", "in-person payment", "e-commerce"]:
            result["issues"].append(f"Type '{tx_type}' n'est pas pagamento/e-commerce")
        else:
            tx_timestamp = transaction.get("timestamp", "")
            if tx_timestamp:
                try:
                    tx_time = datetime.fromisoformat(tx_timestamp.replace('Z', '+00:00'))
                    recent_withdrawals = []
                    for other_tx in other_transactions:
                        if other_tx.get("transaction_type") in ["prelievo", "withdrawal"]:
                            other_tx_time = other_tx.get("timestamp", "")
                            if other_tx_time:
                                try:
                                    other_time = datetime.fromisoformat(other_tx_time.replace('Z', '+00:00'))
                                    time_diff_hours = (tx_time - other_time).total_seconds() / 3600
                                    if 0 <= time_diff_hours <= 2:  # Retrait dans les 2h avant
                                        recent_withdrawals.append({
                                            "transaction_id": other_tx.get("transaction_id"),
                                            "time_diff_hours": time_diff_hours,
                                            "amount": other_tx.get("amount", 0)
                                        })
                                except:
                                    pass
                    
                    result["data_available"]["recent_withdrawals"] = recent_withdrawals
                    
                    if recent_withdrawals:
                        result["detectable"] = True
                        result["reason"] = f"Transaction après {len(recent_withdrawals)} retrait(s)"
                    else:
                        result["issues"].append("Aucun retrait récent dans les 2h avant")
                except:
                    result["issues"].append("Erreur de parsing du timestamp")
            else:
                result["issues"].append("Timestamp de transaction manquant")
    
    elif signal == "amount_anomaly":
        tx_amount = transaction.get("amount", 0)
        sender_salary = sender.get("salary", 0) if sender else 0
        
        result["data_available"] = {
            "tx_amount": tx_amount,
            "sender_salary": sender_salary,
            "ratio": tx_amount / sender_salary if sender_salary > 0 else 0
        }
        
        if sender_salary > 0 and tx_amount > sender_salary * 0.3:
            result["detectable"] = True
            result["reason"] = f"Montant ({tx_amount}) > 30% du salaire ({sender_salary * 0.3})"
        else:
            result["issues"].append(f"Montant ({tx_amount}) pas assez élevé par rapport au salaire ({sender_salary})")
    
    return result


async def analyze_missing_fraud(transaction_id: str, fraud_info: Dict[str, Any]) -> Dict[str, Any]:
    """Analyse une fraude manquée."""
    print(f"Analyse de {transaction_id}...")
    
    api_data = await fetch_transaction_data(transaction_id)
    
    if not api_data:
        return {
            "transaction_id": transaction_id,
            "error": "Impossible de récupérer les données"
        }
    
    transaction = api_data.get("transaction", {})
    sender = api_data.get("sender", {})
    sms_data = api_data.get("sender_sms", []) + api_data.get("recipient_sms", [])
    email_data = api_data.get("sender_emails", []) + api_data.get("recipient_emails", [])
    location_data = api_data.get("sender_locations", []) + api_data.get("recipient_locations", [])
    
    expected_signals = fraud_info.get("fraud_signals", [])
    
    analysis = {
        "transaction_id": transaction_id,
        "fraud_scenario": fraud_info.get("fraud_scenario", ""),
        "expected_signals": expected_signals,
        "signal_analysis": {},
        "summary": {
            "detectable_signals": [],
            "non_detectable_signals": [],
            "missing_data": []
        }
    }
    
    for signal in expected_signals:
        signal_result = analyze_signal_detection(
            signal, transaction, sender, sms_data, email_data, location_data
        )
        analysis["signal_analysis"][signal] = signal_result
        
        if signal_result["detectable"]:
            analysis["summary"]["detectable_signals"].append(signal)
        else:
            analysis["summary"]["non_detectable_signals"].append(signal)
            if signal_result.get("issues"):
                analysis["summary"]["missing_data"].extend(signal_result["issues"])
    
    return analysis


async def main():
    """Analyse toutes les fraudes manquées."""
    script_dir = Path(__file__).parent.parent
    ground_truth_path = script_dir / 'dataset' / 'ground_truth' / 'public_1.csv'
    detected_path = script_dir / 'fraud_graph' / 'results' / 'final_fraud.json'
    
    # Charger ground truth
    ground_truth = {}
    with open(ground_truth_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ground_truth[row['transaction_id']] = {
                'fraud_scenario': row['fraud_scenario'],
                'fraud_signals': row['fraud_signals'].split(',') if row['fraud_signals'] else []
            }
    
    # Charger détections
    detected = set()
    with open(detected_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if isinstance(data, dict) and 'frauds' in data:
            for fraud in data['frauds']:
                detected.add(fraud['transaction_id'])
    
    # Identifier les fraudes manquées
    missing_ids = [tid for tid in ground_truth.keys() if tid not in detected]
    
    print(f"Analyse de {len(missing_ids)} fraudes manquées...")
    print()
    
    analyses = []
    for tid in missing_ids:
        fraud_info = ground_truth[tid]
        analysis = await analyze_missing_fraud(tid, fraud_info)
        analyses.append(analysis)
    
    # Afficher les résultats
    print("\n" + "=" * 80)
    print("RÉSULTATS DE L'ANALYSE")
    print("=" * 80)
    
    for analysis in analyses:
        print(f"\n{'='*80}")
        print(f"Transaction: {analysis['transaction_id']}")
        print(f"Scénario: {analysis['fraud_scenario']}")
        print(f"Signaux attendus: {', '.join(analysis['expected_signals'])}")
        print()
        
        print("Analyse par signal:")
        for signal, signal_analysis in analysis["signal_analysis"].items():
            status = "✅ DÉTECTABLE" if signal_analysis["detectable"] else "❌ NON DÉTECTABLE"
            print(f"  {status} - {signal}")
            print(f"    Raison: {signal_analysis['reason']}")
            if signal_analysis.get("issues"):
                print(f"    Problèmes: {', '.join(signal_analysis['issues'])}")
            print()
        
        print("Résumé:")
        print(f"  Signaux détectables: {len(analysis['summary']['detectable_signals'])}/{len(analysis['expected_signals'])}")
        if analysis['summary']['detectable_signals']:
            print(f"    - {', '.join(analysis['summary']['detectable_signals'])}")
        if analysis['summary']['non_detectable_signals']:
            print(f"  Signaux non détectables: {', '.join(analysis['summary']['non_detectable_signals'])}")
    
    # Sauvegarder
    output_file = script_dir / 'scripts' / 'results' / 'missing_frauds_detailed_analysis.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analyses, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n✅ Analyse sauvegardée dans {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
