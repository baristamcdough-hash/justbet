# JustBet Sportsbook — Requirements Specification (Kenya Localized)

> **Version:** 2.0 — Localized Pivot  
> **Date:** 2026-05-17  
> **Market:** Kenya (KES · Safaricom M-Pesa · Phone/PIN Auth)  
> **Credits:** Built by P.o.Riot  

---

## 1. Introduction & Scope

JustBet is a production-grade, mobile-first Sportsbook platform targeting the Kenyan betting market. The platform mirrors the core operational loop of Betika: punters authenticate with their **Safaricom phone number + 4-digit PIN**, deposit via **M-Pesa STK Push**, place single or accumulator bets on football matches streamed in real-time, and receive winnings directly to their M-Pesa wallet upon match settlement.

All monetary values are denominated in **Kenya Shillings (KES)**. The platform enforces Kenyan regulatory minimums (KES 50 min stake, KES 100 min deposit, KES 100 min withdrawal) and is optimized for low-bandwidth mobile devices running on Safaricom 3G/4G networks.

---

## 2. Stakeholder Definitions

| Stakeholder | Description |
|-------------|-------------|
| **Punter** | Kenyan user who registers via phone, deposits via M-Pesa, places bets in KES, and withdraws winnings to M-Pesa |
| **Admin/Operator** | Platform staff who create matches, update live odds, settle matches, monitor financial liability, and trigger payouts |
| **System** | Automated backend services: odds streaming engine, settlement worker, M-Pesa webhook processor, Redis cache layer |
| **M-Pesa Gateway** | Safaricom Daraja API (simulated) for STK Push deposits and B2C disbursement withdrawals |

---

## 3. Functional Requirements (EARS Notation)

### 3.1 Authentication — Phone Number + 4-Digit PIN

| ID | EARS Requirement |
|----|-----------------|
| FR-AU-01 | **When** a new user registers, **the system shall** collect a Kenyan phone number (format: `07XXXXXXXX` or `+254XXXXXXXXX`) and a 4-digit numeric PIN, validate phone uniqueness, hash the PIN with bcrypt(12), create a User record with role `punter`, and initialize an associated Wallet with `real_balance = 0.00 KES` and `bonus_balance = 0.00 KES`. |
| FR-AU-02 | **When** a user logs in, **the system shall** authenticate via phone + PIN and issue a JWT access token (TTL: 30 minutes) and a refresh token (TTL: 30 days). |
| FR-AU-03 | **When** a JWT access token expires, **the system shall** transparently rotate the token using the refresh token without interrupting the punter's session. |
| FR-AU-04 | **While** a user is unauthenticated, **the system shall** allow match browsing and odds viewing but block bet placement, wallet operations, and My Bets access. |
| FR-AU-05 | **When** the application starts for the first time (empty users table), **the system shall** auto-seed a super-admin account using environment variables `FIRST_ADMIN_PHONE` and `FIRST_ADMIN_PIN`. |
| FR-AU-06 | **When** an admin creates additional admin accounts, **the system shall** require the `ADMIN_SECRET_TOKEN` header for authorization. |

### 3.2 Match Grid & Live Odds Display

| ID | EARS Requirement |
|----|-----------------|
| FR-MG-01 | **When** the Punter opens the application, **the system shall** display a compact match grid grouped by League/Tournament (e.g., "Kenya Premier League", "English Premier League", "UEFA Champions League"). |
| FR-MG-02 | **When** matches are displayed, **the system shall** show 3-Way Market odds selectors (1 = Home, X = Draw, 2 = Away) using decimal format (e.g., 2.15, 3.40, 3.10). |
| FR-MG-03 | **While** a match is marked `live`, **the system shall** stream odds deltas via WebSocket within 500ms of admin update, without requiring page refresh. |
| FR-MG-04 | **When** an odds value increases from its previous value, **the system shall** trigger a green flash animation with an up-arrow (▲) indicator for 600ms. |
| FR-MG-05 | **When** an odds value decreases from its previous value, **the system shall** trigger a red flash animation with a down-arrow (▼) indicator for 600ms. |
| FR-MG-06 | **When** a Punter taps an odds cell, **the system shall** toggle the selection state and add/remove the selection from the Bet Slip, allowing only one market per match. |

### 3.3 Bet Slip & Accumulator Engine

| ID | EARS Requirement |
|----|-----------------|
| FR-BS-01 | **When** on a mobile viewport (≤768px), **the system shall** render the Bet Slip as a slide-up drawer with a floating badge showing selection count. |
| FR-BS-02 | **When** on a desktop viewport (>768px), **the system shall** render the Bet Slip as a sticky sidebar (width: 320px) on the right edge. |
| FR-BS-03 | **When** multiple selections are added, **the system shall** calculate total accumulator odds by multiplying all individual selection odds and display the result to 2 decimal places. |
| FR-BS-04 | **When** the Punter enters or changes a stake amount (KES), **the system shall** instantly recalculate `Potential Win = Stake × Total Odds` and display in KES format. |
| FR-BS-05 | **When** the Punter submits the Bet Slip, **the system shall** validate: (a) stake ≥ KES 50, (b) sufficient wallet balance, (c) all selected matches still accepting bets, then atomically: lock current odds, deduct stake from wallet, create Ticket + Selection records. |
| FR-BS-06 | **If** the wallet balance is less than the entered stake, **the system shall** reject submission and display "Salio haitoshi — Deposit to continue" (insufficient balance notification). |
| FR-BS-07 | **When** odds change after selection but before submission, **the system shall** display an "Odds Changed" warning badge on affected selections and require the punter to accept or remove before placing. |
| FR-BS-08 | **The system shall** persist the Bet Slip state to `localStorage` so selections survive page refresh and app restarts. |

### 3.4 Wallet & M-Pesa Integration (Simulated Daraja)

| ID | EARS Requirement |
|----|-----------------|
| FR-WL-01 | **When** a user account is created, **the system shall** initialize a Wallet with `real_balance = 0.00 KES` and `bonus_balance = 0.00 KES`. |
| FR-WL-02 | **When** a punter requests a deposit (min KES 100, max KES 150,000), **the system shall** simulate a Safaricom M-Pesa STK Push by: (a) creating a pending transaction with `checkout_request_id`, (b) returning a simulated "Enter PIN on phone" response, (c) auto-confirming after 3 seconds (simulating M-Pesa callback). |
| FR-WL-03 | **When** the simulated M-Pesa callback arrives at `POST /api/webhooks/mpesa/callback`, **the system shall** match the `checkout_request_id`, credit the wallet `real_balance`, mark the transaction as `completed`, and return `ResultCode: 0`. |
| FR-WL-04 | **When** a punter requests a withdrawal (min KES 100, max KES 70,000), **the system shall** validate `real_balance ≥ amount`, deduct from wallet, create a pending transaction, and simulate a B2C disbursement confirmation. |
| FR-WL-05 | **The system shall** maintain an immutable, append-only transaction ledger recording: deposits, withdrawals, bet_stake, bet_winning, bonus_credit, and refund entries with `balance_after` snapshots. |
| FR-WL-06 | **When** deducting stake, **the system shall** spend `bonus_balance` first, then `real_balance` (configurable priority). |
| FR-WL-07 | **The system shall** display all balances and amounts in "KES X,XXX.XX" format with Kenyan locale thousand separators. |

### 3.5 Admin Dashboard & Match Settlement

| ID | EARS Requirement |
|----|-----------------|
| FR-AD-01 | **When** an Admin accesses the dashboard, **the system shall** display: total registered users, active tickets count, total stakes (KES), and aggregate financial liability per active match. |
| FR-AD-02 | **When** an Admin creates a match, **the system shall** require: League, Home Team, Away Team, Kickoff DateTime (EAT timezone), and initial 1/X/2 decimal odds. |
| FR-AD-03 | **When** an Admin updates odds for an active match, **the system shall** persist new odds to PostgreSQL, record in odds_history, publish the delta to Redis channel `odds:{match_id}`, and update the Redis cache key `odds:current:{match_id}` (TTL 60s). |
| FR-AD-04 | **When** an Admin settles a match by inputting the final score, **the system shall**: (a) determine the match result (home_win/draw/away_win), (b) evaluate all selections on that match, (c) mark fully-resolved tickets as `won` or `lost`, (d) enqueue payout jobs for winning tickets to the Background Worker. |
| FR-AD-05 | **When** a payout job executes, **the system shall** atomically: lock the wallet row (SELECT FOR UPDATE), credit `real_balance += potential_win`, insert a `bet_winning` transaction, and mark the ticket as `paid`. |
| FR-AD-06 | **If** a payout job fails, **the system shall** retry up to 3 times with exponential backoff (2s, 4s, 8s) before marking the payout as `failed` and alerting the admin. |
| FR-AD-07 | **The system shall** enforce idempotency: re-settling an already-settled match produces zero duplicate transactions (guarded by `reference_id` uniqueness on ticket payouts). |

### 3.6 Real-Time Infrastructure (Redis + WebSocket)

| ID | EARS Requirement |
|----|-----------------|
| FR-RT-01 | **The system shall** use Redis Pub/Sub as the central message bus for odds update events between the API service and WebSocket broadcast layer. |
| FR-RT-02 | **When** a client connects to the WebSocket endpoint `/ws/odds`, **the system shall** validate the JWT token in the query parameter and subscribe the connection to requested match channels. |
| FR-RT-03 | **When** a new client subscribes to a match channel, **the system shall** immediately send the cached odds snapshot from Redis before streaming live deltas. |
| FR-RT-04 | **If** a WebSocket connection drops, the frontend client **shall** auto-reconnect with exponential backoff: 1s → 2s → 4s → 8s → 16s → 30s (max). |
| FR-RT-05 | **The system shall** support a `/ws/odds` health ping/pong mechanism every 30 seconds to detect stale connections. |

---

## 4. Non-Functional Requirements

### 4.1 Performance

| ID | Requirement |
|----|-------------|
| NFR-P-01 | Initial page load (LCP) shall complete within 2 seconds on Safaricom 3G (≈1.5 Mbps). |
| NFR-P-02 | Odds updates shall propagate from Redis PUBLISH to client DOM render in under 500ms (p95). |
| NFR-P-03 | The WebSocket server shall support 10,000 concurrent connections per node. |
| NFR-P-04 | Bet placement (POST /api/tickets) shall complete within 200ms (p95) under 500 concurrent users. |

### 4.2 Scalability

| ID | Requirement |
|----|-------------|
| NFR-S-01 | WebSocket nodes shall scale horizontally; Redis Pub/Sub ensures all nodes receive odds updates. |
| NFR-S-02 | PostgreSQL connection pooling: min 10, max 50 connections per service instance. |

### 4.3 Reliability & Data Integrity

| ID | Requirement |
|----|-------------|
| NFR-R-01 | All wallet mutations shall use PostgreSQL row-level locking (`SELECT ... FOR UPDATE`) within explicit transactions. |
| NFR-R-02 | The settlement worker shall be idempotent — re-processing a settled match yields zero new transactions. |
| NFR-R-03 | Target uptime: 99.9% for core betting flow (match list, bet placement, wallet). |

### 4.4 Security

| ID | Requirement |
|----|-------------|
| NFR-SEC-01 | PINs shall be hashed with bcrypt (cost factor = 12). |
| NFR-SEC-02 | All endpoints except `/api/matches`, `/api/leagues`, and `/health` require valid JWT Bearer token. |
| NFR-SEC-03 | Admin endpoints (`/api/admin/*`) require `role = admin` in JWT claims. |
| NFR-SEC-04 | First admin account seeded from `FIRST_ADMIN_PHONE` + `FIRST_ADMIN_PIN` environment variables (never hardcoded). |
| NFR-SEC-05 | WebSocket authentication via `?token=<JWT>` query parameter validated on handshake. |
| NFR-SEC-06 | Rate limiting: 100 requests/min (authenticated), 30/min (anonymous), enforced per IP. |
| NFR-SEC-07 | CORS restricted to the deployed frontend origin only. |

### 4.5 Mobile-First UX

| ID | Requirement |
|----|-------------|
| NFR-MF-01 | All UI designed mobile-first; breakpoints at 360px (compact), 768px (tablet), 1280px (desktop). |
| NFR-MF-02 | Touch targets minimum 44×44px. |
| NFR-MF-03 | Total initial JS bundle ≤ 200KB gzipped. |
| NFR-MF-04 | Bet slip persists to localStorage across sessions. |
| NFR-MF-05 | All currency displays in "KES X,XXX.XX" format. |

### 4.6 Deployment & Infrastructure (Render)

| ID | Requirement |
|----|-------------|
| NFR-DO-01 | Deployed on Render with: Static Site (frontend), Web Service (API+WS), Background Worker (settlement), Managed PostgreSQL, Managed Redis. |
| NFR-DO-02 | All secrets managed via Render environment variables; zero secrets in source control. |
| NFR-DO-03 | Database migrations auto-applied on API deploy via `alembic upgrade head` in build command. |
| NFR-DO-04 | Admin account auto-seeded on first boot if `FIRST_ADMIN_PHONE` is set. |

---

## 5. Betting Lifecycle — Localized State Machine

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Admin Creates   │────▶│  Odds Streaming  │────▶│  Punter Selects  │
│  Match (KPL/EPL) │     │  (Redis → WS)    │     │  1/X/2 on Grid   │
└──────────────────┘     └──────────────────┘     └────────┬─────────┘
                                                            │
┌──────────────────┐     ┌──────────────────┐              │
│  M-Pesa Payout   │◀────│  Admin Settles   │              ▼
│  (B2C to Phone)  │     │  (Score → Result)│     ┌──────────────────┐
└──────────────────┘     └────────┬─────────┘     │  Bet Placed      │
                                  │               │  (KES deducted,  │
                                  │               │   odds locked)   │
                                  │               └────────┬─────────┘
                                  │                        │
                                  └────────────────────────┘
                                    Worker evaluates tickets
                                    Won → credit KES to wallet
                                    Lost → ticket closed
```

### Business Rules (Kenya-Specific)

| Rule | Value |
|------|-------|
| Currency | KES (Kenya Shilling) |
| Min Stake | KES 50 |
| Max Stake | KES 500,000 |
| Min Deposit | KES 100 |
| Max Deposit | KES 150,000 |
| Min Withdrawal | KES 100 |
| Max Withdrawal | KES 70,000 |
| Max Selections per Slip | 30 |
| Max Potential Win | KES 10,000,000 |
| PIN Format | 4-digit numeric |
| Phone Format | 07XXXXXXXX or +254XXXXXXXXX |
| Timezone | EAT (UTC+3) |

---

## 6. Acceptance Criteria Summary

| Feature | Criteria |
|---------|----------|
| Auth | Phone + 4-digit PIN; auto-seed admin from env vars; JWT 30min/30d |
| Match Grid | Grouped by league; <2s load on 3G; real-time odds with green/red flash |
| Bet Slip | Accumulator math; KES 50 min; mobile drawer + desktop sidebar; localStorage persistence |
| Wallet | KES balances; M-Pesa STK Push simulation; deposit/withdrawal with proper min/max enforcement |
| Settlement | Admin inputs score → tickets evaluated → async payout with 3× retry → idempotent |
| Real-Time | Redis Pub/Sub → WebSocket; <500ms propagation; auto-reconnect; cached snapshot on subscribe |
| Admin | Liability view; match CRUD; odds update (triggers live broadcast); aggregate stats |
| Deployment | render.yaml provisions all services; admin seeded from env; zero secrets in repo |
| Brand | Footer on all pages: "Built by P.o.Riot / Credits P.o.Riot" |

---

*Built by P.o.Riot | Credits P.o.Riot*
