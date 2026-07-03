# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## First Steps

**Your first tool call in this repository MUST be reading .claude/CODING_STANDARD.md.
Do not read any other files, search, or take any actions until you have read it.**
This contains InfraHouse's comprehensive coding standards for Terraform, Python, and general formatting rules.

## What this is

`pytest-infrahouse` is a **pytest plugin** (published to PyPI, one of many InfraHouse projects) that
provides fixtures for testing AWS infrastructure / Terraform modules. Consumers `pip install` it and get
session-scoped fixtures that spin up **real AWS resources** via embedded Terraform configurations, yield their
outputs to the test, and destroy them on teardown. It is registered as a pytest plugin through the
`project.entry-points.pytest11` entry point (`infrahouse = "pytest_infrahouse.plugin"`) in `pyproject.toml`.

Because fixtures create real AWS resources, the "tests" in `tests/` are effectively **integration tests** that
require AWS credentials and cost money/time to run. They are not fast unit tests.

## Commands

```bash
make help            # list all targets (default goal)
make install-dev     # editable install with dev deps  (pip install -e '.[dev]')
make format          # black + isort + terraform fmt -recursive
make lint            # black --check + isort --check-only  (CI runs exactly this)
make test            # pytest -xvvs tests/  (creates real AWS resources)
make check           # lint + test
make build           # clean + python -m build
```

Run a single test / pass through options (the plugin's CLI options come from `pytest_addoption`):

```bash
pytest -xvvs tests/test_jumphost.py
pytest -xvvs tests/test_jumphost.py::test_jumphost
pytest -xvvs tests/test_jumphost.py --keep-after            # don't destroy resources (debug)
pytest -xvvs tests/ --test-role-arn arn:aws:iam::…:role/… --aws-region us-west-2
```

Key pytest options this plugin adds: `--keep-after`, `--test-role-arn`, `--test-role-duration`,
`--test-zone-name` (default `ci-cd.infrahouse.com`), `--aws-region` (default `us-east-1`).

CI (`.github/workflows/python-CI.yml`) runs `black --check`/`isort --check-only` then `make test` across Python
3.10–3.13 on a role with a 12h session; region is `us-west-2`.

## Architecture

Three layers:

1. **`plugin.py`** — the pytest entry point. Defines `pytest_addoption` and every fixture. Fixtures fall into
   two kinds:
   - **boto3 client fixtures** — `boto3_session` (session-scoped) plus per-service clients (`ec2_client`,
     `route53_client`, `iam_client`, etc.). `boto3_session` is the important one: if `--test-role-arn` is set it
     builds a session with **auto-refreshing** STS credentials (`RefreshableCredentials`) so long tests survive
     past the 1h role-chaining cap. It detects credential chaining (`:assumed-role/` in the caller ARN) and caps
     `DurationSeconds` at 3600 accordingly.
   - **Terraform fixtures** — `service_network`, `instance_profile`, `jumphost`, `elasticsearch`, `postgres`,
     `ses`, `probe_role`, `subzone`. Each resolves its embedded module directory, writes a `terraform.tfvars`
     from fixture params, and wraps `terraform_apply(...)` to yield the module's JSON outputs. Fixtures compose:
     e.g. `jumphost` depends on `service_network` + `subzone`, reading subnet IDs / zone ID from the upstream
     fixture's outputs.

2. **`terraform.py`** — the Terraform runner. `terraform_apply` is a `@contextmanager` that runs
   `init → get → apply`, yields `terraform output -json` parsed to a dict, and on exit runs `destroy` (unless
   `destroy_after=False`). `destroy` uses `run_with_retries` (5 attempts, linear backoff) because teardown is
   flaky. `enable_trace=True` sets `TF_LOG=JSON` and writes `tf-apply-trace.txt` / `tf-destroy-trace.txt`.

3. **`data/<name>/`** — embedded Terraform modules, one per fixture, shipped as package data (see
   `[tool.setuptools.package-data]`). They are located at runtime via `importlib.resources`
   (`files("pytest_infrahouse").joinpath("data/…")`), NOT relative paths — this is what lets the modules work
   when installed as a wheel. `utils.py` holds AWS helpers used by consumer tests (e.g.
   `wait_for_instance_refresh`).

### Conventions that matter

- **Fixture ↔ module directory ↔ tfvars**: to add a new Terraform fixture, add `data/<name>/` (with
  `main.tf`, `variables.tf`, `outputs.tf`, etc.), then a session-scoped fixture in `plugin.py` that writes
  `terraform.tfvars` and yields `terraform_apply(module_dir, destroy_after=not keep_after, json_output=True)`.
  Always thread through `region`, `calling_test` (the requesting test's filename), and `role_arn` when
  `--test-role-arn` is set — every existing fixture does this.
- **`--keep-after` must be honored** in any teardown you add (see `subzone`'s manual Route53 cleanup and
  `cluster_bootstrapped`/`.bootstrapped` flag logic in `elasticsearch` for examples of custom teardown).
- Test resources are tagged `created_by_fixture` = `infrahouse/pytest-infrahouse/<fixture>` per the InfraHouse
  standard.

## Coding standards

`.claude/CODING_STANDARD.md` is the authoritative, org-wide standard (**managed centrally by the
github-control repo — do not edit it here; changes get overwritten**). Highlights that apply to this repo:

- **120-char max line length**; all files end with a newline.
- Python: format with **Black** (`--target-version py310`) + **isort**; RST/Sphinx docstrings; type hints on
  functions. **Never** `except Exception: pass` — catch specific exceptions or let it crash; signal errors via
  exceptions, not boolean/tuple return values.
- Pin dependencies to a major version with `~=` (see `pyproject.toml`).
- Terraform in `data/` modules: snake_case names, explicit variable `type`s, exact version pinning for modules
  (Renovate manages bumps), use `registry.infrahouse.com` for InfraHouse modules.

## Releases

Version is bumped via **bump2version** (`.bumpversion.cfg` keeps `pyproject.toml`, `__init__.py`, `README.rst`,
etc. in sync) and changelog generated by **git-cliff**. Use `make release-patch|release-minor|release-major`
(must be on `main`; prompts for confirmation, then instructs you to `git push && git push --tags`). Don't hand-
edit version strings.
