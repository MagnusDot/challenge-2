from typing import Dict, List, Any, Tuple

def calculate_statistics(results: List[Dict[str, Any]]) -> Tuple[Dict[str, int], float, int, Dict[str, int], bool]:
    risk_counts = {}
    total_score = 0
    error_count = 0
    total_tokens_used = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }
    tokens_are_estimated = False

    for result in results:
        risk_level = result.get('risk_level', 'unknown')
        risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1

        score = result.get('risk_score', 0)
        if score >= 0:
            total_score += score
        else:
            error_count += 1

        token_usage = result.get('token_usage', {})
        total_tokens_used["prompt_tokens"] += token_usage.get("prompt_tokens", 0)
        total_tokens_used["completion_tokens"] += token_usage.get("completion_tokens", 0)
        total_tokens_used["total_tokens"] += token_usage.get("total_tokens", 0)

        if token_usage.get("estimated", False):
            tokens_are_estimated = True

    avg_score = total_score / (len(results) - error_count) if (len(results) - error_count) > 0 else 0

    return risk_counts, avg_score, error_count, total_tokens_used, tokens_are_estimated