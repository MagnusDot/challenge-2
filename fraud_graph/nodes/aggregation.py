import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from ..state import FraudState
_save_lock = asyncio.Lock()
WEIGHT_ACCOUNT_DRAINED = 0.3
WEIGHT_BALANCE_VERY_LOW = 0.03
WEIGHT_ABNORMAL_AMOUNT = 0.1
WEIGHT_HIGH_AMOUNT = 0.15
WEIGHT_LARGE_WITHDRAWAL = 0.01
WEIGHT_NEW_DEST = 0.05
WEIGHT_NEW_MERCHANT = 0.1
WEIGHT_POST_WITHDRAWAL = 0.08
WEIGHT_PATTERN_MULTIPLE_WITHDRAWALS = 0.15
WEIGHT_SUSPICIOUS_TYPE = 0.12
WEIGHT_IMPOSSIBLE_TRAVEL = 0.2
WEIGHT_LOCATION_ANOMALY = 0.18
WEIGHT_LOCATION_MISMATCH = 0.01
WEIGHT_NEW_VENUE = 0.08
WEIGHT_GPS_CONTRADICTION = 0.02
WEIGHT_LOCATION_MISSING = 0.01
WEIGHT_TIME_CORRELATION = 0.25
WEIGHT_PHISHING_INDICATORS = 0.01
WEIGHT_SUSPICIOUS_SMS = 0.05
WEIGHT_SUSPICIOUS_EMAIL = 0.01
FRAUD_SCORE_THRESHOLD = 0.25

async def save_fraud_result_async(result: dict, transaction_id: str) -> None:
    async with _save_lock:
        output_dir = Path('fraud_graph/results')
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / 'fraud.json'
        existing_data = []
        if output_file.exists():
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]
            except (json.JSONDecodeError, IOError):
                existing_data = []
        existing_ids = {item.get('transaction_id') for item in existing_data if isinstance(item, dict)}
        if transaction_id not in existing_ids:
            existing_data.append(result)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)

def aggregate_features_and_score(state: FraudState) -> FraudState:
    amount_features = state.get('amount_merchant_features', {})
    country_features = state.get('country_travel_features', {})
    sms_email_features = state.get('sms_email_features', {})
    aggregated_features = {**amount_features, **country_features, **sms_email_features}
    score = WEIGHT_ACCOUNT_DRAINED * aggregated_features.get('account_drained', 0) + WEIGHT_BALANCE_VERY_LOW * aggregated_features.get('balance_very_low', 0) + WEIGHT_ABNORMAL_AMOUNT * aggregated_features.get('abnormal_amount', 0) + WEIGHT_HIGH_AMOUNT * aggregated_features.get('high_amount', 0) + WEIGHT_LARGE_WITHDRAWAL * aggregated_features.get('large_withdrawal', 0) + WEIGHT_NEW_DEST * aggregated_features.get('new_dest', 0) + WEIGHT_NEW_MERCHANT * aggregated_features.get('new_merchant', 0) + WEIGHT_POST_WITHDRAWAL * aggregated_features.get('post_withdrawal', 0) + WEIGHT_PATTERN_MULTIPLE_WITHDRAWALS * aggregated_features.get('pattern_multiple_withdrawals', 0) + WEIGHT_SUSPICIOUS_TYPE * aggregated_features.get('suspicious_type', 0) + WEIGHT_IMPOSSIBLE_TRAVEL * aggregated_features.get('impossible_travel', 0) + WEIGHT_LOCATION_ANOMALY * aggregated_features.get('location_anomaly', 0) + WEIGHT_LOCATION_MISMATCH * aggregated_features.get('location_mismatch', 0) + WEIGHT_NEW_VENUE * aggregated_features.get('new_venue', 0) + WEIGHT_GPS_CONTRADICTION * aggregated_features.get('gps_contradiction', 0) + WEIGHT_LOCATION_MISSING * aggregated_features.get('location_missing', 0) + WEIGHT_TIME_CORRELATION * aggregated_features.get('time_correlation', 0) + WEIGHT_PHISHING_INDICATORS * aggregated_features.get('phishing_indicators', 0) + WEIGHT_SUSPICIOUS_SMS * min(aggregated_features.get('suspicious_sms_count', 0), 3) / 3.0 + WEIGHT_SUSPICIOUS_EMAIL * min(aggregated_features.get('suspicious_email_count', 0), 3) / 3.0
    critical_features = ['account_drained', 'high_amount', 'suspicious_type', 'impossible_travel', 'location_anomaly', 'time_correlation', 'pattern_multiple_withdrawals', 'new_merchant', 'post_withdrawal', 'new_venue']
    has_critical_feature = any((aggregated_features.get(feature, 0) == 1 for feature in critical_features))
    if not has_critical_feature and score < 0.3:
        score = score * 0.3
    critical_count = sum((1 for feature in critical_features if aggregated_features.get(feature, 0) == 1))
    if critical_count >= 2:
        score += 0.15
    score = min(1.0, max(0.0, score))
    return {**state, 'aggregated_features': aggregated_features, 'risk_score': round(score, 2)}

def save_result_to_json(state: FraudState) -> FraudState:
    transaction_id = state.get('current_transaction_id')
    risk_score = state.get('risk_score', 0.0)
    if not transaction_id:
        return state
    if risk_score <= FRAUD_SCORE_THRESHOLD:
        return state
    result = {'transaction_id': transaction_id, 'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), 'risk_score': risk_score, 'decision': state.get('decision', 'SUSPECT'), 'features': state.get('aggregated_features', {}), 'explanation': state.get('explanation')}
    results = state.get('results', [])
    results.append(result)
    output_dir = Path('fraud_graph/results')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'fraud.json'
    existing_data = []
    if output_file.exists():
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    existing_data = [existing_data]
        except (json.JSONDecodeError, IOError):
            existing_data = []
    existing_ids = {item.get('transaction_id') for item in existing_data if isinstance(item, dict)}
    if transaction_id not in existing_ids:
        existing_data.append(result)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)
    return {**state, 'results': results}