.PHONY: help install install-dev test test-coverage lint format clean build build-extension run-server run-ext docker-up docker-down

PYTHON := python
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
VENV_DIR := venv

help:
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║        Pynt - Development & Build Commands                  ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 SETUP & INSTALLATION"
	@echo "  make install            - Install dependencies"
	@echo "  make install-dev        - Install dev dependencies (testing, linting)"
	@echo "  make venv               - Create Python virtual environment"
	@echo ""
	@echo "🧪 TESTING"
	@echo "  make test               - Run all tests"
	@echo "  make test-security      - Run security analysis tests"
	@echo "  make test-rag           - Run RAG tests (offline)"
	@echo "  make test-rag-online    - Run RAG evaluation (requires RUN_RAG_EVALUATION=1)"
	@echo "  make test-coverage      - Run tests with coverage report"
	@echo ""
	@echo "🔍 CODE QUALITY"
	@echo "  make lint               - Run linter (ruff)"
	@echo "  make format             - Format code (black)"
	@echo "  make format-check       - Check code formatting without changes"
	@echo "  make typecheck          - Run mypy type checking"
	@echo ""
	@echo "🏗️ BUILD & PACKAGE"
	@echo "  make build              - Build backend package"
	@echo "  make build-extension    - Build VS Code extension (.vsix)"
	@echo "  make clean              - Clean build artifacts & cache"
	@echo ""
	@echo "▶️ RUN"
	@echo "  make run-server         - Start backend (uvicorn)"
	@echo "  make run-ext            - Run extension in VS Code debug mode"
	@echo ""
	@echo "🐳 DOCKER"
	@echo "  make docker-build       - Build Docker image"
	@echo "  make docker-up          - Start services with docker-compose"
	@echo "  make docker-down        - Stop docker-compose services"
	@echo "  make docker-logs        - View docker-compose logs"
	@echo ""

## Setup & Installation

venv:
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "✓ Virtual environment created at $(VENV_DIR)/"
	@echo "  Activate with: source $(VENV_DIR)/bin/activate (Linux/Mac) or $(VENV_DIR)\\Scripts\\activate (Windows)"

install:
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements.txt
	@echo "✓ Dependencies installed"

install-dev: install
	$(PIP) install -r requirements.txt[dev]
	@echo "✓ Dev dependencies installed"

## Testing

test:
	$(PYTEST) tests/ -v

test-security:
	$(PYTEST) tests/test_security_analysis.py -v

test-rag:
	$(PYTEST) tests/ -v -m rag_offline

test-rag-online:
	$(PYTHON) -c "import os; os.environ['RUN_RAG_EVALUATION'] = '1'" && \
	$(PYTEST) tests/test_rag_evaluation_online.py -v -m rag_online --timeout=300

test-coverage:
	$(PYTEST) tests/ --cov=server --cov-report=html --cov-report=term-missing
	@echo "✓ Coverage report: htmlcov/index.html"

## Code Quality

lint:
	$(PYTHON) -m ruff check server/ tests/
	@echo "✓ Linting passed"

format:
	$(PYTHON) -m black server/ tests/
	@echo "✓ Code formatted"

format-check:
	$(PYTHON) -m black --check server/ tests/

typecheck:
	$(PYTHON) -m mypy server/
	@echo "✓ Type checking passed"

## Build & Package

build:
	$(PYTHON) -m build
	@echo "✓ Backend package built (dist/)"

build-extension:
	cd extension && npm install && npm run compile
	@echo "✓ Extension compiled"

# Package extension as .vsix (requires vsce)
package-extension:
	cd extension && npx @vscode/vsce package -o ../pynt-extension.vsix
	@echo "✓ Extension packaged: pynt-extension.vsix"

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✓ Cleaned build artifacts"

## Run Services

run-server:
	$(PYTHON) -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload

run-ext:
	@echo "Opening extension in VS Code debug mode..."
	cd extension && code . && code --extensionDevelopmentPath=. .

## Docker

docker-build:
	docker build -t pynt:latest .
	@echo "✓ Docker image built: pynt:latest"

docker-up:
	docker-compose up -d
	@echo "✓ Services started"
	@echo "  Backend: http://localhost:8000"
	@echo "  Health: http://localhost:8000/health"

docker-down:
	docker-compose down
	@echo "✓ Services stopped"

docker-logs:
	docker-compose logs -f backend

docker-clean:
	docker-compose down -v
	docker rmi pynt:latest
	@echo "✓ Docker cleaned"

## Utilities

.DEFAULT_GOAL := help
