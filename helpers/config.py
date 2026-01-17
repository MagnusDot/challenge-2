import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent

MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', '5'))
SAVE_INTERVAL = 5

def get_batch_size(model: str = None) -> int:
    """Calcule la taille de batch appropriée selon le modèle.
    
    Args:
        model: Nom du modèle (optionnel, lit depuis MODEL env var si non fourni)
        
    Returns:
        Taille de batch recommandée
    """
    if model is None:
        model = os.getenv('MODEL', '')
    
    model_lower = model.lower()
    
    # Certains modèles ont des limites de contexte plus petites
    # Mistral: 131k tokens -> batch de 50
    # DeepSeek Chat: 64k tokens -> batch de 30 pour être sûr
    # Gemini Flash: 1M tokens mais peut avoir d'autres limites
    if 'mistral' in model_lower or 'mixtral' in model_lower:
        return int(os.getenv('BATCH_SIZE', '50'))
    elif 'deepseek-chat' in model_lower or 'deepseek' in model_lower:
        return int(os.getenv('BATCH_SIZE', '30'))
    elif 'gpt-3.5' in model_lower:
        return int(os.getenv('BATCH_SIZE', '30'))
    
    # Par défaut, utiliser 200 transactions
    return int(os.getenv('BATCH_SIZE', '200'))

BATCH_SIZE = get_batch_size()

DATASET_FOLDER = os.getenv('DATASET_FOLDER', 'public 2')
DATASET_PATH = PROJECT_ROOT / "dataset" / DATASET_FOLDER / "transactions_dataset.json"

SYSTEM_PROMPT_FILE = os.getenv('SYSTEM_PROMPT_FILE', 'system_prompt_compact.md')
if Path(SYSTEM_PROMPT_FILE).is_absolute():
    SYSTEM_PROMPT_PATH = Path(SYSTEM_PROMPT_FILE)
else:
    SYSTEM_PROMPT_PATH = PROJECT_ROOT / "Agent" / SYSTEM_PROMPT_FILE