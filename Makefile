# Ouroboros — common development commands
# Usage: make test, make lint, make health

PYTHON ?= python3
UV ?= uv

.PHONY: install sync sync-global test lint health clean

install:
	bash scripts/install.sh

sync:
	$(UV) sync --extra browser

sync-global:
	$(PYTHON) -m pip install -r requirements.txt

# Run smoke tests (fast, no external deps needed at runtime)
test:
	$(PYTHON) -m pytest tests/ -q --tb=short

# Run smoke tests with verbose output
test-v:
	$(PYTHON) -m pytest tests/ -v --tb=long

# Run codebase health check (requires ouroboros importable)
health:
	$(PYTHON) -c "from ouroboros.review import compute_complexity_metrics; \
		import pathlib, json; \
		m = compute_complexity_metrics(pathlib.Path('.')); \
		print(json.dumps(m, indent=2, default=str))"

# Clean Python cache files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
