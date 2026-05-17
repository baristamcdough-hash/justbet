# JustBet Sportsbook — Requirements Specification

> **Version:** 1.0  
> **Date:** 2026-05-17  
> **Credits:** Built by P.o.Riot  

---

## 1. Introduction & Scope

JustBet is a production-ready, mobile-first Sportsbook web application enabling users to browse live and pre-match sporting events, place single/accumulator bets, manage digital wallets, and receive real-time odds updates via WebSockets. An integrated Admin Dashboard provides operators with liability tracking and manual match settlement capabilities.

---

## 2. Stakeholder Definitions

| Stakeholder | Description |
|-------------|-------------|
| **Punter** | End-user who browses matches, places bets, and manages their wallet |
| **Admin/Operator** | Platform staff who manage matches, settle results, and monitor liability |
| **System** | Automated backend services (odds engine, settlement worker, notification bus) |

---

## 3. Functional Requirements (EARS Notation)

### 3.1 Match Grid & Odds Display

| ID | EARS Requirement |
|----|-----------------|
| FR-MG-01 | **When** the Punter opens the application, **the system shall** display a compact match grid grouped by Tournament/League with live and upcoming matches. |
| FR-MG-02 | **When** matches are displayed, **the system shall** show 3-Way Market selectors (Home/1, Draw/X, Away/2) for each match with current decimal odds. |
| FR-MG-03 | **While** a match is live, **the system shall** stream odds updates via WebSocket and reflect changes within 500ms on the client. |
| FR-MG-04 | **When** an odds value increases, **the system shall** display a green flash animation with an up-arrow indicator on the affected cell. |
| FR-MG-05 | **When** an odds value decreases, **the system shall** display a red flash animation with a down-arrow indicator on the affected cell. |
| FR-MG-06 | **When** a Punter taps/clicks an odds cell, **the system shall** toggle the selection state (active/inactive) and add/remove the selection from the Bet Slip. |

### 3.2 Bet Slip Manager

| ID | EARS Requirement |
|----|-----------------|
| FR-BS-01 | **When** on a mobile viewport (≤768px), **the system shall** render the Bet Slip as a slide-up drawer anchored to the bottom of the screen. |
| FR-BS-02 | **When** on a desktop viewport (>768px), **the system shall** render the Bet Slip as a sticky sidebar on the right side. |
| FR-BS-03 | **When** one or more selections are added, **the system shall** calculate and display the total accumulator odds by multiplying individual selection odds. |
| FR-BS-04 | **When** the Punter enters or changes a stake amount, **the system shall** instantly recalculate and display the potential winnings (stake × total odds). |
| FR-BS-05 | **When** the Punter submits the Bet Slip, **the system shall** validate sufficient wallet balance, lock the current odds, deduct the stake from the wallet, and create a Ticket record. |
| FR-BS-06 | **If** the wallet balance is insufficient, **the system shall** reject the bet placement and display an "Insufficient Balance" notification. |
| FR-BS-07 | **When** odds change after selection but before submission, **the system shall** notify the Punter of the odds movement and require re-confirmation. |

### 3.3 Authentication & User Management

| ID | EARS Requirement |
|----|-----------------|
| FR-AU-01 | **When** a new user registers, **the system shall** collect phone number and PIN/password, validate uniqueness, and create a User record with an associated Wallet. |
| FR-AU-02 | **When** a user logs in, **the system shall** authenticate via phone + PIN/password and issue a JWT access token (15min) and refresh token (7d). |
| FR-AU-03 | **When** a JWT access token expires, **the system shall** transparently refresh the session using the refresh token without user interruption. |
| FR-AU-04 | **While** a user is unauthenticated, **the system shall** allow match browsing but block bet placement and wallet operations. |

### 3.4 Wallet & Transaction Ledger

| ID | EARS Requirement |
|----|-----------------|
| FR-WL-01 | **When** a user account is created, **the system shall** initialize a Wallet with separate `real_balance` (0.00) and `bonus_balance` (0.00) fields. |
| FR-WL-02 | **When** a deposit request is made, **the system shall** expose a simulated mobile-money/payment webhook endpoint, credit the wallet upon confirmation, and create a Transaction record. |
| FR-WL-03 | **When** a withdrawal request is made, **the system shall** validate available balance, create a pending Transaction, and invoke the simulated payout endpoint. |
| FR-WL-04 | **The system shall** maintain an immutable Transaction ledger recording all wallet mutations (deposits, withdrawals, bet stakes, bet winnings, bonus credits). |
| FR-WL-05 | **When** spending balance, **the system shall** prioritize bonus balance before real balance (configurable). |

### 3.5 Admin Dashboard & Match Settlement

| ID | EARS Requirement |
|----|-----------------|
| FR-AD-01 | **When** an Admin accesses the dashboard, **the system shall** display aggregated financial liability per active match (total potential payouts). |
| FR-AD-02 | **When** an Admin creates a match, **the system shall** require League, Home Team, Away Team, Kickoff Time, and initial 1/X/2 odds. |
| FR-AD-03 | **When** an Admin updates odds for a live match, **the system shall** publish the delta to the Redis pub-sub channel, triggering immediate WebSocket broadcast to all connected clients. |
| FR-AD-04 | **When** an Admin settles a match (inputs final score), **the system shall** determine winning/losing selections, mark all associated Tickets accordingly, and enqueue asynchronous payout jobs. |
| FR-AD-05 | **When** a payout job executes, **the system shall** credit the Punter's wallet with (stake × locked odds) and create a winning Transaction record. |
| FR-AD-06 | **If** a payout job fails, **the system shall** retry up to 3 times with exponential backoff and alert the Admin on final failure. |

### 3.6 Real-Time Infrastructure

| ID | EARS Requirement |
|----|-----------------|
| FR-RT-01 | **The system shall** use Redis Pub/Sub as the central message bus for odds update events between the Admin API and WebSocket broadcast layer. |
| FR-RT-02 | **When** a client establishes a WebSocket connection, **the system shall** subscribe the connection to relevant match channels and stream odds deltas in real-time. |
| FR-RT-03 | **If** a WebSocket connection drops, **the system shall** attempt automatic reconnection with exponential backoff (1s, 2s, 4s, max 30s). |
| FR-RT-04 | **The system shall** cache the latest odds snapshot in Redis with a TTL of 60 seconds to serve new connections without querying PostgreSQL. |

---

## 4. Non-Functional Requirements

### 4.1 Performance

| ID | Requirement |
|----|-------------|
| NFR-P-01 | The initial page load (LCP) shall complete within 2 seconds on a 3G mobile connection. |
| NFR-P-02 | Odds updates shall propagate from Redis publish to client render in under 500ms (p95). |
| NFR-P-03 | The API shall support 10,000 concurrent WebSocket connections per node. |
| NFR-P-04 | Bet placement transactions shall complete within 200ms (p95) under normal load. |

### 4.2 Scalability

| ID | Requirement |
|----|-------------|
| NFR-S-01 | The architecture shall support horizontal scaling of WebSocket nodes behind a load balancer. |
| NFR-S-02 | Database operations shall use connection pooling (min 10, max 50 connections per instance). |

### 4.3 Reliability & Availability

| ID | Requirement |
|----|-------------|
| NFR-R-01 | Wallet mutations shall be executed within database transactions with row-level locking to prevent race conditions. |
| NFR-R-02 | The settlement worker shall be idempotent—re-processing a settled match shall not produce duplicate payouts. |
| NFR-R-03 | The system shall target 99.9% uptime for the core betting flow. |

### 4.4 Security

| ID | Requirement |
|----|-------------|
| NFR-SEC-01 | All passwords/PINs shall be hashed using bcrypt (cost factor ≥ 12). |
| NFR-SEC-02 | All API endpoints (except public match listing) shall require valid JWT authentication. |
| NFR-SEC-03 | Admin endpoints shall require role-based authorization (`role = admin`). |
| NFR-SEC-04 | WebSocket connections shall authenticate via token in the initial handshake. |
| NFR-SEC-05 | Rate limiting shall be applied: 100 requests/minute for authenticated users, 30/minute for anonymous. |

### 4.5 Mobile-First & Responsiveness

| ID | Requirement |
|----|-------------|
| NFR-MF-01 | All UI components shall be designed mobile-first with breakpoints at 360px, 768px, and 1280px. |
| NFR-MF-02 | Touch targets shall be minimum 44×44px per WCAG 2.1 guidelines. |
| NFR-MF-03 | The match grid shall use virtualized scrolling for lists exceeding 50 items. |
| NFR-MF-04 | Total JS bundle size shall not exceed 200KB gzipped for initial load. |

### 4.6 Containerization & DevOps

| ID | Requirement |
|----|-------------|
| NFR-DO-01 | The application shall be fully containerized with Docker Compose orchestrating: Frontend, API, PostgreSQL, and Redis services. |
| NFR-DO-02 | Environment configuration shall be managed via `.env` files with no secrets in source control. |
| NFR-DO-03 | Database migrations shall be versioned and applied automatically on container startup. |

---

## 5. Betting Lifecycle State Machine

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Match Created│────▶│  Odds Live   │────▶│ Slip Selected│────▶│ Stake Placed │
│  (by Admin)  │     │ (streaming)  │     │ (by Punter)  │     │(balance deducted)│
└──────────────┘     └──────────────┘     └──────────────┘     └──────┬───────┘
                                                                       │
                    ┌──────────────┐     ┌──────────────┐              │
                    │  Payout Done │◀────│Match Settled │◀─────────────┘
                    │(wallet credit)│     │ (by Admin)   │
                    └──────────────┘     └──────────────┘
```

**States:**
1. **Match Created** → Admin creates match with initial odds
2. **Odds Live** → System streams real-time odds; Punters can browse
3. **Slip Selected** → Punter adds selections to Bet Slip
4. **Stake Placed** → Punter confirms bet; wallet debited; Ticket created with locked odds
5. **Match Settled** → Admin inputs result; system evaluates tickets (Won/Lost)
6. **Payout Done** → Winning tickets trigger async wallet credit

---

## 6. Acceptance Criteria Summary

| Feature | Criteria |
|---------|----------|
| Match Grid | Loads <2s on 3G; grouped by league; real-time odds with visual indicators |
| Bet Slip | Accumulator math correct; mobile drawer + desktop sidebar; odds-change warning |
| Wallet | Atomic transactions; no negative balance; full audit trail |
| Auth | JWT flow with refresh; phone+PIN; role separation |
| Admin | Liability view; manual settlement; async payout with retry |
| Real-Time | <500ms odds propagation; auto-reconnect; Redis-backed |
| Brand | Footer displays "Built by P.o.Riot" on all pages |

---

*Built by P.o.Riot | Credits P.o.Riot*
