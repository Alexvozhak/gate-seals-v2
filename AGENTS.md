# Codex Agent Instructions

## Setup
Install dependencies using Poetry and Yarn:
```shell
poetry install
yarn
```

## Testing
Run tests on the local Hardhat network:
```shell
poetry run ape test -q
```

## Deployment
Use the scripts in `scripts/` to deploy the GateSeal blueprint and factory before creating new GateSeals.

## Pull Request Guidelines
Pull request descriptions should contain the following sections:
- **Summary** – describe the main changes.
- **Testing** – show the result of `poetry run ape test -q`.
