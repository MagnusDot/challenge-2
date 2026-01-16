from helpers.config import SYSTEM_PROMPT_PATH

def load_analysis_prompt() -> str:
    with open(SYSTEM_PROMPT_PATH, 'r', encoding='utf-8') as f:
        return f.read()
