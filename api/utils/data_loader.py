"""
Data loader utilities for loading JSON datasets.
"""

import json
from pathlib import Path
from typing import List
from functools import lru_cache

from api.models import User, Transaction, Location, SMS, Email

# ============================================================================
# CONFIGURATION - Modify this path to switch datasets
# ============================================================================
_DATASET_FOLDER = "public 1"  # Change to "public 1", "public 2", etc.
# ============================================================================

# Get the project root (2 levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent


def get_dataset_folder() -> str:
    """Récupère le nom du dossier dataset actuellement actif.
    
    Returns:
        Nom du dossier dataset (ex: "public 4")
    """
    return _DATASET_FOLDER


def get_dataset_dir() -> Path:
    """Récupère le chemin complet du dossier dataset actuellement actif.
    
    Returns:
        Chemin Path vers le dossier dataset
    """
    return PROJECT_ROOT / "dataset" / _DATASET_FOLDER


def set_dataset_folder(folder_name: str) -> None:
    """Change le dataset actif et vide le cache.
    
    Args:
        folder_name: Nom du dossier dataset (ex: "public 2", "public 3")
        
    Raises:
        ValueError: Si le dataset n'existe pas ou est invalide
    """
    global _DATASET_FOLDER
    
    # Validate that the dataset folder exists
    dataset_path = PROJECT_ROOT / "dataset" / folder_name
    if not dataset_path.exists():
        raise ValueError(
            f"Dataset folder '{folder_name}' does not exist. "
            f"Available datasets: {[d.name for d in (PROJECT_ROOT / 'dataset').iterdir() if d.is_dir()]}"
        )
    
    # Check that required file exists
    required_file = dataset_path / "transactions_dataset.json"
    if not required_file.exists():
        raise ValueError(
            f"Dataset folder '{folder_name}' is missing required file 'transactions_dataset.json'"
        )
    
    # Update the dataset folder
    _DATASET_FOLDER = folder_name
    
    # Clear all caches
    clear_cache()


@lru_cache(maxsize=1)
def load_users() -> List[User]:
    """Load users from JSON file with caching.
    
    Tries to load from users_descriptions.json first (which contains biotags),
    falls back to users.json if not available.
    """
    dataset_dir = get_dataset_dir()
    
    # Try to load from users_descriptions.json first (contains biotags)
    descriptions_path = dataset_dir / "users_descriptions.json"
    if descriptions_path.exists():
        with open(descriptions_path, 'r', encoding='utf-8') as f:
            descriptions_data = json.load(f)
        
        users = []
        for item in descriptions_data:
            # Extract person_data, biotag, and description
            person_data = item.get("person_data", {})
            biotag = person_data.get("_biotag")
            description = item.get("description")
            
            # Create user from person_data (which has the same structure as users.json)
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
    
    # Fallback to users.json if users_descriptions.json doesn't exist
    file_path = dataset_dir / "users.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [User(**item) for item in data]


@lru_cache(maxsize=1)
def load_transactions() -> List[Transaction]:
    """Load transactions from JSON file with caching."""
    file_path = get_dataset_dir() / "transactions_dataset.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [Transaction(**item) for item in data]


@lru_cache(maxsize=1)
def load_locations() -> List[Location]:
    """Load locations from JSON file with caching."""
    file_path = get_dataset_dir() / "locations.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [Location(**item) for item in data]


@lru_cache(maxsize=1)
def load_sms() -> List[SMS]:
    """Load SMS messages from JSON file with caching.
    
    Tries to find files matching generated_sms_*.json pattern first,
    falls back to generated_sms.json if no timestamped files exist.
    """
    dataset_dir = get_dataset_dir()
    
    # Try to find timestamped files first
    sms_files = list(dataset_dir.glob("generated_sms_*.json"))
    
    if sms_files:
        # Use the most recent timestamped file
        latest_file = max(sms_files, key=lambda p: p.stat().st_mtime)
    else:
        # Fallback to generated_sms.json (without timestamp)
        latest_file = dataset_dir / "generated_sms.json"
        if not latest_file.exists():
            return []
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [SMS(**item) for item in data]


@lru_cache(maxsize=1)
def load_emails() -> List[Email]:
    """Load emails from JSON file with caching.
    
    Tries to find files matching generated_mails_*.json pattern first,
    falls back to generated_mails.json if no timestamped files exist.
    """
    dataset_dir = get_dataset_dir()
    
    # Try to find timestamped files first
    email_files = list(dataset_dir.glob("generated_mails_*.json"))
    
    if email_files:
        # Use the most recent timestamped file
        latest_file = max(email_files, key=lambda p: p.stat().st_mtime)
    else:
        # Fallback to generated_mails.json (without timestamp)
        latest_file = dataset_dir / "generated_mails.json"
        if not latest_file.exists():
            return []
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [Email(**item) for item in data]


def clear_cache():
    """Clear all caches."""
    load_users.cache_clear()
    load_transactions.cache_clear()
    load_locations.cache_clear()
    load_sms.cache_clear()
    load_emails.cache_clear()

