# Makefile for FractalChain

.PHONY: help install test run clean docker

help:
	@echo "FractalChain Makefile"
	@echo ""
	@echo "Available commands:"
	@echo "  make install    - Install FractalChain and dependencies"
	@echo "  make test       - Run test suite"
	@echo "  make run        - Run FractalChain node"
	@echo "  make mine       - Run FractalChain node with mining"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make docker     - Build and run with Docker"
	@echo "  make lint       - Run code linters"
	@echo ""

install:
	@echo "Installing FractalChain..."
	chmod +x install.sh
	./install.sh

test:
	@echo "Running tests..."
	. venv/bin/activate && pytest tests/ -v

run:
	@echo "Starting FractalChain node..."
	. venv/bin/activate && python3 main.py

mine:
	@echo "Starting FractalChain node with mining..."
	. venv/bin/activate && python3 main.py --mine

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf venv/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

docker:
	@echo "Building and running with Docker..."
	docker-compose up --build

docker-down:
	@echo "Stopping Docker containers..."
	docker-compose down

lint:
	@echo "Running linters..."
	. venv/bin/activate && flake8 . --exclude=venv
	. venv/bin/activate && pylint core/ consensus/ network/ economic/ api/ utils/

format:
	@echo "Formatting code..."
	. venv/bin/activate && black .

coverage:
	@echo "Running tests with coverage..."
	. venv/bin/activate && pytest tests/ --cov=. --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

benchmark:
	@echo "Running benchmarks..."
	. venv/bin/activate && python3 tests/benchmark.py

wallet:
	@echo "Creating new wallet..."
	. venv/bin/activate && python3 -m api.cli wallet create

info:
	@echo "Getting blockchain info..."
	. venv/bin/activate && python3 -m api.cli chain info
