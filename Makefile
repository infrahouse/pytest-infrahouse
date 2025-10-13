.DEFAULT_GOAL := help

# Use bash for shell commands
SHELL := /bin/bash

# Python and pip executables
PYTHON := python3
PIP := pip3

# Package name from pyproject.toml
PACKAGE_NAME := pytest-infrahouse

# Directories
SRC_DIR := src
TEST_DIR := tests
DIST_DIR := dist
BUILD_DIR := build

.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: install
install: ## Install package in development mode
	$(PIP) install -e .

.PHONY: install-dev
install-dev: ## Install package with development dependencies
	$(PIP) install -e '.[dev]' || $(PIP) install -e .

.PHONY: clean
clean: ## Clean build artifacts and cache files
	rm -rf $(BUILD_DIR)/ $(DIST_DIR)/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

.PHONY: format
format: ## Format code with black and isort
	black $(SRC_DIR) $(TEST_DIR)
	isort $(SRC_DIR) $(TEST_DIR)
	terraform fmt -recursive

.PHONY: lint
lint: ## Run linting checks
	black --check $(SRC_DIR) $(TEST_DIR)
	isort --check-only $(SRC_DIR) $(TEST_DIR)

.PHONY: test
test: ## Run tests
	pytest -xvvs $(TEST_DIR)

.PHONY: test-verbose
test-verbose: ## Run tests with verbose output
	pytest -svvx $(TEST_DIR)

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report
	pytest --cov=$(SRC_DIR) --cov-report=html --cov-report=term $(TEST_DIR)

.PHONY: build
build: clean ## Build package
	$(PYTHON) -m build

.PHONY: upload-test
upload-test: build ## Upload package to Test PyPI
	twine upload --repository testpypi $(DIST_DIR)/*

.PHONY: upload
upload: build ## Upload package to PyPI
	twine upload $(DIST_DIR)/*

.PHONY: bump-patch
bump-patch: ## Bump patch version
	bump2version patch

.PHONY: bump-minor
bump-minor: ## Bump minor version
	bump2version minor

.PHONY: bump-major
bump-major: ## Bump major version
	bump2version major

.PHONY: check
check: lint test ## Run all checks (lint and test)

.PHONY: all
all: clean format check build ## Run all tasks (clean, format, check, build)
