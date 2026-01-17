#!/usr/bin/env python3
"""
Evaluation Script for Fraud Detection Results

This script compares predictions against ground truth and outputs:
- A list of all predicted transactions with 1 (correct) or 0 (incorrect)
- Summary metrics (precision, recall, F1)

Usage:
    python scripts/evaluate_results.py --predictions <predictions_file> --ground-truth <ground_truth_file>
    
Examples:
    python scripts/evaluate_results.py --predictions results.json --ground-truth dataset/ground_truth/public_1.csv
    python scripts/evaluate_results.py -p results.json -g dataset/ground_truth/public_1.csv --output evaluation.json
"""

import argparse
import json
import csv
import sys
from pathlib import Path
from typing import Set, List, Dict, Any


def load_ground_truth(filepath: Path) -> Set[str]:
    """Load ground truth transaction IDs from CSV file.
    
    Args:
        filepath: Path to the ground truth CSV file
        
    Returns:
        Set of transaction IDs that are actual positives (fraudulent)
    """
    ground_truth_ids = set()
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            transaction_id = row.get('transaction_id', '').strip()
            if transaction_id:
                ground_truth_ids.add(transaction_id)
    
    return ground_truth_ids


def load_predictions(filepath: Path) -> List[Dict[str, Any]]:
    """Load predictions from JSON file.
    
    Supports multiple formats:
    - List of transaction IDs (strings)
    - List of objects with 'transaction_id' or 'id' field
    - Object with 'predictions' or 'results' key containing the list
    
    Args:
        filepath: Path to the predictions JSON file
        
    Returns:
        List of prediction dictionaries with at least 'transaction_id' field
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle different formats
    predictions = []
    
    # If it's a dict with a key containing the predictions
    if isinstance(data, dict):
        for key in ['predictions', 'results', 'transactions', 'data']:
            if key in data:
                data = data[key]
                break
    
    # If it's a list
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                # List of transaction IDs
                predictions.append({'transaction_id': item})
            elif isinstance(item, dict):
                # Extract transaction_id from various possible keys
                tx_id = (
                    item.get('transaction_id') or 
                    item.get('id') or 
                    item.get('transactionId') or
                    item.get('tx_id')
                )
                if tx_id:
                    predictions.append({
                        'transaction_id': tx_id,
                        **item
                    })
    
    return predictions


def evaluate(predictions: List[Dict[str, Any]], ground_truth: Set[str]) -> Dict[str, Any]:
    """Evaluate predictions against ground truth.
    
    Args:
        predictions: List of prediction dictionaries
        ground_truth: Set of actual positive transaction IDs
        
    Returns:
        Evaluation results dictionary
    """
    results = []
    true_positives = 0
    false_positives = 0
    
    predicted_ids = set()
    
    for pred in predictions:
        tx_id = pred['transaction_id']
        predicted_ids.add(tx_id)
        
        # 1 if correctly predicted (in ground truth), 0 otherwise
        is_correct = 1 if tx_id in ground_truth else 0
        
        if is_correct:
            true_positives += 1
        else:
            false_positives += 1
        
        results.append({
            'transaction_id': tx_id,
            'correct': is_correct,
            'label': 'TP' if is_correct else 'FP'
        })
    
    # Calculate false negatives (in ground truth but not predicted)
    false_negatives = len(ground_truth - predicted_ids)
    
    # Calculate metrics
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    # Find missed transactions (false negatives)
    missed = ground_truth - predicted_ids
    
    return {
        'results': results,
        'summary': {
            'total_predictions': len(predictions),
            'total_ground_truth': len(ground_truth),
            'true_positives': true_positives,
            'false_positives': false_positives,
            'false_negatives': false_negatives,
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1_score': round(f1, 4)
        },
        'missed_transactions': list(missed)
    }


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate fraud detection predictions against ground truth',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/evaluate_results.py -p results.json -g dataset/ground_truth/public_1.csv
    python scripts/evaluate_results.py --predictions my_predictions.json --ground-truth gt.csv --output eval.json
        """
    )
    
    parser.add_argument(
        '-p', '--predictions',
        required=True,
        help='Path to predictions JSON file'
    )
    
    parser.add_argument(
        '-g', '--ground-truth',
        required=True,
        help='Path to ground truth CSV file'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Path to save evaluation results (optional, prints to stdout if not specified)'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Only output JSON, no summary text'
    )
    
    args = parser.parse_args()
    
    # Resolve paths
    predictions_path = Path(args.predictions)
    ground_truth_path = Path(args.ground_truth)
    
    # Validate files exist
    if not predictions_path.exists():
        print(f"❌ Error: Predictions file not found: {predictions_path}", file=sys.stderr)
        sys.exit(1)
    
    if not ground_truth_path.exists():
        print(f"❌ Error: Ground truth file not found: {ground_truth_path}", file=sys.stderr)
        sys.exit(1)
    
    # Load data
    if not args.quiet:
        print(f"📂 Loading predictions from: {predictions_path}")
    predictions = load_predictions(predictions_path)
    
    if not args.quiet:
        print(f"📂 Loading ground truth from: {ground_truth_path}")
    ground_truth = load_ground_truth(ground_truth_path)
    
    if not predictions:
        print("❌ Error: No predictions found in file", file=sys.stderr)
        sys.exit(1)
    
    # Evaluate
    evaluation = evaluate(predictions, ground_truth)
    
    # Output results
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(evaluation, f, indent=2, ensure_ascii=False)
        if not args.quiet:
            print(f"💾 Results saved to: {output_path}")
    
    # Print summary
    if not args.quiet:
        summary = evaluation['summary']
        print(f"\n{'='*50}")
        print("📊 EVALUATION SUMMARY")
        print(f"{'='*50}")
        print(f"Total Predictions:    {summary['total_predictions']}")
        print(f"Total Ground Truth:   {summary['total_ground_truth']}")
        print(f"{'─'*50}")
        print(f"True Positives (TP):  {summary['true_positives']}")
        print(f"False Positives (FP): {summary['false_positives']}")
        print(f"False Negatives (FN): {summary['false_negatives']}")
        print(f"{'─'*50}")
        print(f"Precision:            {summary['precision']:.2%}")
        print(f"Recall:               {summary['recall']:.2%}")
        print(f"F1 Score:             {summary['f1_score']:.2%}")
        print(f"{'='*50}")
        
        # Show results list
        print(f"\n📋 TRANSACTION RESULTS (1=correct, 0=incorrect):")
        print(f"{'─'*50}")
        for r in evaluation['results']:
            status = "✅" if r['correct'] else "❌"
            print(f"  {status} {r['transaction_id']}: {r['correct']}")
        
        if evaluation['missed_transactions']:
            print(f"\n⚠️  MISSED TRANSACTIONS (False Negatives):")
            for tx_id in evaluation['missed_transactions']:
                print(f"  ❌ {tx_id}")
    else:
        # Quiet mode - just output JSON
        print(json.dumps(evaluation, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
