# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

pytest-infrahouse is a pytest plugin (published to PyPI) that provides Terraform fixtures for testing AWS
infrastructure. Fixtures create **real AWS resources** that cost real money; they are destroyed automatically
after tests unless `--keep-after` is passed.

## First Steps

**Your first tool call in this repository MUST be reading .claude/CODING_STANDARD.md.
Do not read any other files, search, or take any actions until you have read it.**
This contains InfraHouse's comprehensive coding standards for Terraform, Python, and general formatting rules.

Note: `.claude/CODING_STANDARD.md` is managed by Terraform in the
[github-control](https://github.com/infrahouse/github-control) repository — never edit it here.

## Commands

```bash
make install        # pip install -e .
make format         # black (py310 target) + isort on src/ and tests/, terraform fmt -recursive
make lint           # black --check + isort --check-only (what CI runs)
make test           # pytest -xvvs tests/  — creates REAL AWS infrastructure
make check          # lint + test
make build          # python -m build (cleans first)

# Run a single test file (requires AWS credentials and the terraform binary):
pytest -xvvs tests/test_service-network.py

# Common plugin options (defined in src/pytest_infrahouse/plugin.py):
pytest -xvvs tests/test_jumphost.py \
    --aws-region us-west-2 \                 # default: us-east-1
    --test-role-arn arn:aws:iam::...:role/pytest-tester \  # role to assume (optional)
    --test-role-duration 43200 \             # capped at 3600 when role chaining
    --test-zone-name ci-cd.infrahouse.com \  # Route53 parent zone for subzone/jumphost fixtures
    --keep-after                             # don't destroy resources (debugging only)
```

Releases: `make release-patch|release-minor|release-major` (requires git-cliff and bump2version, must be on
`main`; updates CHANGELOG.md, bumps version in `pyproject.toml`/`.bumpversion.cfg`/`src/pytest_infrahouse/__init__.py`,
then `git push && git push --tags`).

CI (`.github/workflows/python-CI.yml`) runs lint + `make test` on Python 3.10–3.13, assuming role
`arn:aws:iam::303467602807:role/pytest-tester` in us-west-2.

## Architecture

The plugin registers via the `pytest11` entry point in `pyproject.toml` (`infrahouse = "pytest_infrahouse.plugin"`),
so installing the package makes the fixtures available to any test suite. Three layers:

1. **`src/pytest_infrahouse/terraform.py`** — the `terraform_apply()` context manager: runs
   `terraform init/get/apply` in a module directory, yields the parsed `terraform output -json` dict, and runs
   `terraform destroy` (with retries and backoff) on exit when `destroy_after=True`. This is also exported as the
   package's public API (`from pytest_infrahouse import terraform_apply`) for testing users' own modules.

2. **`src/pytest_infrahouse/plugin.py`** — all fixtures and pytest CLI options. Infrastructure fixtures
   (session-scoped) follow one pattern: write a `terraform.tfvars` into the corresponding
   `data/<fixture-name>/` directory, then wrap `terraform_apply()` and yield the outputs. Terraform outputs are
   accessed as `output["key"]["value"]`. Also provides boto3 client fixtures and `boto3_session`, which assumes
   `--test-role-arn` with auto-refreshing credentials (role chaining caps session duration at 1 hour).

3. **`src/pytest_infrahouse/data/<fixture-name>/`** — one embedded Terraform root module per fixture
   (shipped as package data). Modules source InfraHouse modules from `registry.infrahouse.com` with exact
   version pins (managed by Renovate).

Fixture dependency graph: `jumphost` and `elasticsearch` depend on `service_network` + `subzone`; `postgres`
depends on `service_network`; `subzone` creates a Route53 zone under `--test-zone-name` and does extra
boto3-based record cleanup on teardown. `elasticsearch` applies twice (bootstrap mode, tracked via a
`.bootstrapped` flag file in the module dir).

Key operational details:

- **Terraform state lives inside the package data directories** (`src/pytest_infrahouse/data/<fixture>/` in dev,
  site-packages when installed). This is what makes `--keep-after` + a later destroy work, and why manual
  `terraform destroy` must be run from those directories.
- All test resources are tagged (e.g. `created_by_fixture = "infrahouse/pytest-infrahouse/<fixture>"`).
  To find/clean up orphaned tagged resources, use `ih-aws resources` (from infrahouse-toolkit).
  `find_tagged_resources.py` at the repo root is a leftover prototype of that command — don't use or extend it.
- Tests in `tests/` are integration tests of the fixtures themselves — there are no mocked/offline tests.