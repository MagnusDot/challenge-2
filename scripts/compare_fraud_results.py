import json
import csv
from pathlib import Path
from typing import Set, Dict, List

def load_ground_truth() -> Dict[str, Dict]:
    ground_truth_file = Path('dataset/ground_truth/public_1.csv')
    ground_truth = {}
    
    with open(ground_truth_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            transaction_id = row['transaction_id'].strip()
            if transaction_id:
                ground_truth[transaction_id] = {
                    'sender_biotag': row.get('sender_biotag', ''),
                    'attack_id': row.get('attack_id', ''),
                    'fraud_scenario': row.get('fraud_scenario', ''),
                    'timestamp': row.get('timestamp', ''),
                    'fraud_signals': row.get('fraud_signals', '').split(',') if row.get('fraud_signals') else []
                }
    
    return ground_truth

def load_detected_frauds() -> Dict[str, Dict]:
    detected_file = Path('fraud_graph/results/real_fraud.json')
    
    if not detected_file.exists():
        return {}
    
    with open(detected_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    detected = {}
    for fraud in data.get('frauds', []):
        transaction_id = fraud.get('transaction_id', '').strip()
        if transaction_id:
            detected[transaction_id] = {
                'risk_level': fraud.get('risk_level', ''),
                'risk_score': fraud.get('risk_score', 0),
                'reason': fraud.get('reason', ''),
                'anomalies': fraud.get('anomalies', [])
            }
    
    return detected

def analyze_results():
    ground_truth = load_ground_truth()
    detected = load_detected_frauds()
    
    ground_truth_ids = set(ground_truth.keys())
    detected_ids = set(detected.keys())
    
    true_positives = ground_truth_ids & detected_ids
    false_positives = detected_ids - ground_truth_ids
    false_negatives = ground_truth_ids - detected_ids
    
    print("=" * 80)
    print("📊 ANALYSE DES RÉSULTATS DE DÉTECTION DE FRAUDE")
    print("=" * 80)
    print()
    
    print(f"✅ Vraies fraudes (ground truth): {len(ground_truth_ids)}")
    print(f"🚨 Fraud détectées par l'agent: {len(detected_ids)}")
    print()
    
    print(f"✅ Vrais positifs (TP): {len(true_positives)}")
    print(f"❌ Faux positifs (FP): {len(false_positives)}")
    print(f"⚠️  Faux négatifs (FN): {len(false_negatives)}")
    print()
    
    precision = len(true_positives) / len(detected_ids) if detected_ids else 0
    recall = len(true_positives) / len(ground_truth_ids) if ground_truth_ids else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    print(f"📈 Précision: {precision:.2%} ({len(true_positives)}/{len(detected_ids)})")
    print(f"📈 Rappel: {recall:.2%} ({len(true_positives)}/{len(ground_truth_ids)})")
    print(f"📈 F1-Score: {f1:.2%}")
    print()
    
    print("=" * 80)
    print("✅ VRAIS POSITIFS (Fraudes correctement détectées)")
    print("=" * 80)
    for tx_id in sorted(true_positives):
        gt = ground_truth[tx_id]
        det = detected[tx_id]
        print(f"\n🔍 {tx_id}")
        print(f"   Scénario: {gt['fraud_scenario']}")
        print(f"   Signaux attendus: {', '.join(gt['fraud_signals'])}")
        print(f"   Raison détectée: {det['reason'][:150]}...")
        print(f"   Anomalies détectées: {', '.join(det['anomalies'][:3])}")
    
    print()
    print("=" * 80)
    print("❌ FAUX POSITIFS (Transactions détectées mais pas de vraies fraudes)")
    print("=" * 80)
    for tx_id in sorted(false_positives)[:10]:
        det = detected[tx_id]
        print(f"\n🔍 {tx_id}")
        print(f"   Raison: {det['reason'][:150]}...")
        print(f"   Anomalies: {', '.join(det['anomalies'][:3])}")
    
    if len(false_positives) > 10:
        print(f"\n   ... et {len(false_positives) - 10} autres faux positifs")
    
    print()
    print("=" * 80)
    print("⚠️  FAUX NÉGATIFS (Vraies fraudes non détectées)")
    print("=" * 80)
    for tx_id in sorted(false_negatives):
        gt = ground_truth[tx_id]
        print(f"\n🔍 {tx_id}")
        print(f"   Scénario: {gt['fraud_scenario']}")
        print(f"   Signaux attendus: {', '.join(gt['fraud_signals'])}")
        print(f"   Sender: {gt['sender_biotag']}")
        print(f"   Timestamp: {gt['timestamp']}")
    
    print()
    print("=" * 80)
    print("📋 ANALYSE DES SCÉNARIOS DE FRAUDE")
    print("=" * 80)
    
    scenario_stats = {}
    for tx_id in ground_truth_ids:
        scenario = ground_truth[tx_id]['fraud_scenario']
        if scenario not in scenario_stats:
            scenario_stats[scenario] = {'total': 0, 'detected': 0}
        scenario_stats[scenario]['total'] += 1
        if tx_id in detected_ids:
            scenario_stats[scenario]['detected'] += 1
    
    for scenario, stats in sorted(scenario_stats.items()):
        recall_scenario = stats['detected'] / stats['total'] if stats['total'] > 0 else 0
        print(f"\n{scenario}:")
        print(f"   Détecté: {stats['detected']}/{stats['total']} ({recall_scenario:.2%})")
    
    print()
    print("=" * 80)
    print("📋 ANALYSE DES SIGNAUX DE FRAUDE")
    print("=" * 80)
    
    signal_stats = {}
    for tx_id in ground_truth_ids:
        signals = ground_truth[tx_id]['fraud_signals']
        detected = tx_id in detected_ids
        for signal in signals:
            if signal not in signal_stats:
                signal_stats[signal] = {'total': 0, 'detected': 0}
            signal_stats[signal]['total'] += 1
            if detected:
                signal_stats[signal]['detected'] += 1
    
    for signal, stats in sorted(signal_stats.items(), key=lambda x: x[1]['total'], reverse=True):
        recall_signal = stats['detected'] / stats['total'] if stats['total'] > 0 else 0
        print(f"\n{signal}:")
        print(f"   Détecté: {stats['detected']}/{stats['total']} ({recall_signal:.2%})")
    
    return {
        'true_positives': list(true_positives),
        'false_positives': list(false_positives),
        'false_negatives': list(false_negatives),
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'scenario_stats': scenario_stats,
        'signal_stats': signal_stats
    }

if __name__ == "__main__":
    results = analyze_results()
    
    output_file = Path('scripts/results/fraud_comparison_analysis.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Analyse sauvegardée dans: {output_file}")
