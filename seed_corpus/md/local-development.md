# Local Development Guide

## Requirements

Use Python 3.11 or newer for the sample worker. Create an isolated environment and install the pinned dependencies from `requirements-dev.txt`. Do not use production API keys in local development.

## Start the sandbox

1. Run `relayctl dev up` to start the local API, queue emulator, and worker.
2. The mock REST API listens at `http://127.0.0.1:8088`.
3. The webhook inspector listens at `http://127.0.0.1:8099`.
4. Set `NORTHSTAR_API_KEY` to a sandbox key beginning with `ns_test_`.
5. Submit a sample job and inspect its lifecycle in the local dashboard.

## Test failure handling

The queue emulator supports a deterministic fault profile named `flaky-3`, which fails the first three worker attempts before succeeding. The `dead-letter-9` profile simulates a job that fails beyond the eight-attempt limit and produces `DLQ-17`. These are local test fixtures, not production server modes.

## Clean up

Use `relayctl dev down` to stop the services and remove temporary containers. The command preserves the local fixture directory unless `--purge-fixtures` is specified. Never commit `.env` files, access tokens, generated payloads, or local delivery logs.
