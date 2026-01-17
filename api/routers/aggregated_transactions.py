"""
Router pour l'endpoint de transaction agrégée.
"""

import logging
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Path

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
    """
    Extrait l'ID utilisateur depuis une ligne From: ou To:.
    
    Les emails peuvent avoir le format:
    - "Caterina Chindamo" <caterina.chindamo@example.com>
    - caterina.chindamo@example.com
    
    Args:
        line: Ligne contenant From: ou To:
        
    Returns:
        L'ID utilisateur si trouvé (format: Prénom_Nom), None sinon
    """
    if 'From:' not in line and 'To:' not in line:
        return None
    
    # Extraire le nom/ID de l'utilisateur
    parts = line.split(':', 1)  # Split seulement sur le premier ':'
    if len(parts) > 1:
        user_part = parts[1].strip()
        
        # Si le nom est entre guillemets, l'extraire
        # Format: "Caterina Chindamo" <email@example.com>
        if '"' in user_part:
            # Extraire le texte entre guillemets
            import re
            quoted_match = re.search(r'"([^"]+)"', user_part)
            if quoted_match:
                name = quoted_match.group(1)
                # Convertir les espaces en underscores pour correspondre au format user_id
                return name.replace(' ', '_')
        
        # Sinon, extraire la partie email avant le @
        if '@' in user_part:
            # Format: email@example.com ou <email@example.com>
            email_part = user_part.split('@')[0].strip()
            # Retirer les chevrons si présents
            email_part = email_part.replace('<', '').replace('>', '').strip()
            # Si c'est un email comme "caterina.chindamo", convertir en "caterina_chindamo"
            return email_part.replace('.', '_')
        
        # Si pas d'email, retourner tel quel
        return user_part.replace(' ', '_')
    return None


def parse_user_id_from_email_or_sms(content: str) -> Optional[str]:
    """
    Extrait l'ID utilisateur depuis le contenu d'un email ou SMS.
    
    Args:
        content: Contenu de l'email ou SMS (peut être une ligne ou plusieurs lignes)
        
    Returns:
        L'ID utilisateur si trouvé (format: Prénom_Nom), None sinon
    """
    # Si c'est une seule ligne, l'utiliser directement
    if '\n' not in content:
        return _extract_user_id_from_line(content)
    
    # Sinon, parcourir les lignes
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
    """
    Trouve les locations proches d'un timestamp donné.
    
    Args:
        locations: Liste de toutes les locations
        biotag: Biotag de l'utilisateur
        timestamp: Timestamp de référence (ISO 8601)
        time_window_hours: Fenêtre temporelle en heures
        
    Returns:
        Liste des locations correspondantes
    """
    if not timestamp or not timestamp.strip():
        logger.warning(f"Empty timestamp provided for biotag {biotag}")
        return []
    
    try:
        # Normaliser le timestamp (gérer différents formats)
        timestamp_normalized = timestamp.replace('Z', '+00:00')
        # Si pas de timezone, ajouter +00:00
        if '+' not in timestamp_normalized and '-' not in timestamp_normalized[-6:]:
            # Format simple sans timezone, on assume UTC
            if 'T' in timestamp_normalized:
                timestamp_normalized = timestamp_normalized + '+00:00'
        
        ref_time = datetime.fromisoformat(timestamp_normalized)
        time_delta = timedelta(hours=time_window_hours)
        
        matching_locations = []
        for loc in locations:
            if loc.biotag == biotag:
                try:
                    # Normaliser le timestamp de la location aussi
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


@router.get("/{transaction_id}", response_model=AggregatedTransaction)
async def get_aggregated_transaction(
    transaction_id: str = Path(
        ...,
        description="UUID de la transaction",
        min_length=36,
        max_length=36
    )
) -> AggregatedTransaction:
    """
    Récupère une transaction avec toutes les données agrégées.
    
    Cet endpoint retourne un JSON complet contenant :
    - Les données de la transaction
    - Les informations complètes de l'expéditeur et du destinataire
    - Les emails et SMS associés aux deux parties
    - Les données de localisation proches de la date de transaction
    
    Args:
        transaction_id: L'UUID de la transaction à récupérer
        
    Returns:
        Transaction avec toutes les données agrégées
        
    Raises:
        HTTPException: 404 si la transaction n'existe pas
    """
    # Charger toutes les données
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
    
    # Trouver la transaction
    transaction = next(
        (t for t in transactions if t.transaction_id == transaction_id),
        None
    )
    
    if not transaction:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction {transaction_id} non trouvée"
        )
    
    # Créer des dictionnaires pour recherche rapide
    users_by_iban = {user.iban: user for user in users}
    # Créer un mapping biotag -> User (plus direct et fiable)
    users_by_biotag = {user.biotag: user for user in users if user.biotag}
    
    logger.debug(f"Created users_by_iban mapping with {len(users_by_iban)} entries")
    logger.debug(f"Created users_by_biotag mapping with {len(users_by_biotag)} entries")
    
    # Trouver l'expéditeur
    # D'abord par biotag (sender_id correspond au biotag dans les transactions)
    sender = None
    if transaction.sender_id and transaction.sender_id.strip():
        sender = users_by_biotag.get(transaction.sender_id)
        if sender:
            logger.debug(f"Found sender by biotag (sender_id): {transaction.sender_id}")
    
    # Si pas trouvé par biotag, essayer par IBAN (fallback)
    if not sender and transaction.sender_iban and transaction.sender_iban.strip():
        sender = users_by_iban.get(transaction.sender_iban)
        if sender:
            logger.debug(f"Found sender by IBAN: {transaction.sender_iban}")
    
    if not sender and transaction.sender_id:
        logger.warning(f"Could not find sender for sender_id/biotag: {transaction.sender_id}")
    
    # Même logique pour le recipient
    recipient = None
    if transaction.recipient_id and transaction.recipient_id.strip():
        recipient = users_by_biotag.get(transaction.recipient_id)
        if recipient:
            logger.debug(f"Found recipient by biotag (recipient_id): {transaction.recipient_id}")
    
    # Si pas trouvé par biotag, essayer par IBAN (fallback)
    if not recipient and transaction.recipient_iban and transaction.recipient_iban.strip():
        recipient = users_by_iban.get(transaction.recipient_iban)
        if recipient:
            logger.debug(f"Found recipient by IBAN: {transaction.recipient_iban}")
    
    if not recipient and transaction.recipient_id:
        logger.debug(f"Could not find recipient for recipient_id/biotag: {transaction.recipient_id}")
    
    # Créer des ID utilisateur pour filtrer emails et SMS
    # Format: Prénom_Nom (utilisé dans les fichiers SMS/emails)
    def get_user_id(user: Optional[object]) -> Optional[str]:
        if user:
            return f"{user.first_name}_{user.last_name}"
        return None
    
    # Pour le sender: utiliser le format Prénom_Nom si on a trouvé le user
    sender_user_id = None
    if sender:
        sender_user_id = get_user_id(sender)
    
    # Pour le recipient: même logique
    recipient_user_id = None
    if recipient:
        recipient_user_id = get_user_id(recipient)
    
    logger.debug(f"Sender user_id for filtering: {sender_user_id}, sender found: {sender is not None}")
    logger.debug(f"Recipient user_id for filtering: {recipient_user_id}, recipient found: {recipient is not None}")
    
    # Filtrer les emails et SMS de l'expéditeur
    sender_emails = []
    sender_sms = []
    if sender_user_id:
        # Pour les emails, chercher dans les champs From et To
        # car un email peut être envoyé par l'utilisateur (From) ou reçu (To)
        for email in emails:
            email_content = email.mail
            # Extraire les IDs depuis From et To
            from_id = None
            to_id = None
            
            lines = email_content.split('\n')
            for line in lines:
                if 'From:' in line:
                    from_id = _extract_user_id_from_line(line)
                elif 'To:' in line:
                    to_id = _extract_user_id_from_line(line)
            
            # Vérifier si l'utilisateur est dans From ou To
            if (from_id and sender_user_id.lower() in from_id.lower()) or \
               (to_id and sender_user_id.lower() in to_id.lower()):
                sender_emails.append(email)
        
        for sms in sms_list:
            if sender_user_id.lower() in sms.id_user.lower():
                sender_sms.append(sms)
        
        logger.debug(f"Found {len(sender_emails)} emails and {len(sender_sms)} SMS for sender")
    else:
        logger.warning(f"No sender_user_id found, cannot filter SMS/emails. sender_id: {transaction.sender_id}")
    
    # Filtrer les emails et SMS du destinataire
    recipient_emails = []
    recipient_sms = []
    if recipient_user_id:
        # Pour les emails, chercher dans les champs From et To
        for email in emails:
            email_content = email.mail
            # Extraire les IDs depuis From et To
            from_id = None
            to_id = None
            
            lines = email_content.split('\n')
            for line in lines:
                if 'From:' in line:
                    from_id = _extract_user_id_from_line(line)
                elif 'To:' in line:
                    to_id = _extract_user_id_from_line(line)
            
            # Vérifier si l'utilisateur est dans From ou To
            if (from_id and recipient_user_id.lower() in from_id.lower()) or \
               (to_id and recipient_user_id.lower() in to_id.lower()):
                recipient_emails.append(email)
        
        for sms in sms_list:
            if recipient_user_id.lower() in sms.id_user.lower():
                recipient_sms.append(sms)
        
        logger.debug(f"Found {len(recipient_emails)} emails and {len(recipient_sms)} SMS for recipient")
    
    # Trouver les locations proches de la transaction
    sender_locations = []
    recipient_locations = []
    
    # Utiliser le sender_id (biotag) de la transaction pour trouver les locations
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
    
    # Récupérer les autres transactions pour le sender (dans une fenêtre de ±3 heures)
    sender_other_transactions = []
    if sender and sender.iban and transaction.timestamp:
        try:
            # Normaliser le timestamp de la transaction actuelle
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
                        # Normaliser le timestamp de la transaction à comparer
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
    
    # Récupérer les autres transactions pour le recipient (dans une fenêtre de ±3 heures)
    recipient_other_transactions = []
    if recipient and recipient.iban and transaction.timestamp:
        try:
            # Normaliser le timestamp de la transaction actuelle
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
                        # Normaliser le timestamp de la transaction à comparer
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
    
    # Créer les objets UserWithTransactions
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
    
    # Construire la réponse agrégée
    return AggregatedTransaction(
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

