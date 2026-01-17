"""Script pour dumper les données API des fraudes manquées."""

import asyncio
import json
import csv
from pathlib import Path
from typing import Dict, List, Any
import httpx


async def fetch_transaction_data(transaction_id: str, base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Récupère les données complètes d'une transaction via l'API.
    
    Args:
        transaction_id: ID de la transaction
        base_url: URL de base de l'API
        
    Returns:
        Données complètes de la transaction
    """
    try:
        url = f"{base_url}/transactions/{transaction_id}"
        params = {"format": "json"}
        
        async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            await asyncio.sleep(0.1)
            return response.json()
    except Exception as e:
        print(f"❌ Erreur pour {transaction_id}: {e}")
        return {"error": str(e), "transaction_id": transaction_id}


async def main():
    """Récupère les données des fraudes manquées."""
    # Lire le ground truth
    ground_truth_path = Path("dataset/ground_truth/public_1.csv")
    fraud_json_path = Path("fraud_graph/results/fraud.json")
    
    # Charger les fraudes détectées
    detected_ids = set()
    if fraud_json_path.exists():
        with open(fraud_json_path, "r", encoding="utf-8") as f:
            detected_frauds = json.load(f)
            detected_ids = {item.get("transaction_id") for item in detected_frauds if isinstance(item, dict)}
    
    # Lire le ground truth
    missing_frauds: List[Dict[str, Any]] = []
    all_frauds: List[Dict[str, Any]] = []
    
    with open(ground_truth_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tx_id = row["transaction_id"]
            fraud_info = {
                "transaction_id": tx_id,
                "fraud_scenario": row.get("fraud_scenario", ""),
                "expected_signals": row.get("fraud_signals", "").split(",") if row.get("fraud_signals") else [],
                "timestamp": row.get("timestamp", ""),
            }
            all_frauds.append(fraud_info)
            
            if tx_id not in detected_ids:
                missing_frauds.append(fraud_info)
    
    print(f"📊 Total fraudes dans ground truth: {len(all_frauds)}")
    print(f"❌ Fraudes manquées: {len(missing_frauds)}")
    print(f"✅ Fraudes détectées: {len(detected_ids)}")
    print("\n🔍 Récupération des données API des fraudes manquées...")
    
    # Récupérer les données API pour chaque fraude manquée
    results = []
    for i, fraud_info in enumerate(missing_frauds, 1):
        tx_id = fraud_info["transaction_id"]
        print(f"  [{i}/{len(missing_frauds)}] Récupération de {tx_id}...")
        
        api_data = await fetch_transaction_data(tx_id)
        
        result = {
            "fraud_info": fraud_info,
            "api_data": api_data,
        }
        results.append(result)
    
    # Sauvegarder dans un JSON
    output_file = Path("scripts/results/missing_frauds_data.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Données sauvegardées dans {output_file}")
    print(f"📁 {len(results)} fraudes manquées analysées")
    
    # Afficher un résumé
    print("\n📋 Résumé des fraudes manquées:")
    for fraud_info in missing_frauds:
        print(f"  - {fraud_info['transaction_id']}: {fraud_info['fraud_scenario']}")
        print(f"    Signaux attendus: {', '.join(fraud_info['expected_signals'])}")


if __name__ == "__main__":
    asyncio.run(main())
