import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent

MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', '5'))
SAVE_INTERVAL = 5

DATASET_FOLDER = os.getenv('DATASET_FOLDER', 'public 2')
DATASET_PATH = PROJECT_ROOT / "dataset" / DATASET_FOLDER / "transactions_dataset.json"

SYSTEM_PROMPT_FILE = os.getenv('SYSTEM_PROMPT_FILE', 'system_prompt.md')
if Path(SYSTEM_PROMPT_FILE).is_absolute():
    SYSTEM_PROMPT_PATH = Path(SYSTEM_PROMPT_FILE)
else:
    SYSTEM_PROMPT_PATH = PROJECT_ROOT / "Agent" / SYSTEM_PROMPT_FILE
