import math
from email.utils import parsedate_to_datetime
from typing import List
from ..state import FraudState
PHISHING_KEYWORDS: List[str] = ['bank', 'account', 'verify', 'locked', 'security', 'suspended', 'subscription', 'renewal', 'payment', 'update', 'card', 'delivery', 'customs', 'parcel', 'fee', 'dhl', 'fedex', 'ups', 'courier', 'identity', 'id', 'verification', 'otp', 'invoice', 'urgent', 'overdue', 'accounting', 'billing', 'supplier', 'click here', 'verify account', 'account locked', 'confirm', 'fraud', 'paypal', 'urgente', 'verifica', 'conferma']

def analyze_amount_merchant(state: FraudState) -> FraudState:
    transaction = state.get('transaction', {})
    user_profile = state.get('user_profile', {})
    if not transaction:
        return {'amount_merchant_features': {}}
    tx_amount = transaction.get('amount', 0)
    tx_type = transaction.get('transaction_type', '')
    balance_after = transaction.get('balance_after', 0)
    sender_salary = user_profile.get('salary', 0)
    description = transaction.get('description', '').lower()
    recipient_iban = transaction.get('recipient_iban', '')
    recipient_id = transaction.get('recipient_id', '')
    other_transactions = user_profile.get('other_transactions', [])
    new_dest = 0
    if recipient_iban or recipient_id:
        seen_recipients = set()
        for other_tx in other_transactions:
            other_iban = other_tx.get('recipient_iban', '')
            other_id = other_tx.get('recipient_id', '')
            if other_iban:
                seen_recipients.add(other_iban)
            if other_id:
                seen_recipients.add(other_id)
        current_recipient = recipient_iban or recipient_id
        if current_recipient and current_recipient not in seen_recipients:
            new_dest = 1
    new_merchant = 0
    if tx_type in ['e-commerce', 'pagamento e-comm']:
        merchant_identifier = None
        if description:
            merchant_identifier = description.split()[0].lower() if description.split() else None
        elif recipient_id:
            merchant_identifier = recipient_id.lower()
        elif transaction.get('location', ''):
            merchant_identifier = transaction.get('location', '').lower()
        if merchant_identifier:
            seen_merchants = set()
            for other_tx in other_transactions:
                if other_tx.get('transaction_type', '') in ['e-commerce', 'pagamento e-comm']:
                    other_desc = other_tx.get('description', '').lower()
                    other_recipient = other_tx.get('recipient_id', '').lower()
                    other_location = other_tx.get('location', '').lower()
                    other_merchant = None
                    if other_desc:
                        other_merchant = other_desc.split()[0] if other_desc.split() else None
                    elif other_recipient:
                        other_merchant = other_recipient
                    elif other_location:
                        other_merchant = other_location
                    if other_merchant:
                        seen_merchants.add(other_merchant)
            if merchant_identifier not in seen_merchants:
                new_merchant = 1
    post_withdrawal = 0
    if tx_type in ['pagamento fisico', 'e-commerce', 'in-person payment']:
        recent_withdrawals = [tx for tx in other_transactions if tx.get('transaction_type') in ['prelievo', 'withdrawal'] and tx.get('amount', 0) > 200]
        if recent_withdrawals:
            post_withdrawal = 1
    pattern_multiple_withdrawals = 0
    if tx_type in ['prelievo', 'withdrawal']:
        recent_withdrawals = [tx for tx in other_transactions if tx.get('transaction_type') in ['prelievo', 'withdrawal']]
        if len(recent_withdrawals) >= 1:
            pattern_multiple_withdrawals = 1
    features = {'account_drained': 1 if balance_after == 0.0 else 0, 'balance_very_low': 1 if 0 < balance_after < 10 else 0, 'abnormal_amount': 1 if sender_salary > 0 and tx_amount > sender_salary * 0.1 else 0, 'high_amount': 1 if tx_amount > 500 else 0, 'large_withdrawal': 1 if tx_type == 'prelievo' and tx_amount > 300 else 0, 'suspicious_type': 1 if tx_type in ['bonifico', 'transfer'] else 0, 'balance_ratio': balance_after / max(sender_salary / 12, 1) if sender_salary > 0 else 1.0, 'unknown_merchant': 1 if not description or len(description) < 3 else 0, 'suspicious_keywords': 1 if any((kw in description for kw in ['urgent', 'verify', 'suspended', 'invoice', 'security'])) else 0, 'new_dest': new_dest, 'new_merchant': new_merchant, 'post_withdrawal': post_withdrawal, 'pattern_multiple_withdrawals': pattern_multiple_withdrawals}
    return {'amount_merchant_features': features}

def analyze_country_travel(state: FraudState) -> FraudState:
    transaction = state.get('transaction', {})
    user_profile = state.get('user_profile', {})
    location_data = state.get('location_data', [])
    if not transaction:
        return {'country_travel_features': {}}
    tx_location = transaction.get('location', '')
    tx_type = transaction.get('transaction_type', '')
    user_residence = user_profile.get('residence', {})
    user_city = user_residence.get('city', '')
    tx_lat = transaction.get('lat')
    tx_lng = transaction.get('lng')
    other_transactions = user_profile.get('other_transactions', [])
    new_venue = 0
    if tx_type in ['pagamento fisico', 'in-person payment'] and tx_location:
        seen_venues = set()
        for other_tx in other_transactions:
            if other_tx.get('transaction_type') in ['pagamento fisico', 'in-person payment']:
                other_location = other_tx.get('location', '')
                if other_location:
                    seen_venues.add(other_location.lower())
        if tx_location.lower() not in seen_venues:
            new_venue = 1
    features = {'location_missing': 1 if not tx_location else 0, 'location_mismatch': 1 if tx_location and user_city and (tx_location.lower() != user_city.lower()) else 0, 'gps_available': 1 if tx_lat and tx_lng else 0, 'gps_contradiction': 0, 'new_venue': new_venue}
    user_lat = user_residence.get('lat')
    user_lng = user_residence.get('lng')
    if user_lat and user_lng and tx_lat and tx_lng:
        lat_diff = abs(float(user_lat) - float(tx_lat))
        lng_diff = abs(float(user_lng) - float(tx_lng))
        distance_km = math.sqrt(lat_diff ** 2 + lng_diff ** 2) * 111
        features['distance_from_residence'] = distance_km
        features['impossible_travel'] = 1 if distance_km > 1000 else 0
        features['location_anomaly'] = 1 if distance_km > 100 else 0
    elif tx_location and user_city:
        tx_city = tx_location.split(' - ')[0].strip().lower() if ' - ' in tx_location else tx_location.lower()
        user_city_lower = user_city.lower()
        if tx_city != user_city_lower:
            features['location_anomaly'] = 1
            major_cities_north = ['modena', 'milano', 'torino', 'genova', 'venezia', 'bologna']
            major_cities_south = ['palermo', 'catania', 'napoli', 'bari']
            tx_is_north = any((city in tx_city for city in major_cities_north))
            tx_is_south = any((city in tx_city for city in major_cities_south))
            user_is_north = any((city in user_city_lower for city in major_cities_north))
            user_is_south = any((city in user_city_lower for city in major_cities_south))
            if tx_is_north and user_is_south or (tx_is_south and user_is_north):
                features['impossible_travel'] = 1
            else:
                features['impossible_travel'] = 0
    return {'country_travel_features': features}

def analyze_sms_email(state: FraudState) -> FraudState:
    from datetime import datetime, timedelta
    sms_data = state.get('sms_data', [])
    email_data = state.get('email_data', [])
    transaction = state.get('transaction', {})
    tx_timestamp = transaction.get('timestamp', '')
    suspicious_sms_count = 0
    suspicious_email_count = 0
    time_correlation = 0
    phishing_sms_times = []
    for sms in sms_data:
        sms_content = sms.get('sms', '').lower()
        if any((kw in sms_content for kw in PHISHING_KEYWORDS)):
            suspicious_sms_count += 1
            sms_time = sms.get('datetime') or sms.get('timestamp')
            if sms_time:
                phishing_sms_times.append(sms_time)
    phishing_email_times = []
    for email in email_data:
        email_content = email.get('mail', '').lower()
        is_phishing = any((kw in email_content for kw in PHISHING_KEYWORDS))
        if not is_phishing:
            if 'customs' in email_content and 'fee' in email_content:
                is_phishing = True
            elif 'identity' in email_content and 'verification' in email_content:
                is_phishing = True
            elif 'parcel' in email_content and ('fee' in email_content or 'customs' in email_content):
                is_phishing = True
            elif 'unpaid' in email_content and ('customs' in email_content or 'fee' in email_content):
                is_phishing = True
        if is_phishing:
            suspicious_email_count += 1
            email_time = email.get('date') or email.get('timestamp')
            if not email_time and 'date:' in email_content:
                try:
                    date_line = [line for line in email_content.split('\n') if 'date:' in line.lower()]
                    if date_line:
                        date_str = date_line[0].split('date:')[-1].strip()
                        parsed_dt = parsedate_to_datetime(date_str)
                        if parsed_dt.tzinfo is None:
                            from datetime import timezone
                            parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                        else:
                            parsed_dt = parsed_dt.astimezone(timezone.utc)
                        email_time = parsed_dt.isoformat()
                except Exception:
                    pass
            if email_time:
                phishing_email_times.append(email_time)
    if tx_timestamp and (phishing_sms_times or phishing_email_times):
        try:
            from datetime import timezone
            tx_timestamp_clean = tx_timestamp.replace('Z', '+00:00') if tx_timestamp.endswith('Z') else tx_timestamp
            tx_time = datetime.fromisoformat(tx_timestamp_clean)
            if tx_time.tzinfo is None:
                tx_time = tx_time.replace(tzinfo=timezone.utc)
            else:
                tx_time = tx_time.astimezone(timezone.utc)
            all_phishing_times = phishing_sms_times + phishing_email_times
            for phishing_time_str in all_phishing_times:
                try:
                    if isinstance(phishing_time_str, str):
                        phishing_time_clean = phishing_time_str.replace('Z', '+00:00') if phishing_time_str.endswith('Z') else phishing_time_str
                        phishing_time = datetime.fromisoformat(phishing_time_clean)
                        if phishing_time.tzinfo is None:
                            phishing_time = phishing_time.replace(tzinfo=timezone.utc)
                        else:
                            phishing_time = phishing_time.astimezone(timezone.utc)
                    else:
                        continue
                    time_diff = tx_time - phishing_time
                    if timedelta(minutes=0) <= time_diff <= timedelta(hours=4):
                        time_correlation = 1
                        break
                except (ValueError, AttributeError, TypeError) as e:
                    continue
        except (ValueError, AttributeError, TypeError):
            pass
    features = {'has_sms': 1 if sms_data else 0, 'has_email': 1 if email_data else 0, 'suspicious_sms_count': suspicious_sms_count, 'suspicious_email_count': suspicious_email_count, 'phishing_indicators': 1 if suspicious_sms_count > 0 or suspicious_email_count > 0 else 0, 'total_communications': len(sms_data) + len(email_data), 'time_correlation': time_correlation}
    return {'sms_email_features': features}