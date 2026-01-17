#!/usr/bin/env python3
"""Extract transaction IDs from ground truth CSV file and save to JSON."""

import csv
import json
import sys
from pathlib import Path


def extract_transaction_ids(csv_path: str, output_path: str) -> None:
    """Extract transaction IDs from CSV and save to JSON.
    
    Args:
        csv_path: Path to the ground truth CSV file
        output_path: Path where to save the JSON file
    """
    transaction_ids = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            transaction_id = row.get('transaction_id', '').strip()
            if transaction_id:
                transaction_ids.append(transaction_id)
    
    # Create output directory if it doesn't exist
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Save to JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(transaction_ids, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Extracted {len(transaction_ids)} transaction IDs")
    print(f"💾 Saved to {output_path}")


if __name__ == '__main__':
    csv_path = 'dataset/ground_truth/public_1.csv'
    output_path = 'dataset/ground_truth/transaction_ids.json'
    
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    
    extract_transaction_ids(csv_path, output_path)
