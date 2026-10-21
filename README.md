# LedgerChain

**A full-stack business ledger, internal payments, inventory, asset provenance, and blockchain-evidence platform.**

LedgerChain brings organization-scoped financial workflows and supply-chain traceability into one application. The repository includes the Next.js frontend, FastAPI backend, PostgreSQL persistence layer, Alembic migrations, backend regression tests, and Solidity evidence registry source.

> **Scope and demo disclaimer:** LedgerChain's payment records represent internal transfers between LedgerChain organization accounts; they are not bank transfers or external settlement. Demo funding is simulated. The default development blockchain provider simulates anchoring and does not create real transactions. An EVM provider and contract source are included, but a live public-network deployment is not implied by this repository.

## Features

- **Organization-scoped accounts and internal transfers** with exact decimal INR amounts, idempotency protection, and transactional balance/payment updates.
- **Double-entry ledger** with debit/credit postings, consistency checks, and append-only protections for posted records.
- **Finance workflows** for budgets and payment requests, including submission, approval/rejection, execution, and request history.
- **Inventory and supply chain** with products, batches, stock movements, shipments, and shipment lifecycle transitions.
- **Asset provenance** with ownership/custody history and recorded lifecycle events.
- **Unified Activity timeline** combining persisted financial, inventory, shipment, asset, and blockchain-evidence records.
- **Blockchain evidence anchoring** through a provider boundary, a development simulator, an EVM provider, and the `LedgerAnchorRegistry` Solidity contract.
- **Authentication and request protections** including Argon2id password hashing, persisted sessions, organization authorization, CSRF/origin checks, and rate limiting.
- **Regression tests and database migrations** for the backend's domain and persistence behavior.

The list describes functionality represented in this source tree; it is not a claim that every optional integration is deployed or externally audited.

## Architecture

```text
Browser
  └── Next.js App Router UI
       └── same-origin API proxy / authenticated server requests
            └── FastAPI REST API (/api/v1)
                 ├── authentication and authorization
                 ├── domain services
                 ├── repositories and SQLAlchemy models
                 └── PostgreSQL

Posted ledger transaction
  └── canonical evidence digest
       └── BlockchainService → BlockchainProvider
            ├── Development provider (simulation)
            └── EVM provider → LedgerAnchorRegistry.sol
```

### Main technologies

| Layer | Technologies |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS |
| Backend API | Python, FastAPI, Pydantic |
| Persistence | PostgreSQL, SQLAlchemy, Alembic |
| Security | Argon2id password hashing, persisted sessions, CSRF/origin validation, rate limits |
| Blockchain | Solidity, OpenZeppelin, web3.py, solc-js |
| Tests | pytest and backend regression/integration tests |

## Repository layout

```text
app/                         Next.js App Router pages and layouts
components/                  Shared UI components
lib/                         Frontend API, service, and validation boundaries
public/                      Static assets
backend/
  app/api/                   Versioned FastAPI routes
  app/core/                  Configuration, middleware, and security utilities
  app/db/                    Database engine and session management
  app/models/                SQLAlchemy domain models
  app/repositories/          Persistence queries
  app/services/              Business rules and workflows
  app/blockchain/            Provider abstraction, simulator, EVM integration
  app/schemas/               Request validation and response DTOs
  contracts/                 Solidity contract and compilation script
  migrations/                Alembic migration history
  tests/                     Backend tests
```

## Run locally

### Requirements

- Node.js compatible with the installed Next.js version
- pnpm (the repository pins its package-manager version in `package.json`)
- Python 3.12+
- Docker Compose for the included PostgreSQL + API development environment, or a separately running PostgreSQL instance

### 1. Start the backend and PostgreSQL

From the repository root:

```bash
cd backend
cp .env.example .env
# Review backend/.env and change local credentials if needed.
docker compose up --build
```

The API is exposed on `http://localhost:8000`. The Compose configuration is for local development, not production deployment. If port 5432 or 8000 is already in use, adjust the local configuration before starting.

### 2. Start the frontend

In a second terminal, from the repository root:

```bash
pnpm install --frozen-lockfile
pnpm dev
```

Open `http://localhost:3000`. The frontend uses the configured backend origin; see the API proxy configuration and `backend/README.md` for environment and deployment details.

### 3. Run checks

Frontend TypeScript check:

```bash
pnpm exec tsc --noEmit
```

Backend tests (from `backend/`, after installing development requirements and configuring a test database as needed):

```bash
python -m pip install -r requirements-dev.txt
pytest
```

Compile the Solidity contract from the repository root:

```bash
pnpm contracts:compile
```

See [`backend/README.md`](backend/README.md) for the API reference, environment settings, persistence details, migration notes, and blockchain configuration.

## Security and configuration

- Never commit `.env`, real database credentials, session secrets, RPC credentials, private keys, or production tokens.
- `backend/.env.example` contains local-development placeholders only. Generate a unique secret and set production values through the deployment environment.
- The development blockchain provider is a simulator. To use an EVM network, configure a dedicated relayer key, RPC endpoint, contract address, chain ID, and network-specific settings outside source control.
- A blockchain digest can establish that anchored evidence bytes match a prior digest; it does not establish that the original business data was truthful.
- Review the deployment configuration and run the full test suite before using the application with real users or sensitive data.

## Current boundaries

- Internal organization-to-organization transfers only; no bank rails, external settlement, or custody of real money.
- Demo funding is simulated.
- Email delivery and some account-management integrations may require additional provider configuration; consult `backend/README.md`.
- The repository includes EVM integration code, but no public-network deployment or third-party security audit is asserted here.

## Contributing

Issues and pull requests are welcome. Please include the reason for a change, steps to reproduce bugs, and tests for behavior changes. Avoid posting secrets, private customer data, or exploit details in public issues; follow [`SECURITY.md`](SECURITY.md) for security reports.

## License

No license file is included in this release. Before treating this project as open source or inviting reuse beyond viewing and collaboration, choose and add a license that reflects the team's intent and ownership.
