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
- `OPENROUTER_API_KEY`: API key for OpenRouter (recommended)
- Alternative: `OPENAI_API_KEY` or `GOOGLE_API_KEY` for direct API access

### Model Configuration
- `MODEL`: Model to use (default: `openrouter/openai/gpt-5-mini`)
  - OpenRouter format: `openrouter/provider/model` (e.g., `openrouter/openai/gpt-5-mini`, `openrouter/openai/gpt-4o`, `openrouter/anthropic/claude-3.5-sonnet`)
  - Direct OpenAI format: `openai/gpt-4.1`
  - Gemini format: `gemini-2.0-flash-exp`

### Data Configuration
- `DATASET_FOLDER`: Dataset folder to analyze (default: `public 4`)
  - Examples: `public 4`, `public 5`, `public 6`
  - Expected file: `dataset/{DATASET_FOLDER}/transactions_dataset.json`

### System Prompt Configuration
- `SYSTEM_PROMPT_FILE`: System prompt file (default: `system_prompt_compact.md`)
  - Relative path to `Agent/` directory or absolute path
  - **Default**: `system_prompt_compact.md` (optimized for token efficiency, ~70% fewer tokens)
  - Alternatives: `system_prompt.md` (full version, 439 lines), `system_prompt_v2.md`
  - Examples: `system_prompt_compact.md`, `system_prompt.md`, `system_prompt_v2.md`

### Parallelization Configuration
- `MAX_CONCURRENT_REQUESTS`: Number of concurrent requests
  - Default: `50` for `just run`
  - Default: `5` for `just analyze-all-transactions`
- `BATCH_SIZE`: Number of transactions to process per batch
  - Default: `200`
  - Transactions are analyzed in batches, with automatic save after each batch

### Caching Configuration

The project supports both **request caching** and **prompt caching** to reduce API costs and improve performance.

#### Request Caching (LiteLLM)
LiteLLM caching is configured via environment variables:
- `LITELLM_CACHE`: Set to `"True"` to enable caching (default: disabled)
  - Works with OpenAI/OpenRouter models
  - Caches identical prompts to reduce API costs
- `LITELLM_CACHE_TYPE`: Cache backend type (default: `local`)
  - Options: `local` (in-memory), `redis` (requires Redis server)
  
**Example:**
```bash
export LITELLM_CACHE="True"
export LITELLM_CACHE_TYPE="local"
```

#### Prompt Caching (Context Caching)
For Gemini 2.0+ models, use `App` with `ContextCacheConfig` instead of `Runner`:
- `CONTEXT_CACHE_MIN_TOKENS`: Minimum tokens to enable caching (default: `2048`)
- `CONTEXT_CACHE_TTL_SECONDS`: Cache time-to-live in seconds (default: `600`)
- `CONTEXT_CACHE_INTERVALS`: Max cache uses before refresh (default: `5`)

**Note**: Context caching requires using `App` instead of `Runner`. See `core/app_setup.py` for an example.

### Token Optimization

The project is optimized to minimize token usage:

1. **Compact System Prompt**: Default `system_prompt_compact.md` uses ~70% fewer tokens than full version
   - Removed redundant explanations and examples
   - Uses concise, structured format
   - Maintains all critical detection logic

2. **TOON Format**: API responses use TOON format (~40% fewer tokens than JSON)
   - Automatically used in `get_transaction_aggregated` tool
   - No wrapper text, direct TOON output

3. **Optimized Tool Responses**: Minimal wrapper text in tool responses

**To use full prompt** (if needed for debugging):
```env
SYSTEM_PROMPT_FILE=system_prompt.md
```

### Example `.env` file
```env
OPENROUTER_API_KEY=sk-or-v1-...
MODEL=openrouter/openai/gpt-5-mini
DATASET_FOLDER=public 4
SYSTEM_PROMPT_FILE=system_prompt_compact.md
MAX_CONCURRENT_REQUESTS=50

# Caching configuration
LITELLM_CACHE=true
LITELLM_CACHE_TYPE=local

# Context caching (for Gemini models)
CONTEXT_CACHE_MIN_TOKENS=2048
CONTEXT_CACHE_TTL_SECONDS=600
CONTEXT_CACHE_INTERVALS=5
```

## Project Structure

- `Agent/`: Fraud detection agent implementation
- `scripts/`: Analysis and processing scripts
- `api/`: REST API for transaction analysis
- `dataset/`: Transaction datasets
- `docs/`: Project documentation
