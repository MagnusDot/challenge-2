from datetime import datetime
from typing import Dict, Any, List

RISK_EMOJI = {
    "low": "🟢",
    "medium": "🟡",
    "high": "🟠",
    "critical": "🔴"
}

def get_risk_emoji(risk_level: str) -> str:
    return RISK_EMOJI.get(risk_level, "⚪")

def format_progress_line(transaction_num: int, result: Dict[str, Any], token_usage: Dict[str, Any], 
                        completed: int, total: int, state_start_time: datetime) -> str:
    risk_emoji = get_risk_emoji(result['risk_level'])
    progress_pct = (completed / total) * 100
    elapsed = (datetime.now() - state_start_time).total_seconds()
    avg_time = elapsed / completed if completed > 0 else 0
    remaining = total - completed
    eta = avg_time * remaining
    total_tokens = token_usage.get("total_tokens", 0)
    token_marker = "~" if token_usage.get("estimated", False) else " "
    
    return f"✅ [{transaction_num:3d}] {risk_emoji} {result['risk_level']:8s} | Score: {result['risk_score']:3d}/100 | Tokens: {token_marker}{total_tokens:5d} | Progress: {completed}/{total} ({progress_pct:.1f}%) | ETA: {eta:.0f}s"

def display_statistics(results: List[Dict[str, Any]], duration: float, risk_counts: Dict[str, int], 
                      avg_score: float, error_count: int, total_tokens_used: Dict[str, int], 
                      tokens_are_estimated: bool):
    print(f"\n{'='*70}")
    print("📊 ANALYSIS STATISTICS")
    print(f"{'='*70}")
    print(f"Total transactions analyzed: {len(results)}")
    print(f"Execution time: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"Average time per transaction: {duration/len(results):.2f} seconds")
    print(f"Throughput: {len(results)/duration:.2f} transactions/second")
    print(f"Average risk score: {avg_score:.1f}/100")
    if error_count > 0:
        print(f"Errors encountered: {error_count}")
    
    print(f"\n💰 TOKEN USAGE{' (ESTIMATED)' if tokens_are_estimated else ''}:")
    print(f"  Prompt tokens:     {total_tokens_used['prompt_tokens']:,}")
    print(f"  Completion tokens: {total_tokens_used['completion_tokens']:,}")
    print(f"  Total tokens:      {total_tokens_used['total_tokens']:,}")
    if len(results) > 0:
        avg_tokens = total_tokens_used['total_tokens'] / len(results)
        print(f"  Average per transaction: {avg_tokens:.1f} tokens")
    if tokens_are_estimated:
        print(f"  ⚠️  Note: Tokens were estimated (API didn't provide usage data)")
        print(f"     To see API event details, run: just analyze-parallel-debug")
    
    print(f"\n📈 Risk level distribution:")
    for risk_level in ['low', 'medium', 'high', 'critical', 'error', 'unknown']:
        count = risk_counts.get(risk_level, 0)
        if count > 0:
            percentage = (count / len(results)) * 100
            emoji = {
                'low': '🟢',
                'medium': '🟡',
                'high': '🟠',
                'critical': '🔴',
                'error': '❌',
                'unknown': '⚪'
            }.get(risk_level, '⚪')
            print(f"  {emoji} {risk_level.upper():10s}: {count:5d} ({percentage:5.1f}%)")
