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
_DATASET_FOLDER = "public 2"  # Change to "public 1", "public 2", etc.
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
    """Load users from JSON file with caching."""
    file_path = get_dataset_dir() / "users.json"
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
    """Load SMS messages from JSON file with caching."""
    # Find the most recent SMS file
    dataset_dir = get_dataset_dir()
    sms_files = list(dataset_dir.glob("generated_sms_*.json"))
    if not sms_files:
        return []
    
    latest_file = max(sms_files, key=lambda p: p.stat().st_mtime)
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [SMS(**item) for item in data]


@lru_cache(maxsize=1)
def load_emails() -> List[Email]:
    """Load emails from JSON file with caching."""
    # Find the most recent email file
    dataset_dir = get_dataset_dir()
    email_files = list(dataset_dir.glob("generated_mails_*.json"))
    if not email_files:
        return []
    
    latest_file = max(email_files, key=lambda p: p.stat().st_mtime)
    
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

