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
    @echo "⚠️  Don't forget to add your OPENAI_API_KEY"

# Setup everything (venv, install, env)
setup:
    @just venv
    @just install
    @just env
    @echo ""
    @echo "🎉 Setup complete!"
    @echo "📝 Next steps:"
    @echo "   1. Add your OPENAI_API_KEY or GOOGLE_API_KEY to .env"
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

# Convert CSV dataset to JSON
csv-to-json:
    PYTHONPATH=. .venv/bin/python scripts/convert_csv_to_json.py --pretty
    @echo "💡 JSON file created: dataset/transactions_dataset.json"

# Extract high-risk transaction IDs
extract-high-risk:
    PYTHONPATH=. .venv/bin/python scripts/extract_high_risk_ids.py
    @echo "✅ High-risk IDs extracted!"

# Filter high-risk transactions
filter-high-risk:
    PYTHONPATH=. .venv/bin/python scripts/filter_high_risk.py
    @echo "✅ High-risk transactions filtered!"

# Analyze all transactions with AI agent (generates risk assessment)
# Uses parallel script by default (main script)
analyze-all-transactions CONCURRENT="5":
    @echo "🚀 Starting analysis with {{CONCURRENT}} concurrent requests..."
    PYTHONPATH=. MAX_CONCURRENT_REQUESTS={{CONCURRENT}} .venv/bin/python app.py
    @echo "✅ Analysis complete! Check scripts/results/transaction_risk_analysis_*.json"

# Analyze all transactions in parallel with AI agent (alias for analyze-all-transactions)
analyze-all-parallel CONCURRENT="5":
    @just analyze-all-transactions CONCURRENT={{CONCURRENT}}

# Analyze all transactions sequentially (legacy script, slower)
analyze-all-sequential:
    @echo "⚠️  Using legacy sequential script (slower)"
    PYTHONPATH=. .venv/bin/python scripts/analyze_all_transactions.py
    @echo "✅ Sequential analysis complete! Check scripts/results/transaction_risk_analysis_*.json"

# Analyze with debug mode to see token usage events
analyze-parallel-debug CONCURRENT="5":
    @echo "🐛 Starting parallel analysis with DEBUG mode..."
    PYTHONPATH=. DEBUG_TOKENS=1 MAX_CONCURRENT_REQUESTS={{CONCURRENT}} .venv/bin/python app.py
    @echo "✅ Debug analysis complete! Check scripts/results/"

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

# Check if .env has OPENAI_API_KEY set
check-env:
    @if [ ! -f ".env" ]; then echo "❌ .env file not found"; exit 1; fi
    @if grep -q "OPENAI_API_KEY=$" .env || ! grep -q "OPENAI_API_KEY" .env; then \
        echo "❌ OPENAI_API_KEY not set in .env"; \
        exit 1; \
    fi
    @echo "✅ OPENAI_API_KEY is set"

# Run app.py with environment check
run-safe: check-env
    .venv/bin/python app.py

# Run web interface with environment check
web-safe PORT="8000": check-env
    @echo "🚀 Starting ADK web interface on port {{PORT}}..."
    .venv/bin/adk web --port {{PORT}}

