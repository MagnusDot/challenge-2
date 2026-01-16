# Reply Challenge

Transaction analysis project with fraud detection using Google ADK.

## Main Scripts

### Transaction Analysis

The main script to analyze all transactions is `app.py`.

**Usage with Just:**
```bash
# Main command - Analysis with 50 concurrent requests (default)
just run

# Analysis with custom number of concurrent requests
just run CONCURRENT=10

# Analysis with 5 concurrent requests (default for analyze-all-transactions)
just analyze-all-transactions

# Analysis with custom number of concurrent requests
just analyze-all-transactions CONCURRENT=10

# Debug mode to see token events
just analyze-parallel-debug CONCURRENT=5

# Sequential analysis (old script, slower)
just analyze-all-sequential

# Initialize agent only (original app.py behavior)
just init-agent
```

**Direct usage:**
```bash
python app.py
```

## Configuration

The script uses the following environment variables (defined in `.env`):

### API Keys (required)
- `OPENAI_API_KEY` or `GOOGLE_API_KEY`: API key for the LLM model (at least one required)

### Model Configuration
- `MODEL`: Model to use (default: `openai/gpt-4.1`)

### Data Configuration
- `DATASET_FOLDER`: Dataset folder to analyze (default: `public 4`)
  - Examples: `public 4`, `public 5`, `public 6`
  - Expected file: `dataset/{DATASET_FOLDER}/transactions_dataset.json`

### System Prompt Configuration
- `SYSTEM_PROMPT_FILE`: System prompt file (default: `system_prompt_v2.md`)
  - Relative path to `Agent/` directory or absolute path
  - Examples: `system_prompt_v2.md`, `system_prompt.md`, `transaction_analysis_prompt.md`

### Parallelization Configuration
- `MAX_CONCURRENT_REQUESTS`: Number of concurrent requests
  - Default: `50` for `just run`
  - Default: `5` for `just analyze-all-transactions`

### Example `.env` file
```env
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
MODEL=openai/gpt-4.1
DATASET_FOLDER=public 4
SYSTEM_PROMPT_FILE=system_prompt_v2.md
MAX_CONCURRENT_REQUESTS=50
```

## Project Structure

- `Agent/`: Fraud detection agent implementation
- `scripts/`: Analysis and processing scripts
- `api/`: REST API for transaction analysis
- `dataset/`: Transaction datasets
- `docs/`: Project documentation
