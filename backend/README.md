# LedgerChain Backend

Standalone FastAPI API for LedgerChain. The Next.js frontend uses the existing `LedgerService` boundary and a same-origin API proxy for browser mutations, while authenticated server components forward session cookies directly to the backend. Finance, inventory, shipments, assets, and blockchain evidence share the existing persisted domain records and bounded unified Activity read model; there is no separate event bus. Payments remain internal INR account transfers, not external settlement.

## Architecture

```text
Next.js UI → LedgerService → typed API client → same-origin proxy / authenticated server requests
FastAPI /api/v1 → auth/user/account/payment/activity/ledger/blockchain/product/asset routes
                 → services → repositories → SQLAlchemy → PostgreSQL
Payment + account balance changes + ledger posting → one DB transaction
BlockchainService → BlockchainProvider → backend EVM signer → LedgerAnchorRegistry
                → separate blockchain record transaction
```

Routes validate input and serialize safe DTOs. Services own business rules and commits. Repositories isolate database queries. `DbSession` provides one request-scoped session and rolls it back when a request raises.

The account balance on `organizations` remains the operational available-balance source of truth. The ledger is a double-entry audit record, not an independently maintained balance and not an event-sourcing system.

## Stack and structure

Python 3.12+, FastAPI, SQLAlchemy 2.x, PostgreSQL/psycopg 3, Alembic, Pydantic Settings, Argon2id, web3.py, pytest, and eth-tester for local EVM integration tests. Solidity compiles with solc-js 0.8.37 and OpenZeppelin Contracts 5.6.1.

```text
backend/
├── app/
│   ├── api/v1/                       # auth, accounts, finance, inventory, shipment, asset, activity, blockchain
│   ├── core/                          # config, standardized errors, middleware, auth limits
│   ├── db/                            # SQLAlchemy engine, sessions, metadata
│   ├── models/                        # auth, organization, finance, inventory, shipment, asset, ledger, evidence
│   ├── repositories/                  # scoped persistence and bounded read queries
│   ├── services/                      # business transitions, unified Activity, blockchain rules
│   ├── blockchain/                    # provider protocol, simulator, and EVM provider
│   └── schemas/                       # validated input and safe response DTOs
├── contracts/                         # Solidity source, compiler script, and ABI/bytecode artifact
├── migrations/versions/               # Alembic revisions 0001–0013
└── tests/                              # Backend regression suite, including local EVM tests
```

## Environment and local development

Run commands from `backend/`:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
pip install -r requirements-dev.txt
cp .env.example .env               # optional for local development
uvicorn app.main:app --reload --port 8000
```

Settings use the `LEDGERCHAIN_` prefix and read environment variables, then `backend/.env`. Production rejects the default database URL and default secret. `LEDGERCHAIN_CORS_ORIGINS` is a comma-separated exact-origin allowlist and defaults to `http://localhost:3000`.

## Authentication and account APIs

All API routes require an authenticated, active, email-verified user where noted. Passwords use Argon2id; opaque session/action tokens are persisted as SHA-256 digests. Cookie-authenticated writes use the existing double-submit CSRF header/cookie pair (`X-CSRF-Token`) and exact-origin allowlist. Auth secrets and raw tokens are never exposed by profile APIs. Email provider delivery is not configured.

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | Create user, default organization/owner membership, settings and preferences |
| POST | `/api/v1/auth/login` | Authenticate and issue persisted session/CSRF cookies |
| POST | `/api/v1/auth/logout` | CSRF-protected session revocation |
| GET | `/api/v1/auth/me` | Return safe current-user auth fields |
| POST | `/api/v1/auth/verify-email` | Consume email verification token |
| POST | `/api/v1/auth/forgot-password` | Uniform password reset response |
| POST | `/api/v1/auth/reset-password` | Consume a reset token and revoke sessions |
| GET/PATCH | `/api/v1/users/me` | Read/update safe profile fields; email is read-only |
| GET/PATCH | `/api/v1/account` | Read organization account; owner-only organization changes |
| GET/PATCH | `/api/v1/users/me/settings` | Read/update current user's preferences |
| GET/PATCH | `/api/v1/users/me/notifications` | Read/update notification preferences |

## Payment API

All payment records represent internal transfers between LedgerChain organization accounts; they are not external bank settlement. Accounts have unique 18-digit numbers and exact `NUMERIC(18,2)` INR balances. New and migrated balances start at `0.00`; the separate demo-funding endpoint is explicitly simulated, idempotent, and never contacts a bank. Fees are currently fixed at `0.00`.

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/api/v1/payments` | Create internal payment; authenticated, CSRF/origin protected, requires `Idempotency-Key` |
| GET | `/api/v1/payments/{payment_id}` | Read payment as sender or participating organization member |
| GET | `/api/v1/payments?limit=20&offset=0` | Bounded paginated list visible to current user |

The amount is a decimal JSON **string**, not a JSON float. The payment service locks sender/recipient organizations in stable ID order, checks balance and account limits, updates both balances, completes the payment, and posts its ledger within one SQLAlchemy transaction. Any failure rolls everything back. Module 5's persisted idempotency key is scoped to sender organization; same-payload retries return the original payment and conflicting reuse returns `IDEMPOTENCY_CONFLICT`.

## Activity & ledger engine

Payments, ledger, and Activity are separate concepts:

```text
Payment = business transfer record
LedgerTransaction = accounting record linked one-to-one to a payment
LedgerEntry = individual posting against an organization account
Activity = chronological read model of persisted payment, finance, inventory, shipment, asset, and blockchain records
```

A completed payment writes a sender debit and recipient credit. The exact debit and credit totals must match the ledger transaction amount. Module 5 currently charges zero fees; nonzero fees cannot be introduced without defining a corresponding fee/clearing account. Organization balances remain the spendable balance source; ledger entries are not replayed to calculate balances.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/api/v1/activity?limit=20&offset=0&type=payment` | Chronological payment activity |
| GET | `/api/v1/activity?limit=20&offset=0&type=finance` | Persisted payment-request transitions and budget creation |
| GET | `/api/v1/activity?limit=20&offset=0&type=shipment` | Persisted shipment transitions |
| GET | `/api/v1/activity?limit=20&offset=0&type=inventory` | Persisted inventory movements |
| GET | `/api/v1/activity?limit=20&offset=0&type=asset` | Persisted asset provenance events |
| GET | `/api/v1/activity?limit=20&offset=0&type=blockchain` | Existing blockchain evidence records |
| GET | `/api/v1/ledger/{transaction_id}` | Read posted transaction and debit/credit entries |

All Activity filters share the same bounded pagination and chronological merge. Reads require authentication, are scoped to organization membership or transaction participation, return no-store responses, and conceal unauthorized IDs as not found. Each item describes persisted application state; the read model does not fabricate verification or budget-transition events. Ledger data is read-only; there are no generic ledger mutation endpoints.

## Finance workflows

Finance budgets and payment requests are persisted under the requesting organization. Requests record append-only, sequence-numbered status transitions; authorized approvers can approve or reject a submitted request, and execution checks the associated budget before creating the internal payment and ledger posting. Budget creation appears in Activity from the persisted budget record; no synthetic events are created for budget recalculation.

| Method | Path | Behavior |
| --- | --- | --- |
| GET/POST | `/api/v1/finance/budgets` | List bounded budgets or create an organization budget |
| GET/POST | `/api/v1/finance/payment-requests` | List requests or create an idempotent payment request |
| POST | `/api/v1/finance/payment-requests/{id}/submit` | Submit a draft request |
| POST | `/api/v1/finance/payment-requests/{id}/approve` | Approve as an authorized organization member |
| POST | `/api/v1/finance/payment-requests/{id}/reject` | Reject with a persisted decision |
| POST | `/api/v1/finance/payment-requests/{id}/execute` | Budget-check and execute the internal payment/ledger flow |
| GET | `/api/v1/finance/payment-requests/{id}/history` | Read the request's immutable status history |

## Supply chain and inventory

Products, lots/batches, stock movements, shipments, and shipment transitions use the existing organization-scoped records. Shipment transitions update stock and append immutable events in the same transaction. The unified Activity feed reads those persisted shipment and inventory rows; shipment evidence is anchored explicitly, not automatically.

| Method | Path | Behavior |
| --- | --- | --- |
| GET/POST | `/api/v1/inventory/batches` | List or create product lots |
| GET/POST | `/api/v1/inventory/shipments` | List or create organization-scoped shipments |
| POST | `/api/v1/inventory/shipments/{id}/dispatch` | Dispatch and transfer the batch quantity |
| POST | `/api/v1/inventory/shipments/{id}/transit` | Record an in-transit transition |
| POST | `/api/v1/inventory/shipments/{id}/receive` | Receive and reconcile the shipment quantity |
| POST | `/api/v1/inventory/shipments/{id}/reject` | Record a rejection and handle stock return |
| GET | `/api/v1/inventory/stocks?limit=20&offset=0` | List bounded stock state for member organizations |
| GET | `/api/v1/inventory/movements?limit=20&offset=0` | Read immutable inventory movement history |

### Append-only and consistency guarantees

Migration `0005` adds `ledger_transactions` and `ledger_entries`, foreign keys to the existing `payments` and `organizations`, exact numeric amounts, positive-amount/direction/currency/status/type checks, a unique payment-to-ledger relationship, and history indexes. It backfills existing completed Module 5 payments before enforcing the new ledger flow. PostgreSQL deferred triggers validate at commit that posted transactions have at least one debit and credit, equal totals matching the transaction amount, and that completed payments have a posted ledger transaction. Posted entries/transactions and completed payments cannot be updated/deleted; entries cannot be appended to a posted transaction. No reversal system is included.

SQLite migrations install immediate triggers for balance and immutability checks; service-level transaction rollback and API tests cover the same payment-ledger atomicity behavior. Module 7's `0006` and Module 8's `0007` blockchain migrations were exercised on SQLite. SQLite does not prove PostgreSQL deferred-trigger or concurrency behavior.

## Blockchain evidence anchoring and verification

```text
Posted LedgerTransaction → unchanged ledgerchain-ledger-v1 canonical bytes
                         → SHA-256 → BlockchainService → BlockchainProvider
                         → EVM relayer → LedgerAnchorRegistry → configured EVM network
```

Only an authorized participant can anchor a posted ledger transaction through the API. The existing `ledgerchain-ledger-v1` representation and SHA-256 calculation are unchanged: it includes ledger reference/ID/type/amount/currency/posting time and sorted debit/credit amount/currency lines, while excluding account IDs, notes, descriptions, names, and personal details. The provider receives the digest and ledger UUID only, never the full ledger row.

### Contract

`contracts/src/LedgerAnchorRegistry.sol` is Solidity **0.8.37**, contract version **1.0.0**, using OpenZeppelin Contracts **5.6.1** `Ownable`. The owner controls authorized submitter addresses. Each new anchor stores a `bytes32` digest, a padded ledger UUID reference, block timestamp, and submitting address; `RecordAnchored` emits those non-sensitive fields. `verifyRecord` and `getAnchor` are read-only. Zero values, unauthorized submitters, a reused reference with a different digest, and a digest associated with a different reference are rejected. Repeating the exact digest/reference is a safe no-op (no second event); the application database also remains unique per ledger transaction.

Compile the ABI/bytecode artifact from the repository root with `pnpm contracts:compile`. The script pins the compiler version, optimizer and EVM target; the committed artifact records compiler version and source hash. The Python integration loads that artifact only inside the blockchain provider layer.

### EVM provider and transaction lifecycle

`BlockchainProvider` exposes anchor, transaction lookup, on-chain lookup, and health operations. `DevelopmentBlockchainProvider` remains explicit simulation with no fabricated hashes. `EVMBlockchainProvider` signs transactions in the backend only, verifies configured chain ID and contract version/bytecode, verifies relayer authorization, polls actual receipts, and records transaction hash, mined block/time, contract address and version. `LEDGERCHAIN_BLOCKCHAIN_CONFIRMATION_DEPTH` defaults to one mined block; increase it when the configured network requires more confirmations. Mined reverts become terminal `failed` records. RPC/submission failures remain safely sanitized and retryable through the existing record idempotency key; they do not change payment/ledger state.

### API and verification

All routes remain authenticated, participant-scoped, and `Cache-Control: no-store`. Writes use the existing CSRF/origin protection; there is no raw transaction or arbitrary contract-call endpoint.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/api/v1/blockchain/status` | Provider/network/contract health |
| POST | `/api/v1/blockchain/ledger/{ledger_transaction_id}/anchor` | Submit the authorized posted-ledger digest |
| POST | `/api/v1/assets/{asset_id}/history/{event_id}/anchor` | Anchor authorized asset provenance through the same provider |
| POST | `/api/v1/blockchain/shipments/{shipment_id}/events/{event_id}/anchor` | Anchor authorized shipment evidence through the same provider |
| GET | `/api/v1/blockchain/transactions/{record_id}` | Read anchor record and refresh pending receipt state |
| GET | `/api/v1/blockchain/ledger/{ledger_transaction_id}/verify` | Recompute and verify the canonical ledger digest |
| GET | `/api/v1/blockchain/shipments/{shipment_id}/events/{event_id}/verify` | Check shipment history and verify its optional evidence anchor |

Ledger verification returns `ANCHORED_MATCH`, `ANCHORED_MISMATCH`, `NOT_ANCHORED`, or `CONFIRMATION_PENDING`; shipment verification also distinguishes `SIMULATED` and `VERIFICATION_UNAVAILABLE`. Shipment events use deterministic `ledgerchain-shipment-event-v1` canonical evidence and SHA-256 through the same `BlockchainService → BlockchainProvider → EVM/Development Provider → LedgerAnchorRegistry` path as ledger and asset evidence. Responses separately identify the application record, internal immutable event, anchor record, and confirmation state. Development anchors are explicitly `simulated` and never include fabricated transaction hashes or block numbers. A mismatch is an integrity warning; an anchor proves only that a digest/reference was recorded on-chain, not that source data was truthful, a user legitimate, or a payment legally authorized.

### Network and secrets

Provider, network, chain ID, RPC URL, signer private key, contract address/version, RPC timeout, and confirmation depth use `LEDGERCHAIN_` settings. The configurable EVM testnet strategy documents Ethereum Sepolia (chain ID `11155111`) as the application-development target. Configure `LEDGERCHAIN_BLOCKCHAIN_PROVIDER=evm` only after deploying `LedgerAnchorRegistry` and supplying the actual chain ID/address, an HTTPS RPC URL in production, and a dedicated backend relayer key through secret configuration. No RPC credentials, signer key, or deployed contract address were available here: **deployment and live testnet transactions were not performed**. The default stays `development`; no address or transaction hash is claimed. The backend relayer is responsible for gas; gas is never charged to LedgerChain's internal INR account.

Nonce locking is process-local; a multi-process/multi-instance production deployment needs shared nonce coordination. Receipt-depth confirmations do not eliminate deep-reorganization risk. The contract is not upgradeable, and contract admin/key rotation remains an operational responsibility.

## Migrations

- `0001`–`0008` — baseline, auth/accounts/payments, ledger, blockchain metadata, products/assets, and immutable provenance.
- `0009` — persisted simulated demo funding.
- `0010` — organization-scoped inventory movements and stock.
- `0011` — budgets and payment-request approval history.
- `0012` — product batches and auditable inventory shipments.
- `0013` — shipment-event references on the existing blockchain evidence records.

Apply when PostgreSQL is reachable:

```bash
alembic upgrade head
```

Generate PostgreSQL SQL without applying it:

```bash
alembic upgrade head --sql
```

Offline SQL generation does not apply the migration or validate server-side trigger execution. `Base.metadata` imports all models for Alembic autogenerate.

## Supply Chain and Assets

Products are organization-scoped catalog records identified by a SKU unique within that organization. Assets are individually identified records optionally linked to a product; the registering organization remains the origin while `current_owner_organization_id` tracks domain ownership. A `NULL` current custodian means the owner retains custody; a different organization ID represents a separate custodian. These are application organizations, not wallets.

`asset_events` is an append-only, sequence-numbered provenance log. Registration, transfer, custody change, and retirement store actor/organization IDs, previous/resulting state snapshots, and bounded metadata. `asset_ownerships` adds one immutable ownership fact for initial registration and each transfer. Current state changes and their event/ownership rows commit in one transaction. Active assets may transfer or change custody; retired assets cannot be transferred or have custody changed. Owner-role members of the current owner organization authorize transfers, custody changes, and retirement. Transfer and custody requests resolve the recipient's active organization by its account number, reject invalid/inactive recipients, and record the account-number reference in append-only event metadata. Ownership and custody remain distinct: transferring ownership does not silently change custody. Product/asset reads are limited to member organizations connected to the product or asset origin/current owner/current custodian; hidden IDs return not found. Cookie-authenticated writes require the existing CSRF token and allowed-origin protections. State-changing asset operations require an `Idempotency-Key`; duplicate keys replay the original event for the same actor organization, while conflicting payload reuse is rejected.

JSON metadata is limited to 8 KB and must be JSON-serializable. It is returned to authorized organization members; do not store secrets or unnecessary personal/sensitive data in it. No update/delete API exists for provenance or ownership facts. SQLite/PostgreSQL migration triggers reject update/delete of those rows. Verification checks event sequence/state continuity, ownership rows, and the current asset state. It distinguishes application consistency from blockchain status; neither an internally consistent app record nor a digest anchor proves the real-world truth or authenticity of the asset.

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/api/v1/products` | Create a product in a member organization (CSRF/origin protected) |
| GET | `/api/v1/products?limit=20&offset=0` | Paginated products in organizations the user belongs to |
| GET | `/api/v1/products/{product_id}` | Read an organization-scoped product |
| POST | `/api/v1/assets` | Register asset, initial ownership fact, and `REGISTERED` provenance event atomically |
| GET | `/api/v1/assets?limit=20&offset=0` | Paginated assets visible through origin, owner, or custodian membership |
| GET | `/api/v1/assets/{asset_id}` | Read current asset state |
| POST | `/api/v1/assets/{asset_id}/transfer` | Owner-authorized ownership transfer with required idempotency key |
| POST | `/api/v1/assets/{asset_id}/custody` | Owner-authorized custody change with required idempotency key |
| POST | `/api/v1/assets/{asset_id}/retire` | Owner-authorized irreversible retirement |
| GET | `/api/v1/assets/{asset_id}/history` | Read ordered provenance events |
| GET | `/api/v1/assets/{asset_id}/ownership` | Read immutable ownership facts in event order |
| GET | `/api/v1/assets/{asset_id}/verify` | Check current/history consistency and any explicitly created asset-event anchor |
| POST | `/api/v1/assets/{asset_id}/history/{event_id}/anchor` | Anchor an authorized event through the existing blockchain provider/registry |

Asset-event anchoring extends `blockchain_records` with an exclusive ledger-transaction-or-asset-event reference; it does not introduce another provider or contract. The existing `ledgerchain-ledger-v1` digest is unchanged. Asset events use `ledgerchain-asset-event-v1`, covering stable IDs, sequence, event type, timestamp, and state snapshots while excluding freeform metadata and user ID. Anchoring is explicit, and the development provider remains `simulated` with no real transaction hash/block. Reports call it `NOT_ANCHORED`; only a confirmed digest/reference that matches the provider is `ANCHORED_MATCH`. A chain proves a digest/reference was recorded, not that an asset exists or is genuine in the real world. Asset events are not automatically posted to the financial ledger; future payment-backed transfers must explicitly link a separate payment/ledger operation.

## Tests and verification limits

Run the full backend suite from `backend/`:

```bash
pytest
```

The full backend pytest suite passes, including finance, shipment, asset, authorization/isolation, idempotency, evidence, migration, and local-EVM/provider tests. `python -m compileall -q app` and PostgreSQL offline SQL generation through the current Alembic head `0013` pass. Frontend checks completed with `pnpm exec tsc --noEmit` and `pnpm build`. Browser verification confirmed that `/activity` is protected and routes unauthenticated users to sign-in; no test credentials were available, so authenticated browser journeys were not performed.

Docker and a live PostgreSQL server/client are unavailable in this environment. PostgreSQL migration application, deferred trigger execution, actual PostgreSQL locking/concurrency, and production performance remain unverified. The offline `alembic upgrade head --sql` check is not a substitute for runtime verification. Starlette `TestClient` and websockets emit upstream deprecation warnings; tests pass.

## Security and scope boundary

Authentication and CSRF/origin protection reuse Module 3 dependencies. Ledger and activity reads authorize sender identity or current organization membership rather than relying on unguessable IDs. DTOs do not expose raw ORM records or unrelated parties' records. Completed ledger history has no mutation route and is guarded in the migration. Account balance checks and row-locking remain Module 5 behavior.

A Vercel preview validates the Next.js deployment, not the separately deployed FastAPI service, PostgreSQL schema, or public-chain transaction path. No real testnet RPC, relayer key, contract address, or on-chain transaction was available or verified; local EthereumTester coverage passes. PostgreSQL migration application remains a separate deployment step. Email delivery, wallet custody, tokens, crypto payments, external bank settlement, external gateways, full ERP, warehouse management, distributed workers, and multi-chain support are not implemented. PostgreSQL migration application, production concurrency behavior, and authenticated browser journeys remain unverified here. Security overview/password-change/session-revocation and support-ticket endpoints are intentionally not exposed; notification preferences persist, but there is no notification feed/delivery API.
