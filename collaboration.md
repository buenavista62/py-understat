# Collaboration

This repository is public. Anyone may inspect the code, fork the repository, open an issue, or submit a pull request. Write access is intentionally limited.

## Main branch policy

- `main` is protected.
- Changes must arrive through a pull request; direct pushes are blocked.
- The `Owner-only main updates` ruleset allows only repository administrators to update `main`; `buenavista62` is currently the only administrator.
- Branch protection is enforced for administrators.
- The `Format, lint, type-check, and test` CI check must pass before merging.
- Force-pushes and branch deletion are disabled.
- Contributors may fork the repository, create branches, and open pull requests, but only the owner can merge into `main`.
- Do not grant repository administrator access to another account.

The repository is owned by a personal GitHub account. GitHub's branch-protection API does not support per-user push restrictions for personal repositories, so the owner-only ruleset is the control that prevents collaborators from updating `main`. Keep the ruleset active if collaborators are added.

## Development setup

Use Python 3.13 or newer and install the locked development environment:

```bash
uv sync --locked --all-groups
```

Run the same checks used by CI before opening a pull request:

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
```

## Pull requests

1. Create a focused branch from `main`.
2. Keep the change small and explain the user-visible behavior in the pull request description.
3. Add or update tests when the change introduces a new observable contract or fixes a regression.
4. Run formatting, linting, type checking, and tests locally.
5. Push the branch and open a pull request against `main`.
6. Wait for CI and resolve all review feedback before merging.

Do not commit credentials, API tokens, local virtual environments, build artifacts, or unrelated formatting changes.

## Releases

Releases are made by the repository owner from a version tag. Update the package version in `pyproject.toml` and `src/py_understat/__init__.py`, then push the tag:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

The `publish.yml` workflow runs the checks, builds the source distribution and wheel, publishes them to PyPI through trusted publishing, and creates the matching GitHub Release.
