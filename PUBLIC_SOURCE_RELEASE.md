# Public Source Release Notes

LedgerChain's public source distribution retains the project structure, frontend, API routes, data models, migrations, blockchain provider interfaces, smart-contract source, and selected tests.

## Deliberately excluded implementation

For source-protection purposes, selected core write/verification method bodies are replaced by explicit `PUBLIC_SOURCE_WORKFLOW_UNAVAILABLE` service errors. The API and UI surfaces remain available to inspect, but protected actions do not mutate state or claim success. This is intentional, not a deployment failure.

Protected areas include payment execution and ledger posting; finance write workflows; inventory mutations; asset lifecycle mutations and verification; supply-chain batch/shipment mutations; demo funding; and blockchain anchoring and verification internals. Read-only operations and supporting schemas/models remain where useful.

The production website is a separate deployed application. Do not infer that the public source archive contains every implementation used by that deployment.

## Tests

Tests that require withheld workflows are marked skipped in this distribution. Other retained tests may still require PostgreSQL, environment configuration, and installed dependencies. Run the test suite in a configured development environment before relying on results.

## Local configuration

Copy `backend/.env.example` to `backend/.env` and replace all development values locally. Never commit real secrets, private keys, credentials, or production connection strings.
