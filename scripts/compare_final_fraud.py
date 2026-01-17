#!/usr/bin/env python3
"""Compare final_fraud.json with ground truth public_1.csv"""

import json
import csv
from pathlib import Path
from typing import Set, Dict, List

def load_ground_truth(csv_path: Path) -> Dict[str, Dict]:
    """Load ground truth frauds from CSV."""
    frauds = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            transaction_id = row['transaction_id']
            frauds[transaction_id] = {
                'transaction_id': transaction_id,
                'fraud_scenario': row['fraud_scenario'],
                'fraud_signals': row['fraud_signals'].split(',') if row['fraud_signals'] else [],
                'timestamp': row['timestamp']
            }
    return frauds

def load_detected_frauds(json_path: Path) -> Dict[str, Dict]:
    """Load detected frauds from JSON."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    frauds = {}
    if isinstance(data, dict) and 'frauds' in data:
        for fraud in data['frauds']:
            transaction_id = fraud['transaction_id']
            frauds[transaction_id] = fraud
    elif isinstance(data, list):
        for fraud in data:
            transaction_id = fraud['transaction_id']
            frauds[transaction_id] = fraud
    
    return frauds

def compare_results(ground_truth: Dict[str, Dict], detected: Dict[str, Dict]) -> Dict:
    """Compare ground truth with detected frauds."""
    ground_truth_ids = set(ground_truth.keys())
    detected_ids = set(detected.keys())
    
    true_positives = ground_truth_ids & detected_ids
    false_positives = detected_ids - ground_truth_ids
    false_negatives = ground_truth_ids - detected_ids
    
    tp_count = len(true_positives)
    fp_count = len(false_positives)
    fn_count = len(false_negatives)
    
    precision = tp_count / (tp_count + fp_count) if (tp_count + fp_count) > 0 else 0.0
    recall = tp_count / (tp_count + fn_count) if (tp_count + fn_count) > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        'true_positives': sorted(true_positives),
        'false_positives': sorted(false_positives),
        'false_negatives': sorted(false_negatives),
        'tp_count': tp_count,
        'fp_count': fp_count,
        'fn_count': fn_count,
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'total_ground_truth': len(ground_truth_ids),
        'total_detected': len(detected_ids)
    }

def analyze_false_positives(false_positives: List[str], detected: Dict[str, Dict], ground_truth: Dict[str, Dict]) -> List[Dict]:
    """Analyze false positives to understand why they were flagged."""
    analysis = []
    for fp_id in false_positives:
        fraud_data = detected.get(fp_id, {})
        analysis.append({
            'transaction_id': fp_id,
            'reasons': fraud_data.get('reason', ''),
            'anomalies': fraud_data.get('anomalies', [])
        })
    return analysis

def analyze_false_negatives(false_negatives: List[str], ground_truth: Dict[str, Dict]) -> List[Dict]:
    """Analyze false negatives to understand what was missed."""
    analysis = []
    for fn_id in false_negatives:
        truth_data = ground_truth.get(fn_id, {})
        analysis.append({
            'transaction_id': fn_id,
            'fraud_scenario': truth_data.get('fraud_scenario', ''),
            'expected_signals': truth_data.get('fraud_signals', [])
        })
    return analysis

def main():
    script_dir = Path(__file__).parent.parent
    ground_truth_path = script_dir / 'dataset' / 'ground_truth' / 'public_1.csv'
    detected_path = script_dir / 'fraud_graph' / 'results' / 'final_fraud.json'
    
    print('=' * 80)
    print('COMPARAISON: final_fraud.json vs public_1.csv')
    print('=' * 80)
    print()
    
    if not ground_truth_path.exists():
        print(f'❌ Fichier ground truth introuvable: {ground_truth_path}')
        return
    
    if not detected_path.exists():
        print(f'❌ Fichier final_fraud.json introuvable: {detected_path}')
        print('💡 Exécutez d\'abord l\'analyse avec: just lang')
        return
    
    ground_truth = load_ground_truth(ground_truth_path)
    detected = load_detected_frauds(detected_path)
    
    results = compare_results(ground_truth, detected)
    
    print(f'📊 MÉTRIQUES:')
    print(f'  ✅ Vrais Positifs (TP): {results["tp_count"]}/{results["total_ground_truth"]}')
    print(f'  ❌ Faux Positifs (FP): {results["fp_count"]}')
    print(f'  ⚠️  Faux Négatifs (FN): {results["fn_count"]}')
    print()
    print(f'  📈 Précision: {results["precision"]:.2%}')
    print(f'  📈 Rappel (Recall): {results["recall"]:.2%}')
    print(f'  📈 F1-Score: {results["f1_score"]:.2%}')
    print()
    
    print(f'✅ VRAIS POSITIFS ({results["tp_count"]}):')
    for tp_id in results['true_positives']:
        truth = ground_truth[tp_id]
        detected_data = detected[tp_id]
        print(f'  - {tp_id}')
        print(f'    Scénario: {truth["fraud_scenario"]}')
        print(f'    Signaux attendus: {", ".join(truth["fraud_signals"])}')
        print(f'    Raisons détectées: {detected_data.get("reason", "N/A")}')
        print()
    
    if results['false_positives']:
        print(f'❌ FAUX POSITIFS ({results["fp_count"]}):')
        fp_analysis = analyze_false_positives(results['false_positives'], detected, ground_truth)
        for fp in fp_analysis:
            print(f'  - {fp["transaction_id"]}')
            print(f'    Raisons: {fp["reasons"]}')
            print(f'    Anomalies: {", ".join(fp["anomalies"])}')
            print()
    
    if results['false_negatives']:
        print(f'⚠️  FAUX NÉGATIFS ({results["fn_count"]}):')
        fn_analysis = analyze_false_negatives(results['false_negatives'], ground_truth)
        for fn in fn_analysis:
            print(f'  - {fn["transaction_id"]}')
            print(f'    Scénario: {fn["fraud_scenario"]}')
            print(f'    Signaux attendus: {", ".join(fn["expected_signals"])}')
            print()
    
    print('=' * 80)
    print(f'🎯 RÉSUMÉ: {results["tp_count"]}/{results["total_ground_truth"]} fraudes correctement détectées')
    print('=' * 80)

if __name__ == '__main__':
    main()
