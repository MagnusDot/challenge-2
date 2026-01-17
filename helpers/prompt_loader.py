from functools import lru_cache
from helpers.config import SYSTEM_PROMPT_PATH

@lru_cache(maxsize=1)
def load_analysis_prompt() -> str:

    with open(SYSTEM_PROMPT_PATH, 'r', encoding='utf-8') as f:
        return f.read()