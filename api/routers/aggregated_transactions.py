import logging
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Path, Query
from api.utils.response_formatter import format_response
from api.utils.toon_formatter import format_response_as_toon

logger = logging.getLogger(__name__)

from api.models.aggregated import AggregatedTransaction, UserWithTransactions
from api.utils.data_loader import (
    load_transactions,
    load_users,
    load_emails,
    load_sms,
    load_locations
)

router = APIRouter(prefix="/transactions", tags=["transactions"])

def _extract_user_id_from_line(line: str) -> Optional[str]:

    if 'From:' not in line and 'To:' not in line:
        return None

    parts = line.split(':', 1)
    if len(parts) > 1:
        user_part = parts[1].strip()

        if '"' in user_part:

            import re
            quoted_match = re.search(r'"([^"]+)"', user_part)
            if quoted_match:
                name = quoted_match.group(1)

                return name.replace(' ', '_')

        if '@' in user_part:

            email_part = user_part.split('@')[0].strip()

            email_part = email_part.replace('<', '').replace('>', '').strip()

            return email_part.replace('.', '_')

        return user_part.replace(' ', '_')
    return None

def parse_user_id_from_email_or_sms(content: str) -> Optional[str]:

    if '\n' not in content:
        return _extract_user_id_from_line(content)

    lines = content.split('\n')
    for line in lines:
        result = _extract_user_id_from_line(line)
        if result:
            return result
    return None

def find_locations_near_timestamp(
    locations: list,
    biotag: str,
    timestamp: str,
    time_window_hours: int = 24
) -> list:

    if not timestamp or not timestamp.strip():
        logger.warning(f"Empty timestamp provided for biotag {biotag}")
        return []

    try:

        timestamp_normalized = timestamp.replace('Z', '+00:00')

        if '+' not in timestamp_normalized and '-' not in timestamp_normalized[-6:]:

            if 'T' in timestamp_normalized:
                timestamp_normalized = timestamp_normalized + '+00:00'

        ref_time = datetime.fromisoformat(timestamp_normalized)
        time_delta = timedelta(hours=time_window_hours)

        matching_locations = []
        for loc in locations:
            if loc.biotag == biotag:
                try:

                    loc_timestamp = loc.datetime.replace('Z', '+00:00')
                    if '+' not in loc_timestamp and '-' not in loc_timestamp[-6:]:
                        if 'T' in loc_timestamp:
                            loc_timestamp = loc_timestamp + '+00:00'

                    loc_time = datetime.fromisoformat(loc_timestamp)
                    time_diff = abs(loc_time - ref_time)
                    if time_diff <= time_delta:
                        matching_locations.append(loc)
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Error parsing location timestamp {loc.datetime}: {e}")
                    continue

        logger.debug(f"Found {len(matching_locations)} locations for biotag {biotag} near {timestamp}")
        return matching_locations
    except (ValueError, AttributeError) as e:
        logger.error(f"Error parsing reference timestamp {timestamp}: {e}")
        return []

@router.get("/{transaction_id}")
async def get_aggregated_transaction(
    transaction_id: str = Path(
        ...,
        description="UUID de la transaction",
        min_length=36,
        max_length=36
    ),
    format: str = Query("json", description="Response format: 'json' or 'toon'", alias="format")
):

    try:
        transactions = load_transactions()
        users = load_users()
        emails = load_emails()
        sms_list = load_sms()
        locations = load_locations()
    except (FileNotFoundError, ValueError) as e:
        from api.utils.data_loader import get_dataset_folder
        raise HTTPException(
            status_code=500,
            detail=f"Error loading data from dataset '{get_dataset_folder()}': {str(e)}"
        )

    transaction = next(
        (t for t in transactions if t.transaction_id == transaction_id),
        None
    )

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction {transaction_id} non trouvée"
        )

    users_by_iban = {user.iban: user for user in users}

    users_by_biotag = {user.biotag: user for user in users if user.biotag}

    logger.debug(f"Created users_by_iban mapping with {len(users_by_iban)} entries")
    logger.debug(f"Created users_by_biotag mapping with {len(users_by_biotag)} entries")

    sender = None
    if transaction.sender_id and transaction.sender_id.strip():
        sender = users_by_biotag.get(transaction.sender_id)
        if sender:
            logger.debug(f"Found sender by biotag (sender_id): {transaction.sender_id}")

    if not sender and transaction.sender_iban and transaction.sender_iban.strip():
        sender = users_by_iban.get(transaction.sender_iban)
        if sender:
            logger.debug(f"Found sender by IBAN: {transaction.sender_iban}")

    if not sender and transaction.sender_id:
        logger.warning(f"Could not find sender for sender_id/biotag: {transaction.sender_id}")

    recipient = None
    if transaction.recipient_id and transaction.recipient_id.strip():
        recipient = users_by_biotag.get(transaction.recipient_id)
        if recipient:
            logger.debug(f"Found recipient by biotag (recipient_id): {transaction.recipient_id}")

    if not recipient and transaction.recipient_iban and transaction.recipient_iban.strip():
        recipient = users_by_iban.get(transaction.recipient_iban)
        if recipient:
            logger.debug(f"Found recipient by IBAN: {transaction.recipient_iban}")

    if not recipient and transaction.recipient_id:
        logger.debug(f"Could not find recipient for recipient_id/biotag: {transaction.recipient_id}")

    def get_user_id(user: Optional[object]) -> Optional[str]:
        if user:
            return f"{user.first_name}_{user.last_name}"
        return None

    sender_user_id = None
    if sender:
        sender_user_id = get_user_id(sender)

    recipient_user_id = None
    if recipient:
        recipient_user_id = get_user_id(recipient)

    logger.debug(f"Sender user_id for filtering: {sender_user_id}, sender found: {sender is not None}")
    logger.debug(f"Recipient user_id for filtering: {recipient_user_id}, recipient found: {recipient is not None}")

    sender_emails = []
    sender_sms = []
    if sender_user_id:

        for email in emails:
            email_content = email.mail

            from_id = None
            to_id = None

            lines = email_content.split('\n')
            for line in lines:
                if 'From:' in line:
                    from_id = _extract_user_id_from_line(line)
                elif 'To:' in line:
                    to_id = _extract_user_id_from_line(line)

            if (from_id and sender_user_id.lower() in from_id.lower()) or \
               (to_id and sender_user_id.lower() in to_id.lower()):
                sender_emails.append(email)

        for sms in sms_list:
            if sender_user_id.lower() in sms.id_user.lower():
                sender_sms.append(sms)

        logger.debug(f"Found {len(sender_emails)} emails and {len(sender_sms)} SMS for sender")
    else:
        logger.warning(f"No sender_user_id found, cannot filter SMS/emails. sender_id: {transaction.sender_id}")

    recipient_emails = []
    recipient_sms = []
    if recipient_user_id:

        for email in emails:
            email_content = email.mail

            from_id = None
            to_id = None

            lines = email_content.split('\n')
            for line in lines:
                if 'From:' in line:
                    from_id = _extract_user_id_from_line(line)
                elif 'To:' in line:
                    to_id = _extract_user_id_from_line(line)

            if (from_id and recipient_user_id.lower() in from_id.lower()) or \
               (to_id and recipient_user_id.lower() in to_id.lower()):
                recipient_emails.append(email)

        for sms in sms_list:
            if recipient_user_id.lower() in sms.id_user.lower():
                recipient_sms.append(sms)

        logger.debug(f"Found {len(recipient_emails)} emails and {len(recipient_sms)} SMS for recipient")

    sender_locations = []
    recipient_locations = []

    if transaction.sender_id and transaction.sender_id.strip():
        sender_locations = find_locations_near_timestamp(
            locations,
            transaction.sender_id,
            transaction.timestamp,
            time_window_hours=24
        )
        logger.debug(f"Found {len(sender_locations)} locations for sender_id: {transaction.sender_id}")

    if transaction.recipient_id and transaction.recipient_id.strip():
        recipient_locations = find_locations_near_timestamp(
            locations,
            transaction.recipient_id,
            transaction.timestamp,
            time_window_hours=24
        )
        logger.debug(f"Found {len(recipient_locations)} locations for recipient_id: {transaction.recipient_id}")

    sender_other_transactions = []
    if sender and sender.iban and transaction.timestamp:
        try:

            transaction_timestamp = transaction.timestamp.replace('Z', '+00:00')
            if '+' not in transaction_timestamp and '-' not in transaction_timestamp[-6:]:
                if 'T' in transaction_timestamp:
                    transaction_timestamp = transaction_timestamp + '+00:00'

            ref_time = datetime.fromisoformat(transaction_timestamp)
            time_window = timedelta(hours=3)

            for tx in transactions:
                if (tx.transaction_id != transaction_id
                    and (tx.sender_iban == sender.iban or tx.recipient_iban == sender.iban)
                    and tx.timestamp):
                    try:

                        tx_timestamp = tx.timestamp.replace('Z', '+00:00')
                        if '+' not in tx_timestamp and '-' not in tx_timestamp[-6:]:
                            if 'T' in tx_timestamp:
                                tx_timestamp = tx_timestamp + '+00:00'

                        tx_time = datetime.fromisoformat(tx_timestamp)
                        time_diff = abs(tx_time - ref_time)

                        if time_diff <= time_window:
                            sender_other_transactions.append(tx)
                    except (ValueError, AttributeError) as e:
                        logger.debug(f"Error parsing transaction timestamp {tx.timestamp}: {e}")
                        continue
        except (ValueError, AttributeError) as e:
            logger.error(f"Error parsing reference transaction timestamp {transaction.timestamp}: {e}")

        logger.debug(f"Found {len(sender_other_transactions)} other transactions for sender IBAN: {sender.iban} within ±3 hours")

    recipient_other_transactions = []
    if recipient and recipient.iban and transaction.timestamp:
        try:

            transaction_timestamp = transaction.timestamp.replace('Z', '+00:00')
            if '+' not in transaction_timestamp and '-' not in transaction_timestamp[-6:]:
                if 'T' in transaction_timestamp:
                    transaction_timestamp = transaction_timestamp + '+00:00'

            ref_time = datetime.fromisoformat(transaction_timestamp)
            time_window = timedelta(hours=3)

            for tx in transactions:
                if (tx.transaction_id != transaction_id
                    and (tx.sender_iban == recipient.iban or tx.recipient_iban == recipient.iban)
                    and tx.timestamp):
                    try:

                        tx_timestamp = tx.timestamp.replace('Z', '+00:00')
                        if '+' not in tx_timestamp and '-' not in tx_timestamp[-6:]:
                            if 'T' in tx_timestamp:
                                tx_timestamp = tx_timestamp + '+00:00'

                        tx_time = datetime.fromisoformat(tx_timestamp)
                        time_diff = abs(tx_time - ref_time)

                        if time_diff <= time_window:
                            recipient_other_transactions.append(tx)
                    except (ValueError, AttributeError) as e:
                        logger.debug(f"Error parsing transaction timestamp {tx.timestamp}: {e}")
                        continue
        except (ValueError, AttributeError) as e:
            logger.error(f"Error parsing reference transaction timestamp {transaction.timestamp}: {e}")

        logger.debug(f"Found {len(recipient_other_transactions)} other transactions for recipient IBAN: {recipient.iban} within ±3 hours")

    sender_with_transactions = None
    if sender:
        sender_with_transactions = UserWithTransactions(
            **sender.model_dump(),
            other_transactions=sender_other_transactions
        )

    recipient_with_transactions = None
    if recipient:
        recipient_with_transactions = UserWithTransactions(
            **recipient.model_dump(),
            other_transactions=recipient_other_transactions
        )

    aggregated = AggregatedTransaction(
        transaction=transaction,
        sender=sender_with_transactions,
        recipient=recipient_with_transactions,
        sender_emails=sender_emails,
        recipient_emails=recipient_emails,
        sender_sms=sender_sms,
        recipient_sms=recipient_sms,
        sender_locations=sender_locations,
        recipient_locations=recipient_locations
    )

    aggregated_dict = aggregated.model_dump()

    return format_response(aggregated_dict, response_format=format.lower())