import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from ..state import FraudState


def aggregate_confirmed_frauds(state: FraudState) -> FraudState:
    agent_results = state.get('agent_analysis_results', {})
    
    if not agent_results:
        return state
    
    all_frauds = []
    batch_results = agent_results.get('batch_results', [])
    
    for batch_result in batch_results:
        if isinstance(batch_result, dict):
            frauds = batch_result.get('frauds_detected', [])
            all_frauds.extend(frauds)
    
    if not all_frauds:
        print('⚠️  Aucune fraude confirmée par l\'agent')
        return state
    
    output_file = Path('fraud_graph/results/real_fraud.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    real_frauds_data = {
        'timestamp': datetime.now().isoformat(),
        'total_confirmed_frauds': len(all_frauds),
        'frauds': all_frauds
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(real_frauds_data, f, indent=2, ensure_ascii=False)
    
    print(f'💾 {len(all_frauds)} fraudes confirmées sauvegardées dans: {output_file}')
    
    return {
        **state,
        'real_frauds': real_frauds_data
    }
