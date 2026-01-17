#!/usr/bin/env python3
"""Analyse les faux positifs pour comprendre pourquoi ils sont détectés."""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))
from Agent.helpers.http_client import make_api_request


async def analyze_false_positive(transaction_id: str) -> Dict[str, Any]:
    """Analyse une transaction faussement détectée comme fraude."""
    print(f"Analyse de {transaction_id}...")
    
    try:
        endpoint = f'/transactions/{transaction_id}'
        data = await make_api_request('GET', endpoint, response_format='json')
        
        transaction = data.get("transaction", {})
        sender = data.get("sender", {})
        
        analysis = {
            "transaction_id": transaction_id,
            "transaction_type": transaction.get("transaction_type"),
            "amount": transaction.get("amount"),
            "balance_after": transaction.get("balance_after"),
            "location": transaction.get("location"),
            "description": transaction.get("description", "")[:100],
            "sender_salary": sender.get("salary", 0) if sender else 0,
            "other_transactions_count": len(sender.get("other_transactions", [])) if sender else 0,
            "has_recipient": data.get("recipient") is not None,
        }
        
        return analysis
    except Exception as e:
        return {"transaction_id": transaction_id, "error": str(e)}


async def main():
    """Analyse tous les faux positifs."""
    false_positives = [
        "0c91eed2-d2b1-435d-97e7-fd2a0f0b60c1",
        "4f6ded2a-fc5d-41c0-8fc0-670e38664244",
        "67fc4b9b-8987-473e-8e3d-c6410bedbb66",
        "86fdbf92-90e1-4110-be58-337a498c4ac6",
        "9fa7eb40-8b98-4b89-a84e-dc06d5247ef8",
        "ab0df8fe-f982-4b13-8c7c-b0bf2afdddea",
    ]
    
    print("=" * 80)
    print("ANALYSE DES FAUX POSITIFS")
    print("=" * 80)
    print()
    
    analyses = []
    for fp_id in false_positives:
        analysis = await analyze_false_positive(fp_id)
        analyses.append(analysis)
    
    for analysis in analyses:
        print(f"\n{'='*80}")
        print(f"Transaction: {analysis['transaction_id']}")
        print(f"  Type: {analysis.get('transaction_type', 'N/A')}")
        print(f"  Montant: {analysis.get('amount', 'N/A')}€")
        print(f"  Balance après: {analysis.get('balance_after', 'N/A')}€")
        print(f"  Salaire utilisateur: {analysis.get('sender_salary', 'N/A')}€")
        print(f"  Location: {analysis.get('location', 'N/A')}")
        print(f"  Description: {analysis.get('description', 'N/A')}")
        print(f"  Autres transactions: {analysis.get('other_transactions_count', 0)}")
        print(f"  A un destinataire: {analysis.get('has_recipient', False)}")
        
        # Analyser pourquoi c'est un faux positif
        balance = analysis.get('balance_after', 0)
        if balance and balance > 0:
            print(f"  ⚠️  Balance > 0€ ({balance}€) - Pas de vidage de compte")
        
        amount = analysis.get('amount', 0)
        salary = analysis.get('sender_salary', 0)
        if salary > 0 and amount > 0:
            ratio = amount / salary
            if ratio < 0.3:
                print(f"  ⚠️  Montant ({amount}€) < 30% du salaire ({salary}€) - Pas d'anomalie de montant")


if __name__ == "__main__":
    asyncio.run(main())
