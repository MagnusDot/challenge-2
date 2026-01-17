# Justfile for Reply Challenge
# Run `just` to see available commands

# Default recipe to display help
default:
    @just --list

# Create virtual environment
venv:
    python3 -m venv .venv
    @echo "✅ Virtual environment created"
    @echo "💡 Run 'just install' to install dependencies"

# Install dependencies
install:
    .venv/bin/pip install -r requirements.txt
    @echo "✅ Dependencies installed"

# Install dependencies and upgrade pip
install-upgrade:
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
    @echo "✅ Dependencies installed with upgraded pip"

# Run the application (analyze all transactions with parallel script)
# Uses 50 concurrent requests by default for maximum performance
run CONCURRENT="50":
    @echo "🚀 Starting transaction analysis with {{CONCURRENT}} concurrent requests..."
    PYTHONPATH=. MAX_CONCURRENT_REQUESTS={{CONCURRENT}} .venv/bin/python app.py
    @echo "✅ Analysis complete! Check scripts/results/transaction_risk_analysis_*.json"

# Retry failed transactions (batch bonus)
# Automatically finds the latest results file and retries all transactions with risk_level="error"
retry CONCURRENT="50":
    @echo "🔄 Starting batch bonus to retry failed transactions..."
    PYTHONPATH=. MAX_CONCURRENT_REQUESTS={{CONCURRENT}} .venv/bin/python app.py retry
    @echo "✅ Batch bonus complete! Check scripts/results/transaction_risk_analysis_bonus_*.json"
    @echo "💡 Merged results saved in scripts/results/transaction_risk_analysis_merged_*.json"

# Retry failed transactions from a specific results file
retry-file RESULTS_FILE CONCURRENT="50":
    @echo "🔄 Starting batch bonus to retry failed transactions from {{RESULTS_FILE}}..."
    PYTHONPATH=. MAX_CONCURRENT_REQUESTS={{CONCURRENT}} .venv/bin/python app.py retry {{RESULTS_FILE}}
    @echo "✅ Batch bonus complete! Check scripts/results/transaction_risk_analysis_bonus_*.json"
    @echo "💡 Merged results saved in scripts/results/transaction_risk_analysis_merged_*.json"

# Initialize agent only (original app.py behavior)
init-agent:
    .venv/bin/python app.py

# Run ADK web interface
web PORT="8001":
    @echo "🚀 Starting ADK web interface on port {{PORT}}..."
    .venv/bin/adk web --port {{PORT}}

# Create .env file from example
env:
    cp .env.example .env
    @echo "✅ .env file created"
    @echo "⚠️  Don't forget to add your OPENROUTER_API_KEY"

# Setup everything (venv, install, env)
setup:
    @just venv
    @just install
    @just env
    @echo ""
    @echo "🎉 Setup complete!"
    @echo "📝 Next steps:"
    @echo "   1. Add your OPENROUTER_API_KEY to .env"
    @echo "   2. Run: just run (analyzes transactions with 50 concurrent requests)"

# Clean virtual environment
clean:
    rm -rf .venv
    @echo "✅ Virtual environment removed"

# Clean Python cache files
clean-cache:
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    @echo "✅ Python cache cleaned"

# Clean everything
clean-all: clean clean-cache
    @echo "✅ All cleaned"

# Show environment info
info:
    @echo "Python version:"
    @python3 --version
    @echo ""
    @echo "Virtual environment status:"
    @if [ -d ".venv" ]; then echo "✅ .venv exists"; else echo "❌ .venv not found"; fi
    @echo ""
    @echo ".env file status:"
    @if [ -f ".env" ]; then echo "✅ .env exists"; else echo "❌ .env not found"; fi

# Freeze current dependencies
freeze:
    .venv/bin/pip freeze > requirements.txt
    @echo "✅ Dependencies frozen to requirements.txt"

# ==== Dataset Commands ====

# Convert CSV dataset to JSON (uses DATASET_FOLDER from .env)
csv-to-json:
    PYTHONPATH=. .venv/bin/python scripts/convert_csv_to_json.py --pretty
    @echo "💡 JSON file created in dataset folder (see DATASET_FOLDER in .env)"

# Convert CSV dataset to JSON (compact format, no indentation)
csv-to-json-compact:
    PYTHONPATH=. .venv/bin/python scripts/convert_csv_to_json.py
    @echo "💡 JSON file created in dataset folder (see DATASET_FOLDER in .env)"

# Normalize dataset file names (remove timestamps and numbers) - preview only
normalize-files-preview:
    PYTHONPATH=. .venv/bin/python scripts/normalize_dataset_files.py --dry-run

# Normalize dataset file names (remove timestamps and numbers)
normalize-files:
    PYTHONPATH=. .venv/bin/python scripts/normalize_dataset_files.py

# ==== Evaluation Commands ====

# Evaluate predictions against ground truth
# Output saved to dataset/evals/<ground_truth_filename>.json
# Usage: just eval predictions.json dataset/ground_truth/public_1.csv
eval PREDICTIONS GROUND_TRUTH:
    @mkdir -p dataset/evals
    @echo "📊 Evaluating predictions..."
    PYTHONPATH=. .venv/bin/python scripts/evaluate_results.py -p {{PREDICTIONS}} -g {{GROUND_TRUTH}} -o dataset/evals/$(basename {{GROUND_TRUTH}} .csv).json
    @echo "💾 Results saved to dataset/evals/$(basename {{GROUND_TRUTH}} .csv).json"

# ==== API Commands ====

# Run API locally (development)
api-dev:
    .venv/bin/uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Build Docker image
docker-build:
    docker-compose build

# Start API with Docker
docker-up:
    docker-compose up -d
    @echo "✅ API running at http://localhost:8000"
    @echo "📚 API docs at http://localhost:8000/docs"

# Stop Docker containers
docker-down:
    docker-compose down

# View Docker logs
docker-logs:
    docker-compose logs -f

# Restart Docker containers
docker-restart:
    docker-compose restart

# Check API health
api-health:
    @curl -f http://localhost:8000/health || echo "❌ API not responding"

# Check if .env has OPENROUTER_API_KEY set
check-env:
    @if [ ! -f ".env" ]; then echo "❌ .env file not found"; exit 1; fi
    @if grep -q "OPENROUTER_API_KEY=$" .env || ! grep -q "OPENROUTER_API_KEY" .env; then \
        echo "❌ OPENROUTER_API_KEY not set in .env"; \
        exit 1; \
    fi
    @echo "✅ OPENROUTER_API_KEY is set"

# Run app.py with environment check
run-safe: check-env
    .venv/bin/python app.py

# Run web interface with environment check
web-safe PORT="8000": check-env
    @echo "🚀 Starting ADK web interface on port {{PORT}}..."
    .venv/bin/adk web --port {{PORT}}

