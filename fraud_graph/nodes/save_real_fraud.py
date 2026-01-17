import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from ..state import FraudState

_save_lock = asyncio.Lock()


async def save_fraud_to_real_fraud_json(frauds: List[Dict[str, Any]]) -> None:
    """Sauvegarde les fraudes dans real_fraud.json (version avec merge des fraudes existantes)."""
    if not frauds:
        return
    
    output_file = Path('fraud_graph/results/real_fraud.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    async with _save_lock:
        existing_frauds = []
        if output_file.exists():
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, dict) and 'frauds' in existing_data:
                        existing_frauds = existing_data['frauds']
                    elif isinstance(existing_data, list):
                        existing_frauds = existing_data
            except (json.JSONDecodeError, KeyError):
                existing_frauds = []
        
        existing_ids = {f.get('transaction_id') for f in existing_frauds if isinstance(f, dict)}
        
        new_frauds = [
            f for f in frauds
            if isinstance(f, dict) and f.get('transaction_id') not in existing_ids
        ]
        
        if not new_frauds:
            return
        
        all_frauds = existing_frauds + new_frauds
        
        real_frauds_data = {
            'timestamp': datetime.now().isoformat(),
            'total_confirmed_frauds': len(all_frauds),
            'frauds': all_frauds
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(real_frauds_data, f, indent=2, ensure_ascii=False)
        
        print(f'💾 {len(new_frauds)} nouvelle(s) fraude(s) ajoutée(s) à real_fraud.json (total: {len(all_frauds)})')


async def save_frauds_bulk_optimized(frauds: List[Dict[str, Any]], merge_existing: bool = True) -> None:
    """Sauvegarde optimisée en bulk - une seule écriture, optionnellement merge avec l'existant.
    
    Args:
        frauds: Liste de toutes les fraudes à sauvegarder
        merge_existing: Si True, merge avec les fraudes existantes. Si False, écrase le fichier.
    """
    if not frauds:
        return
    
    output_file = Path('fraud_graph/results/real_fraud.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    async with _save_lock:
        if merge_existing and output_file.exists():
            # Lire les fraudes existantes une seule fois
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, dict) and 'frauds' in existing_data:
                        existing_frauds = existing_data['frauds']
                    elif isinstance(existing_data, list):
                        existing_frauds = existing_data
                    else:
                        existing_frauds = []
            except (json.JSONDecodeError, KeyError):
                existing_frauds = []
            
            # Dédupliquer : garder les fraudes existantes + nouvelles (sans doublons)
            existing_ids = {f.get('transaction_id') for f in existing_frauds if isinstance(f, dict)}
            new_frauds = [
                f for f in frauds
                if isinstance(f, dict) and f.get('transaction_id') not in existing_ids
            ]
            all_frauds = existing_frauds + new_frauds
        else:
            # Écraser directement sans lire le fichier
            all_frauds = frauds
        
        real_frauds_data = {
            'timestamp': datetime.now().isoformat(),
            'total_confirmed_frauds': len(all_frauds),
            'frauds': all_frauds
        }
        
        # Une seule écriture
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(real_frauds_data, f, indent=2, ensure_ascii=False)
