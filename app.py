import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path

from helpers.config import (
    PROJECT_ROOT, MAX_CONCURRENT_REQUESTS, SAVE_INTERVAL,
    DATASET_PATH, DATASET_FOLDER, SYSTEM_PROMPT_PATH
)
from helpers.prompt_loader import load_analysis_prompt
from helpers.analysis_state import AnalysisState
from helpers.statistics import calculate_statistics
from helpers.display import display_statistics
from core.runner_setup import setup_runner
from core.transaction_analyzer import analyze_transaction_with_agent

async def main():
    print("="*70)
    print("🚀 ANALYZING ALL TRANSACTIONS WITH CHALLENGE AGENT")
    print("="*70)
    
    openai_api_key = os.getenv('OPENAI_API_KEY')
    google_api_key = os.getenv('GOOGLE_API_KEY')
    openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not openai_api_key and not google_api_key and not openrouter_api_key:
        print("❌ Error: No API key found in .env")
        print("💡 Add OPENROUTER_API_KEY, OPENAI_API_KEY or GOOGLE_API_KEY to your .env file")
        sys.exit(1)
    
    if openai_api_key:
        os.environ['OPENAI_API_KEY'] = openai_api_key
    if google_api_key:
        os.environ['GOOGLE_API_KEY'] = google_api_key
    if openrouter_api_key:
        os.environ['OPENROUTER_API_KEY'] = openrouter_api_key
    
    print(f"\n📂 Loading transactions from: {DATASET_PATH}")
    print(f"📁 Dataset folder: {DATASET_FOLDER}")
    
    if not DATASET_PATH.exists():
        print(f"❌ Error: Dataset file not found: {DATASET_PATH}")
        dataset_dir = PROJECT_ROOT / "dataset"
        if dataset_dir.exists():
            available_folders = [d.name for d in dataset_dir.iterdir() if d.is_dir()]
            if available_folders:
                print(f"💡 Available dataset folders: {', '.join(available_folders)}")
                print(f"💡 Set DATASET_FOLDER in .env file or use: DATASET_FOLDER={available_folders[0]}")
        sys.exit(1)
    
    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        transactions = json.load(f)
    
    total = len(transactions)
    print(f"✅ {total} transactions loaded")
    
    print(f"\n⚠️  You are about to analyze {total} transactions.")
    print("💰 This will consume API credits!")
    response = input("\n❓ Continue? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y', 'oui', 'o']:
        print("❌ Analysis cancelled")
        sys.exit(0)
    
    print(f"\n📝 Loading analysis prompt template...")
    print(f"📄 Prompt file: {SYSTEM_PROMPT_PATH}")
    try:
        prompt_template = load_analysis_prompt()
        print(f"✅ Prompt template loaded successfully")
    except FileNotFoundError:
        print(f"❌ Error: Prompt template file not found")
        sys.exit(1)
    
    runner = setup_runner()
    
    print(f"\n{'='*70}")
    print("📊 STARTING PARALLEL ANALYSIS")
    print(f"{'='*70}")
    
    start_time = datetime.now()
    user_id = "fraud_analyst"
    
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    results_dir = PROJECT_ROOT / "scripts" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    output_file = results_dir / f"transaction_risk_analysis_{timestamp}.json"
    
    state = AnalysisState(total, start_time, output_file)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    print(f"\n⏱️  Analysis started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"👤 User ID: {user_id}")
    print(f"🔄 Max concurrent requests: {MAX_CONCURRENT_REQUESTS}")
    print(f"💾 Results file: {output_file.name} (sauvegarde tous les {SAVE_INTERVAL} résultats)")
    print(f"💡 Each transaction will create its own session")
    print(f"\n{'─'*70}")
    
    tasks = []
    for i, transaction in enumerate(transactions, 1):
        task = analyze_transaction_with_agent(
            runner, 
            transaction, 
            i, 
            state,
            prompt_template,
            semaphore,
            user_id=user_id
        )
        tasks.append(task)
    
    print(f"🚀 Lancement de {len(tasks)} analyses en parallèle...")
    await asyncio.gather(*tasks, return_exceptions=True)
    
    print(f"\n{'─'*70}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    results = state.get_results()
    
    bar_length = 40
    bar = "█" * bar_length
    print(f"\n{'='*70}")
    print(f"📊 Progress: [{bar}] 100.0%")
    print(f"✅ All {total} transactions analyzed!")
    print(f"⏱️  Total time: {duration:.1f}s ({duration/60:.1f} minutes)")
    print(f"⚡ Speedup: ~{total/(duration/60):.1f} transactions/minute")
    print(f"{'='*70}")
    
    state.save_results()
    
    risk_counts, avg_score, error_count, total_tokens_used, tokens_are_estimated = calculate_statistics(results)
    
    summary_file = results_dir / f"transaction_analysis_summary_{timestamp}.json"
    summary_data = {
        "analysis_info": {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "duration_minutes": duration / 60,
            "total_transactions": len(results),
            "max_concurrent_requests": MAX_CONCURRENT_REQUESTS,
            "throughput_per_second": len(results) / duration if duration > 0 else 0,
            "average_time_per_transaction": duration / len(results) if len(results) > 0 else 0
        },
        "token_usage": {
            "prompt_tokens": total_tokens_used["prompt_tokens"],
            "completion_tokens": total_tokens_used["completion_tokens"],
            "total_tokens": total_tokens_used["total_tokens"],
            "average_tokens_per_transaction": total_tokens_used["total_tokens"] / len(results) if len(results) > 0 else 0,
            "estimated": tokens_are_estimated,
            "note": "Tokens were estimated using approximation formula" if tokens_are_estimated else "Tokens captured from API"
        },
        "risk_distribution": {
            level: {
                "count": count,
                "percentage": (count / len(results)) * 100 if len(results) > 0 else 0
            }
            for level, count in risk_counts.items()
        },
        "scores": {
            "average_risk_score": avg_score,
            "error_count": error_count
        }
    }
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*70}")
    print("💾 FINAL RESULTS SAVED")
    print(f"{'='*70}")
    print(f"Results file: {output_file.name}")
    print(f"Summary file: {summary_file.name}")
    
    display_statistics(results, duration, risk_counts, avg_score, error_count, 
                      total_tokens_used, tokens_are_estimated)
    
    print(f"\n{'='*70}")
    print(f"✅ PARALLEL ANALYSIS COMPLETE!")
    print(f"📄 Results saved in: {output_file.name}")
    print(f"📊 Summary saved in: {summary_file.name}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
