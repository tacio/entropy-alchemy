# Repository Guidelines

## Project Structure & Module Organization

`deck_wallet.py` contains the BIP39 conversion, payload format, and factoradic deck codec. `main.py` is a thin `encode`/`decode` CLI. Tests live in `tests/`, and the vendored English BIP39 list is `wordlists/english.txt`. Keep reusable logic out of the CLI. `.venv/`, caches, and bytecode are generated locally and must not be committed.

## Build, Test, and Development Commands

There is no packaging or build step. From the repository root, use:

- `.venv/bin/python main.py encode` — read a mnemonic and print its deck.
- `.venv/bin/python main.py decode` — read a deck and recover its mnemonic.
- `.venv/bin/python -m pytest -q` — run all tests.
- `.venv/bin/python -m compileall -q deck_wallet.py main.py tests` — check syntax.

If the virtual environment is missing, create one with `python -m venv .venv` and install development dependencies from `requirements-dev.txt`.

## Coding Style & Naming Conventions

Follow PEP 8 with four-space indentation and keep lines focused and readable. Use `snake_case` for functions and variables, `UPPER_CASE` for module constants, and descriptive `test_<behavior>` names. Add type annotations to public functions and concise docstrings that state accepted ranges and return shapes. Prefer straightforward integer operations and deterministic transformations; avoid hidden global state. No formatter or linter is currently configured, so review changes for consistent quoting and imports.

## Testing Guidelines

Use pytest. Cover official BIP39 vectors, encode/decode round trips, malformed mnemonics, card validation, metadata failures, and CLI behavior. Keep the v1 golden deck vector stable; changing it is a format migration, not a routine refactor. Add a regression test with every bug fix. No coverage threshold is configured, but new branches should be exercised.

## Commit & Pull Request Guidelines

This checkout contains no usable Git history, so no existing commit convention can be inferred. Use short, imperative subjects such as `Validate deck checksum`, and keep unrelated changes separate. Pull requests should explain behavior and format changes, list commands run and results, and link relevant issues. Never include real mnemonics, passphrases, wallet data, generated environments, or caches. Treat any payload-layout change as a versioned compatibility decision.
