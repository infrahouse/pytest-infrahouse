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
	find . -type d -name ".terraform" -exec rm -rf {} +

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

# Internal function to handle version release
# Args: $(1) = major|minor|patch
define do_release
	@echo "Checking if git-cliff is installed..."
	@command -v git-cliff >/dev/null 2>&1 || { \
		echo ""; \
		echo "Error: git-cliff is not installed."; \
		echo ""; \
		echo "Please install it using one of the following methods:"; \
		echo ""; \
		echo "  Cargo (Rust):"; \
		echo "    cargo install git-cliff"; \
		echo ""; \
		echo "  Arch Linux:"; \
		echo "    pacman -S git-cliff"; \
		echo ""; \
		echo "  Homebrew (macOS/Linux):"; \
		echo "    brew install git-cliff"; \
		echo ""; \
		echo "  From binary (Linux/macOS/Windows):"; \
		echo "    https://github.com/orhun/git-cliff/releases"; \
		echo ""; \
		echo "For more installation options, see: https://git-cliff.org/docs/installation"; \
		echo ""; \
		exit 1; \
	}
	@echo "Checking if bumpversion is installed..."
	@command -v bumpversion >/dev/null 2>&1 || { \
		echo ""; \
		echo "Error: bumpversion is not installed."; \
		echo ""; \
		echo "Please install it using:"; \
		echo "  pip install bump2version"; \
		echo ""; \
		exit 1; \
	}
	@BRANCH=$$(git rev-parse --abbrev-ref HEAD); \
	if [ "$$BRANCH" != "main" ]; then \
		echo "Error: You must be on the 'main' branch to release."; \
		echo "Current branch: $$BRANCH"; \
		exit 1; \
	fi; \
	CURRENT=$$(grep ^current_version .bumpversion.cfg | head -1 | cut -d= -f2 | tr -d ' '); \
	echo "Current version: $$CURRENT"; \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	MINOR=$$(echo $$CURRENT | cut -d. -f2); \
	PATCH=$$(echo $$CURRENT | cut -d. -f3); \
	if [ "$(1)" = "major" ]; then \
		NEW_VERSION=$$((MAJOR + 1)).0.0; \
	elif [ "$(1)" = "minor" ]; then \
		NEW_VERSION=$$MAJOR.$$((MINOR + 1)).0; \
	elif [ "$(1)" = "patch" ]; then \
		NEW_VERSION=$$MAJOR.$$MINOR.$$((PATCH + 1)); \
	fi; \
	echo "New version will be: $$NEW_VERSION"; \
	printf "Continue? (y/n) "; \
	read -r REPLY; \
	case "$$REPLY" in \
		[Yy]|[Yy][Ee][Ss]) \
			echo "Updating CHANGELOG.md with git-cliff..."; \
			git cliff --unreleased --tag $$NEW_VERSION --prepend CHANGELOG.md; \
			git add CHANGELOG.md; \
			git commit -m "Update CHANGELOG for $$NEW_VERSION"; \
			echo "Bumping version with bumpversion..."; \
			bumpversion --new-version $$NEW_VERSION patch; \
			echo ""; \
			echo "✓ Released version $$NEW_VERSION"; \
			echo ""; \
			echo "Next steps:"; \
			echo "  git push && git push --tags"; \
			;; \
		*) \
			echo "Release cancelled"; \
			;; \
	esac
endef

.PHONY: release-patch
release-patch: ## Release a patch version (x.x.PATCH)
	$(call do_release,patch)

.PHONY: release-minor
release-minor: ## Release a minor version (x.MINOR.0)
	$(call do_release,minor)

.PHONY: release-major
release-major: ## Release a major version (MAJOR.0.0)
	$(call do_release,major)

.PHONY: bump-patch
bump-patch: release-patch ## Alias for release-patch (deprecated, use release-patch)

.PHONY: bump-minor
bump-minor: release-minor ## Alias for release-minor (deprecated, use release-minor)

.PHONY: bump-major
bump-major: release-major ## Alias for release-major (deprecated, use release-major)

.PHONY: check
check: lint test ## Run all checks (lint and test)

.PHONY: all
all: clean format check build ## Run all tasks (clean, format, check, build)
