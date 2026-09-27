# EscrowX

Decentralized freelancer escrow on **Base Sepolia**. Clients fund milestone payments in USDC, freelancers submit proof of work, and funds are released on approval, after a review timeout, or after an AI-assisted dispute ruling.

> **Status: Phase 0 (scaffolding).** Nothing from this rebuild is deployed yet. Sections marked _(planned)_ describe the target design. The source of truth for contract behavior will be [`SPEC.md`](SPEC.md) once it lands.

## How it works

| Step | What happens |
|---|---|
| **Fund** | The client deposits USDC into an escrow contract, per milestone |
| **Submit** | The freelancer submits proof of work (stored on IPFS) |
| **Approve** | The client approves, and payment is released immediately |
| **Timeout** | If the client stays silent past the review period, the freelancer can claim payment |
| **Dispute** | Either party can dispute a submitted milestone. An off-chain AI arbitrator rules using both parties' evidence |

Dispute routing is confidence-based: a high-confidence ruling opens an appeal window, and a low-confidence ruling goes straight to a secondary review. Exact thresholds, deadlines and appeal rules are defined in `SPEC.md`.

Milestone lifecycle:

```
PENDING -> FUNDED -> SUBMITTED -> RELEASED
                        |
                        v
                    DISPUTED -> RELEASED | REFUNDED

PENDING / FUNDED -> CANCELLED (before submission)
```

## Architecture

| Layer | Technology |
|---|---|
| Smart contracts | Vyper 0.4.3 |
| Contract tests | pytest + Titanoboa |
| Chain | Base Sepolia (chain ID `84532`) |
| Payment token | Circle testnet USDC |
| Frontend | React, Vite, Tailwind CSS, wagmi + viem |
| Backend | Node.js, Express, MongoDB (TypeScript) |
| AI arbitrator | Node.js worker calling Google Gemini |
| Evidence storage | IPFS via Pinata (uploads proxied by the backend, so the JWT never reaches the browser) |
| RPC | Alchemy (free tier) |

The chain is the source of truth for amounts, statuses and parties. MongoDB stores only what the chain cannot: job descriptions, profiles, and an index of on-chain events.

**Network details**

| | |
|---|---|
| Chain ID | `84532` |
| USDC | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` |
| Explorer | https://sepolia.basescan.org |
| Deployed addresses | [`deployments/base-sepolia.json`](deployments/base-sepolia.json) |

## Repository layout _(planned)_

```
escrow-system/
├── SPEC.md            State machine, functions, events, scenarios (contract source of truth)
├── contracts/         Vyper contracts and the frozen ABI
├── tests/             pytest + Titanoboa
├── scripts/           Deploy and live-scenario tooling (TypeScript + viem)
├── backend/           Express + MongoDB API, IPFS proxy, event indexer
├── arbitrator/        AI arbitrator worker (Gemini)
├── frontend/          React app
├── deployments/       Deployed addresses per network
├── docs/              Limitations, live test results, key handling, demo script
└── .github/           CI and CODEOWNERS
```

## Team and ownership

| Role | Owns | GitHub |
|---|---|---|
| **A** Frontend core + AI arbitrator | `frontend/` (core), `arbitrator/` | @TBD |
| **B** Backend + web screens | `backend/`, some screens in `frontend/` | @TBD |
| **C** Smart contracts + spec | `contracts/`, `tests/`, `SPEC.md` | @TBD |
| **D** Chain integration + DevOps | `scripts/`, `deployments/`, `.github/`, `frontend/src/chain/viem.ts` | @TBD |

Cross-reviews: A and B review each other, C and D review each other. The full duty list per role lives in the team planning notes.

## Prerequisites

- Git
- Node.js 22 LTS (20.19+ works)
- Python 3.11 or 3.12
- MetaMask, for using the app on Base Sepolia
- Free accounts: Alchemy, Pinata, MongoDB Atlas (or a local MongoDB), Google AI Studio (Gemini key)

## Setup

Commands are for PowerShell. Each package has its own `.env.example`; copy it to `.env` and fill it in.

```powershell
git clone https://github.com/<org>/escrow-system.git
cd escrow-system
```

| Package | Quick start | Status |
|---|---|---|
| `scripts/` | `cd scripts; npm ci; copy .env.example .env; npm run check` | in progress |
| `contracts/`, `tests/` | `python -m venv venv; venv\Scripts\Activate.ps1; pip install -r requirements.txt; pytest` | planned |
| `backend/` | `cd backend; npm ci; copy .env.example .env; npm run dev` | in progress |
| `arbitrator/` | `cd arbitrator; npm ci; copy .env.example .env; npm run dev` | planned |
| `frontend/` | `cd frontend; npm ci; npm run dev` | planned |

Always confirm `(venv)` appears in your prompt before running `pip install`, so packages don't install system-wide.

## Secrets

- `.env` files are never committed. `.gitignore` blocks them, and only `.env.example` files are tracked.
- Testnet keys are still credentials. Never reuse a key that controls real funds.
- No secret ever appears under `frontend/`.
- Share keys through a password manager, never through git or chat.

Details: [`docs/keys-and-env.md`](docs/keys-and-env.md).

## Contributing

1. Branch from `main`: `feat/<area>-<thing>`, `fix/<area>-<thing>`, or `docs/<thing>`.
2. Open a pull request. CI must pass and one teammate must review.
3. Prefer squash merges, with commit prefixes `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
4. Contract or ABI changes need all four sign-offs and a line in `contracts/abi/CHANGELOG.md`.

CI runs `pytest` for the contracts and lint, build and tests for each Node package.

## Documentation

| Doc | Owner | Status |
|---|---|---|
| [`SPEC.md`](SPEC.md) | C | planned |
| [`backend/API.md`](backend/API.md) | B | planned |
| [`docs/limitations.md`](docs/limitations.md) | C | planned |
| [`docs/live-results.md`](docs/live-results.md) | D | generated by the live scenario runner |
| [`docs/keys-and-env.md`](docs/keys-and-env.md) | D | planned |
| [`docs/demo-script.md`](docs/demo-script.md) | D | planned |

## Known limitations (summary)

This is a **testnet project with no security audit**. Do not use real funds. Known limits include a single trusted arbitrator key, untrusted evidence being read by an LLM (prompt-injection risk), uncalibrated model confidence, and publicly readable IPFS content. See `docs/limitations.md` for the full list.

## License

To be decided.