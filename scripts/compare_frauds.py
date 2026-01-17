#!/usr/bin/env python3
"""Script pour comparer les fraudes réelles (ground truth) avec les fraudes détectées."""

import json
import csv
import sys
from pathlib import Path

# Chemins des fichiers
GROUND_TRUTH_PATH = Path("dataset/ground_truth/public_1.csv")
FRAUD_JSON_PATH = Path("fraud_graph/results/fraud.json")


def load_ground_truth() -> dict:
    """Charge les fraudes réelles depuis le CSV.
    
    Returns:
        Dictionnaire {transaction_id: {signals, scenario, ...}}
    """
    frauds = {}
    if not GROUND_TRUTH_PATH.exists():
        print(f"❌ Fichier ground truth non trouvé: {GROUND_TRUTH_PATH}")
        return frauds
    
    with open(GROUND_TRUTH_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tx_id = row['transaction_id']
            frauds[tx_id] = {
                'transaction_id': tx_id,
                'scenario': row['fraud_scenario'],
                'signals': [s.strip() for s in row['fraud_signals'].split(',')],
                'timestamp': row['timestamp'],
            }
    
    return frauds


def load_detected_frauds() -> dict:
    """Charge les fraudes détectées depuis fraud.json.
    
    Returns:
        Dictionnaire {transaction_id: {score, decision, features, ...}}
    """
    frauds = {}
    if not FRAUD_JSON_PATH.exists():
        print(f"❌ Fichier fraud.json non trouvé: {FRAUD_JSON_PATH}")
        return frauds
    
    with open(FRAUD_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for item in data:
            tx_id = item['transaction_id']
            frauds[tx_id] = {
                'transaction_id': tx_id,
                'risk_score': item.get('risk_score', 0.0),
                'decision': item.get('decision', 'UNKNOWN'),
                'features': item.get('features', {}),
                'explanation': item.get('explanation', ''),
            }
    
    return frauds


def analyze_comparison(real_frauds: dict, detected_frauds: dict) -> dict:
    """Analyse la comparaison entre fraudes réelles et détectées.
    
    Args:
        real_frauds: Dictionnaire des fraudes réelles
        detected_frauds: Dictionnaire des fraudes détectées
        
    Returns:
        Dictionnaire avec les statistiques
    """
    real_ids = set(real_frauds.keys())
    detected_ids = set(detected_frauds.keys())
    
    # Calculs de base
    true_positives = real_ids & detected_ids
    false_positives = detected_ids - real_ids
    false_negatives = real_ids - detected_ids
    
    # Métriques
    total_real = len(real_ids)
    total_detected = len(detected_ids)
    tp_count = len(true_positives)
    fp_count = len(false_positives)
    fn_count = len(false_negatives)
    
    precision = tp_count / total_detected if total_detected > 0 else 0.0
    recall = tp_count / total_real if total_real > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    # Analyse des signaux des fraudes manquées
    missing_signals = {}
    for tx_id in false_negatives:
        signals = real_frauds[tx_id]['signals']
        for signal in signals:
            missing_signals[signal] = missing_signals.get(signal, 0) + 1
    
    # Analyse des scores des vraies fraudes détectées
    tp_scores = [detected_frauds[tx_id]['risk_score'] for tx_id in true_positives]
    avg_tp_score = sum(tp_scores) / len(tp_scores) if tp_scores else 0.0
    min_tp_score = min(tp_scores) if tp_scores else 0.0
    max_tp_score = max(tp_scores) if tp_scores else 0.0
    
    # Analyse des scores des faux positifs
    fp_scores = [detected_frauds[tx_id]['risk_score'] for tx_id in list(false_positives)[:100]]
    avg_fp_score = sum(fp_scores) / len(fp_scores) if fp_scores else 0.0
    
    return {
        'total_real': total_real,
        'total_detected': total_detected,
        'true_positives': tp_count,
        'false_positives': fp_count,
        'false_negatives': fn_count,
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'true_positive_ids': sorted(true_positives),
        'false_positive_ids': sorted(list(false_positives)[:20]),  # Limiter à 20 pour l'affichage
        'false_negative_ids': sorted(false_negatives),
        'missing_signals': missing_signals,
        'avg_tp_score': avg_tp_score,
        'min_tp_score': min_tp_score,
        'max_tp_score': max_tp_score,
        'avg_fp_score': avg_fp_score,
    }


def print_report(stats: dict, real_frauds: dict, detected_frauds: dict):
    """Affiche le rapport de comparaison.
    
    Args:
        stats: Statistiques de comparaison
        real_frauds: Dictionnaire des fraudes réelles
        detected_frauds: Dictionnaire des fraudes détectées
    """
    print("=" * 70)
    print("📊 RAPPORT DE COMPARAISON : FRAUDES RÉELLES vs DÉTECTÉES")
    print("=" * 70)
    print()
    
    # Statistiques générales
    print("📈 STATISTIQUES GÉNÉRALES")
    print("-" * 70)
    print(f"  Fraudes réelles (ground truth):     {stats['total_real']}")
    print(f"  Fraudes détectées (fraud.json):     {stats['total_detected']}")
    print()
    
    # Métriques de performance
    print("🎯 MÉTRIQUES DE PERFORMANCE")
    print("-" * 70)
    print(f"  Vrais positifs (TP):                {stats['true_positives']}/{stats['total_real']}")
    print(f"  Faux positifs (FP):                 {stats['false_positives']}")
    print(f"  Faux négatifs (FN):                 {stats['false_negatives']}")
    print()
    print(f"  Précision (TP / (TP + FP)):         {stats['precision']:.2%}")
    print(f"  Rappel (TP / (TP + FN)):            {stats['recall']:.2%}")
    print(f"  F1-Score:                           {stats['f1_score']:.2%}")
    print()
    
    # Analyse des scores
    print("📊 ANALYSE DES SCORES")
    print("-" * 70)
    if stats['true_positives'] > 0:
        print(f"  Scores des vraies fraudes détectées:")
        print(f"    Moyenne: {stats['avg_tp_score']:.2f}")
        print(f"    Min:     {stats['min_tp_score']:.2f}")
        print(f"    Max:     {stats['max_tp_score']:.2f}")
    if stats['false_positives'] > 0:
        print(f"  Score moyen des faux positifs:     {stats['avg_fp_score']:.2f}")
    print()
    
    # Vraies fraudes détectées
    if stats['true_positive_ids']:
        print("✅ FRAUDES RÉELLES DÉTECTÉES")
        print("-" * 70)
        for tx_id in stats['true_positive_ids']:
            real = real_frauds[tx_id]
            detected = detected_frauds[tx_id]
            print(f"  {tx_id[:8]}...")
            print(f"    Scénario: {real['scenario']}")
            print(f"    Signaux attendus: {', '.join(real['signals'])}")
            print(f"    Score détecté: {detected['risk_score']:.2f}")
            print()
    
    # Fraudes manquées
    if stats['false_negative_ids']:
        print("❌ FRAUDES RÉELLES NON DÉTECTÉES")
        print("-" * 70)
        for tx_id in stats['false_negative_ids']:
            real = real_frauds[tx_id]
            print(f"  {tx_id[:8]}...")
            print(f"    Scénario: {real['scenario']}")
            print(f"    Signaux attendus: {', '.join(real['signals'])}")
            print()
        
        # Analyse des signaux manqués
        if stats['missing_signals']:
            print("  Signaux les plus fréquents dans les fraudes manquées:")
            for signal, count in sorted(stats['missing_signals'].items(), key=lambda x: -x[1]):
                print(f"    {signal}: {count}/{stats['false_negatives']}")
            print()
    
    # Faux positifs (échantillon)
    if stats['false_positives'] > 0:
        print(f"⚠️  FAUX POSITIFS (échantillon de 20 sur {stats['false_positives']})")
        print("-" * 70)
        for tx_id in stats['false_positive_ids'][:20]:
            detected = detected_frauds[tx_id]
            print(f"  {tx_id[:8]}... Score: {detected['risk_score']:.2f}")
        if stats['false_positives'] > 20:
            print(f"  ... et {stats['false_positives'] - 20} autres")
        print()
    
    print("=" * 70)


def main():
    """Point d'entrée principal."""
    print("🔍 Chargement des données...")
    print()
    
    # Charger les données
    real_frauds = load_ground_truth()
    detected_frauds = load_detected_frauds()
    
    if not real_frauds:
        print("❌ Aucune fraude réelle trouvée")
        sys.exit(1)
    
    if not detected_frauds:
        print("❌ Aucune fraude détectée trouvée")
        sys.exit(1)
    
    # Analyser la comparaison
    stats = analyze_comparison(real_frauds, detected_frauds)
    
    # Afficher le rapport
    print_report(stats, real_frauds, detected_frauds)


if __name__ == "__main__":
    main()
