import json
from pathlib import Path
from typing import List
from functools import lru_cache

from api.models import User, Transaction, Location, SMS, Email

_DATASET_FOLDER = "public 1"

PROJECT_ROOT = Path(__file__).parent.parent.parent

def get_dataset_folder() -> str:

    return _DATASET_FOLDER

def get_dataset_dir() -> Path:

    return PROJECT_ROOT / "dataset" / _DATASET_FOLDER

def set_dataset_folder(folder_name: str) -> None:

    global _DATASET_FOLDER

    dataset_path = PROJECT_ROOT / "dataset" / folder_name
    if not dataset_path.exists():
        raise ValueError(
            f"Dataset folder '{folder_name}' does not exist. "
            f"Available datasets: {[d.name for d in (PROJECT_ROOT / 'dataset').iterdir() if d.is_dir()]}"
        )

    required_file = dataset_path / "transactions_dataset.json"
    if not required_file.exists():
        raise ValueError(
            f"Dataset folder '{folder_name}' is missing required file 'transactions_dataset.json'"
        )

    _DATASET_FOLDER = folder_name

    clear_cache()

def _build_iban_to_biotag_mapping() -> dict:

    try:

        transactions_path = get_dataset_dir() / "transactions_dataset.json"
        if not transactions_path.exists():
            return {}

        with open(transactions_path, 'r', encoding='utf-8') as f:
            transactions_data = json.load(f)

        iban_to_biotag = {}

        for tx in transactions_data:

            sender_id = tx.get('sender_id', '').strip() if tx.get('sender_id') else ''
            sender_iban = tx.get('sender_iban', '').strip() if tx.get('sender_iban') else ''
            if sender_id and sender_iban:
                iban_to_biotag[sender_iban] = sender_id

            recipient_id = tx.get('recipient_id', '').strip() if tx.get('recipient_id') else ''
            recipient_iban = tx.get('recipient_iban', '').strip() if tx.get('recipient_iban') else ''
            if recipient_id and recipient_iban:
                iban_to_biotag[recipient_iban] = recipient_id

        return iban_to_biotag
    except Exception:

        return {}

@lru_cache(maxsize=1)
def load_users() -> List[User]:

    dataset_dir = get_dataset_dir()

    descriptions_path = dataset_dir / "users_descriptions.json"
    if descriptions_path.exists():
        with open(descriptions_path, 'r', encoding='utf-8') as f:
            descriptions_data = json.load(f)

        users = []
        for item in descriptions_data:

            person_data = item.get("person_data", {})
            biotag = person_data.get("_biotag")
            description = item.get("description")

            user_dict = {
                "first_name": person_data.get("first_name"),
                "last_name": person_data.get("last_name"),
                "birth_year": person_data.get("birth_year"),
                "salary": person_data.get("salary"),
                "job": person_data.get("job"),
                "iban": person_data.get("iban"),
                "residence": person_data.get("residence"),
                "biotag": biotag,
                "description": description
            }
            users.append(User(**user_dict))

        return users

    file_path = dataset_dir / "users.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    iban_to_biotag = _build_iban_to_biotag_mapping()

    enriched_users = []
    for item in data:

        if 'biotag' not in item or not item.get('biotag'):
            iban = item.get('iban', '')
            if iban in iban_to_biotag:
                item['biotag'] = iban_to_biotag[iban]

        enriched_users.append(User(**item))

    return enriched_users

@lru_cache(maxsize=1)
def load_transactions() -> List[Transaction]:

    file_path = get_dataset_dir() / "transactions_dataset.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [Transaction(**item) for item in data]

@lru_cache(maxsize=1)
def load_locations() -> List[Location]:

    file_path = get_dataset_dir() / "locations.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Normaliser les données : mapper 'timestamp' vers 'datetime' si nécessaire
    # Filtrer les locations sans datetime/timestamp valide
    normalized_data = []
    for item in data:
        normalized_item = item.copy()
        # Si 'timestamp' existe mais pas 'datetime', mapper timestamp -> datetime
        if 'timestamp' in normalized_item and 'datetime' not in normalized_item:
            normalized_item['datetime'] = normalized_item.pop('timestamp')
        
        # Ignorer les locations sans datetime (champ requis par le modèle)
        if 'datetime' not in normalized_item:
            continue
            
        normalized_data.append(normalized_item)
    
    return [Location(**item) for item in normalized_data]

@lru_cache(maxsize=1)
def load_sms() -> List[SMS]:

    dataset_dir = get_dataset_dir()

    sms_files = list(dataset_dir.glob("generated_sms_*.json"))

    if sms_files:

        latest_file = max(sms_files, key=lambda p: p.stat().st_mtime)
    else:

        latest_file = dataset_dir / "generated_sms.json"
        if not latest_file.exists():
            return []

    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [SMS(**item) for item in data]

@lru_cache(maxsize=1)
def load_emails() -> List[Email]:

    dataset_dir = get_dataset_dir()

    email_files = list(dataset_dir.glob("generated_mails_*.json"))

    if email_files:

        latest_file = max(email_files, key=lambda p: p.stat().st_mtime)
    else:

        latest_file = dataset_dir / "generated_mails.json"
        if not latest_file.exists():
            return []

    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [Email(**item) for item in data]

def clear_cache():

    load_users.cache_clear()
    load_transactions.cache_clear()
    load_locations.cache_clear()
    load_sms.cache_clear()
    load_emails.cache_clear()