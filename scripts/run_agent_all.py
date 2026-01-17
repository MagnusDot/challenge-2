#!/usr/bin/env python3
"""Run agent on all transaction IDs from ground truth JSON file."""

import json
import subprocess
import sys
from pathlib import Path


def run_agent_all(json_path: str = 'dataset/ground_truth/transaction_ids.json') -> None:
    """Run agent on all transaction IDs from JSON file.
    
    Args:
        json_path: Path to JSON file containing transaction IDs
    """
    # Load transaction IDs
    with open(json_path, 'r', encoding='utf-8') as f:
        transaction_ids = json.load(f)
    
    print(f"🚀 Running LangGraph agent on {len(transaction_ids)} transactions...")
    print("⚠️  Make sure API is running (just api-dev)\n")
    
    success_count = 0
    failed_count = 0
    
    for i, transaction_id in enumerate(transaction_ids, 1):
        print(f"📋 [{i}/{len(transaction_ids)}] Processing transaction: {transaction_id}")
        
        try:
            # Run just agent command
            result = subprocess.run(
                ['just', 'agent', transaction_id],
                check=False,
                capture_output=False
            )
            
            if result.returncode == 0:
                success_count += 1
                print(f"✅ Success for {transaction_id}\n")
            else:
                failed_count += 1
                print(f"❌ Failed for {transaction_id}\n")
        except Exception as e:
            failed_count += 1
            print(f"❌ Error for {transaction_id}: {e}\n")
    
    print("=" * 60)
    print(f"✅ All agent analyses complete!")
    print(f"   Success: {success_count}/{len(transaction_ids)}")
    print(f"   Failed: {failed_count}/{len(transaction_ids)}")


if __name__ == '__main__':
    json_path = sys.argv[1] if len(sys.argv) > 1 else 'dataset/ground_truth/transaction_ids.json'
    run_agent_all(json_path)
