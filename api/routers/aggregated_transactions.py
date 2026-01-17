import logging
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Path, Query, Body
from typing import List
from api.utils.response_formatter import format_response
from api.utils.toon_formatter import format_response_as_toon

logger = logging.getLogger(__name__)

from api.models.aggregated import AggregatedTransaction, UserWithTransactions
from api.models.email import Email
from api.utils.data_loader import (
    load_transactions,
    load_users,
    load_emails,
    load_sms,
    load_locations
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/ids")
async def get_all_transaction_ids(
    format: str = Query("json", description="Response format: 'json' or 'toon'", alias="format")
):
    """Récupère tous les IDs de transactions du dataset.
    
    Returns:
        Liste de tous les transaction_id disponibles
    """
    try:
        transactions = load_transactions()
        transaction_ids = [tx.transaction_id for tx in transactions]
        
        return format_response(
            {"transaction_ids": transaction_ids, "count": len(transaction_ids)},
            response_format=format.lower()
        )
    except (FileNotFoundError, ValueError) as e:
        from api.utils.data_loader import get_dataset_folder
        raise HTTPException(
            status_code=500,
            detail=f"Error loading data from dataset '{get_dataset_folder()}': {str(e)}"
        )

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

def extract_text_from_html(html_content: str) -> str:
    """Extrait le texte brut depuis du contenu HTML."""
    import re
    
    # Supprimer les balises <script> et <style> avec leur contenu
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remplacer les balises de saut de ligne par des sauts de ligne réels
    html_content = re.sub(r'<br\s*/?>', '\n', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'</p>', '\n\n', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'</div>', '\n', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'</li>', '\n', html_content, flags=re.IGNORECASE)
    html_content = re.sub(r'</h[1-6]>', '\n\n', html_content, flags=re.IGNORECASE)
    
    # Supprimer toutes les autres balises HTML
    html_content = re.sub(r'<[^>]+>', '', html_content)
    
    # Décoder les entités HTML courantes
    html_content = html_content.replace('&nbsp;', ' ')
    html_content = html_content.replace('&amp;', '&')
    html_content = html_content.replace('&lt;', '<')
    html_content = html_content.replace('&gt;', '>')
    html_content = html_content.replace('&quot;', '"')
    html_content = html_content.replace('&#39;', "'")
    html_content = html_content.replace('&apos;', "'")
    
    # Nettoyer les espaces multiples et les sauts de ligne
    html_content = re.sub(r'[ \t]+', ' ', html_content)
    html_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', html_content)
    html_content = html_content.strip()
    
    return html_content

def extract_text_from_email(email_content: str) -> str:
    """Extrait le texte brut depuis le contenu d'un email, en supprimant le HTML."""
    # Séparer les headers du body
    parts = email_content.split('\n\n', 1)
    if len(parts) < 2:
        return email_content  # Pas de body séparé, retourner tel quel
    
    headers = parts[0]
    body = parts[1]
    
    # Vérifier si le body contient du HTML
    if '<html' in body.lower() or '<body' in body.lower():
        # Extraire le texte depuis le HTML
        text_body = extract_text_from_html(body)
        # Reconstruire l'email avec le texte brut
        return f"{headers}\n\n{text_body}"
    
    return email_content  # Pas de HTML, retourner tel quel

def extract_timestamp_from_email(email_content: str) -> Optional[datetime]:
    """Extrait le timestamp depuis le contenu d'un email (RFC 822 format)."""
    import re
    from email.utils import parsedate_to_datetime
    
    # Chercher le header Date: dans l'email
    date_patterns = [
        r'Date:\s*(.+?)(?:\n|$)',
        r'date:\s*(.+?)(?:\n|$)',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, email_content, re.IGNORECASE | re.MULTILINE)
        if match:
            date_str = match.group(1).strip()
            try:
                # Parser le format RFC 822
                parsed_date = parsedate_to_datetime(date_str)
                return parsed_date
            except (ValueError, TypeError):
                # Essayer avec fromisoformat si c'est un format ISO
                try:
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except:
                    continue
    return None

def extract_timestamp_from_sms(sms_content: str) -> Optional[datetime]:
    """Extrait le timestamp depuis le contenu d'un SMS."""
    import re
    from datetime import timezone
    
    # Chercher le pattern "Date: YYYY-MM-DD HH:MM:SS"
    date_pattern = r'Date:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})'
    match = re.search(date_pattern, sms_content, re.IGNORECASE | re.MULTILINE)
    
    if match:
        date_str = match.group(1).strip()
        try:
            # Parser le format "YYYY-MM-DD HH:MM:SS" et ajouter UTC timezone
            naive_dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            # Convertir en datetime aware avec UTC timezone
            return naive_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    
    return None

def filter_emails_by_timestamp(
    emails: list,
    transaction_timestamp: str,
    time_window_hours: int = 3
) -> list:
    """Filtre les emails pour ne garder que ceux dans les N heures avant la transaction."""
    if not transaction_timestamp or not transaction_timestamp.strip():
        return emails
    
    try:
        from datetime import timezone
        
        # Normaliser le timestamp de la transaction
        tx_timestamp = transaction_timestamp.replace('Z', '+00:00')
        if '+' not in tx_timestamp and '-' not in tx_timestamp[-6:]:
            if 'T' in tx_timestamp:
                tx_timestamp = tx_timestamp + '+00:00'
        
        ref_time = datetime.fromisoformat(tx_timestamp)
        # S'assurer que ref_time est aware (avec timezone)
        if ref_time.tzinfo is None:
            ref_time = ref_time.replace(tzinfo=timezone.utc)
        
        time_window = timedelta(hours=time_window_hours)
        
        filtered_emails = []
        for email in emails:
            email_timestamp = extract_timestamp_from_email(email.mail)
            if email_timestamp:
                # S'assurer que email_timestamp est aware (avec timezone)
                if email_timestamp.tzinfo is None:
                    email_timestamp = email_timestamp.replace(tzinfo=timezone.utc)
                
                # Ne garder que les emails dans les N heures AVANT la transaction
                # (entre l'heure de la transaction et 3h avant)
                time_diff = ref_time - email_timestamp
                if timedelta(0) <= time_diff <= time_window:
                    filtered_emails.append(email)
            else:
                # Si on ne peut pas extraire le timestamp, inclure quand même l'email
                logger.debug(f"Could not extract timestamp from email, including anyway")
                filtered_emails.append(email)
        
        logger.debug(f"Filtered {len(filtered_emails)}/{len(emails)} emails within {time_window_hours}h before transaction")
        return filtered_emails
    except (ValueError, AttributeError) as e:
        logger.error(f"Error filtering emails by timestamp: {e}")
        return emails  # Retourner tous les emails en cas d'erreur

def filter_sms_by_timestamp(
    sms_list: list,
    transaction_timestamp: str,
    time_window_hours: int = 3
) -> list:
    """Filtre les SMS pour ne garder que ceux dans les N heures avant la transaction."""
    if not transaction_timestamp or not transaction_timestamp.strip():
        return sms_list
    
    try:
        from datetime import timezone
        
        # Normaliser le timestamp de la transaction
        tx_timestamp = transaction_timestamp.replace('Z', '+00:00')
        if '+' not in tx_timestamp and '-' not in tx_timestamp[-6:]:
            if 'T' in tx_timestamp:
                tx_timestamp = tx_timestamp + '+00:00'
        
        ref_time = datetime.fromisoformat(tx_timestamp)
        # S'assurer que ref_time est aware (avec timezone)
        if ref_time.tzinfo is None:
            ref_time = ref_time.replace(tzinfo=timezone.utc)
        
        time_window = timedelta(hours=time_window_hours)
        
        filtered_sms = []
        for sms in sms_list:
            sms_timestamp = extract_timestamp_from_sms(sms.sms)
            if sms_timestamp:
                # S'assurer que sms_timestamp est aware (avec timezone)
                if sms_timestamp.tzinfo is None:
                    sms_timestamp = sms_timestamp.replace(tzinfo=timezone.utc)
                
                # Ne garder que les SMS dans les N heures AVANT la transaction
                # (entre l'heure de la transaction et 3h avant)
                time_diff = ref_time - sms_timestamp
                if timedelta(0) <= time_diff <= time_window:
                    filtered_sms.append(sms)
            else:
                # Si on ne peut pas extraire le timestamp, inclure quand même le SMS
                logger.debug(f"Could not extract timestamp from SMS, including anyway")
                filtered_sms.append(sms)
        
        logger.debug(f"Filtered {len(filtered_sms)}/{len(sms_list)} SMS within {time_window_hours}h before transaction")
        return filtered_sms
    except (ValueError, AttributeError) as e:
        logger.error(f"Error filtering SMS by timestamp: {e}")
        return sms_list  # Retourner tous les SMS en cas d'erreur

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

        # Filtrer par timestamp (3 heures avant la transaction)
        if transaction.timestamp:
            sender_emails = filter_emails_by_timestamp(sender_emails, transaction.timestamp, time_window_hours=3)
            sender_sms = filter_sms_by_timestamp(sender_sms, transaction.timestamp, time_window_hours=3)
        
        # Extraire le texte depuis le HTML pour les emails
        sender_emails = [
            Email(mail=extract_text_from_email(email.mail))
            for email in sender_emails
        ]

        logger.debug(f"Found {len(sender_emails)} emails and {len(sender_sms)} SMS for sender (within 3h before transaction)")
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

        # Filtrer par timestamp (3 heures avant la transaction)
        if transaction.timestamp:
            recipient_emails = filter_emails_by_timestamp(recipient_emails, transaction.timestamp, time_window_hours=3)
            recipient_sms = filter_sms_by_timestamp(recipient_sms, transaction.timestamp, time_window_hours=3)
        
        # Extraire le texte depuis le HTML pour les emails
        recipient_emails = [
            type(email)(mail=extract_text_from_email(email.mail))
            for email in recipient_emails
        ]

        logger.debug(f"Found {len(recipient_emails)} emails and {len(recipient_sms)} SMS for recipient (within 3h before transaction)")

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

@router.post("/batch")
async def get_batch_aggregated_transactions(
    transaction_ids: List[str] = Body(..., description="List of transaction UUIDs"),
    format: str = Query("toon", description="Response format: 'json' or 'toon'", alias="format")
):
    try:
        transactions_list = load_transactions()
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
    
    if not transaction_ids or len(transaction_ids) == 0:
        raise HTTPException(status_code=400, detail="transaction_ids list cannot be empty")
    
    if len(transaction_ids) > 200:
        raise HTTPException(status_code=400, detail="Maximum 200 transaction IDs allowed per batch")
    
    users_by_iban = {user.iban: user for user in users}
    users_by_biotag = {user.biotag: user for user in users if user.biotag}
    
    batch_results = []
    
    for transaction_id in transaction_ids:
        if not transaction_id or len(transaction_id) != 36:
            batch_results.append({
                "transaction_id": transaction_id,
                "error": "Invalid transaction_id format"
            })
            continue
        
        transaction = next(
            (t for t in transactions_list if t.transaction_id == transaction_id),
            None
        )
        
        if not transaction:
            batch_results.append({
                "transaction_id": transaction_id,
                "error": "Transaction not found"
            })
            continue
        
        sender = None
        if transaction.sender_id and transaction.sender_id.strip():
            sender = users_by_biotag.get(transaction.sender_id)
        
        if not sender and transaction.sender_iban and transaction.sender_iban.strip():
            sender = users_by_iban.get(transaction.sender_iban)
        
        recipient = None
        if transaction.recipient_id and transaction.recipient_id.strip():
            recipient = users_by_biotag.get(transaction.recipient_id)
        
        if not recipient and transaction.recipient_iban and transaction.recipient_iban.strip():
            recipient = users_by_iban.get(transaction.recipient_iban)
        
        sender_emails = []
        if sender and sender.biotag:
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
                if (from_id and sender.biotag.lower() in from_id.lower()) or \
                   (to_id and sender.biotag.lower() in to_id.lower()):
                    sender_emails.append(email)
        
        recipient_emails = []
        if recipient and recipient.biotag:
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
                if (from_id and recipient.biotag.lower() in from_id.lower()) or \
                   (to_id and recipient.biotag.lower() in to_id.lower()):
                    recipient_emails.append(email)
        
        sender_sms = []
        if sender and sender.biotag:
            sender_sms = [s for s in sms_list if sender.biotag.lower() in s.id_user.lower()]
        
        recipient_sms = []
        if recipient and recipient.biotag:
            recipient_sms = [s for s in sms_list if recipient.biotag.lower() in s.id_user.lower()]
        
        # Filtrer par timestamp (3 heures avant la transaction)
        if transaction.timestamp:
            sender_emails = filter_emails_by_timestamp(sender_emails, transaction.timestamp, time_window_hours=3)
            sender_sms = filter_sms_by_timestamp(sender_sms, transaction.timestamp, time_window_hours=3)
            recipient_emails = filter_emails_by_timestamp(recipient_emails, transaction.timestamp, time_window_hours=3)
            recipient_sms = filter_sms_by_timestamp(recipient_sms, transaction.timestamp, time_window_hours=3)
        
        # Extraire le texte depuis le HTML pour les emails
        sender_emails = [
            Email(mail=extract_text_from_email(email.mail))
            for email in sender_emails
        ]
        recipient_emails = [
            type(email)(mail=extract_text_from_email(email.mail))
            for email in recipient_emails
        ]
        
        sender_locations = []
        if sender and sender.biotag and transaction.timestamp:
            sender_locations = find_locations_near_timestamp(locations, sender.biotag, transaction.timestamp, 24)
        
        recipient_locations = []
        if recipient and recipient.biotag and transaction.timestamp:
            recipient_locations = find_locations_near_timestamp(locations, recipient.biotag, transaction.timestamp, 24)
        
        sender_other_transactions = []
        if sender and sender.iban and transaction.timestamp:
            try:
                transaction_timestamp = transaction.timestamp.replace('Z', '+00:00')
                if '+' not in transaction_timestamp and '-' not in transaction_timestamp[-6:]:
                    if 'T' in transaction_timestamp:
                        transaction_timestamp = transaction_timestamp + '+00:00'
                ref_time = datetime.fromisoformat(transaction_timestamp)
                time_window = timedelta(hours=3)
                
                for tx in transactions_list:
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
                        except (ValueError, AttributeError):
                            continue
            except (ValueError, AttributeError):
                pass
        
        recipient_other_transactions = []
        if recipient and recipient.iban and transaction.timestamp:
            try:
                transaction_timestamp = transaction.timestamp.replace('Z', '+00:00')
                if '+' not in transaction_timestamp and '-' not in transaction_timestamp[-6:]:
                    if 'T' in transaction_timestamp:
                        transaction_timestamp = transaction_timestamp + '+00:00'
                ref_time = datetime.fromisoformat(transaction_timestamp)
                time_window = timedelta(hours=3)
                
                for tx in transactions_list:
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
                        except (ValueError, AttributeError):
                            continue
            except (ValueError, AttributeError):
                pass
        
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
        
        batch_results.append(aggregated.model_dump())
    
    return format_response(batch_results, response_format=format.lower())