# Makefile - targets: venv, install, test, clean

.PHONY: venv install test clean

VENV=.venv
PYTHON=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

venv:
	@test -d $(VENV) || python3 -m venv $(VENV)

install: venv
	@echo "Activating venv and installing dev requirements..."
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements.txt

test: install
	@echo "Running tests..."
	@$(PYTHON) -m pytest -q

clean:
	@echo "Cleaning..."
	@rm -rf $(VENV) .pytest_cache __pycache__ tests/__pycache__



























