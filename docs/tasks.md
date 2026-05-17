# JustBet Sportsbook — Implementation Tasks

> **Version:** 1.0  
> **Date:** 2026-05-17  
> **Credits:** Built by P.o.Riot  

---

## Overview

Tasks are organized into sequential MVP blocks. Each block is independently deliverable and builds upon the previous. Tasks within a block can be parallelized where noted.

---

## Block 1: Project Scaffolding & Infrastructure

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| T-1.1 | Create monorepo directory structure (`/frontend`, `/backend`, `/docs`, `/docker`) | P0 | None |
| T-1.2 | Initialize backend: Python 3.12, FastAPI, pyproject.toml, virtual env | P0 | T-1.1 |
| T-1.3 | Initialize frontend: Vite + React 18 + TypeScript + Tailwind CSS | P0 | T-1.1 |
| T-1.4 | Write `docker-compose.yml` with all 5 services (frontend, api, ws, postgres, redis) | P0 | T-1.1 |
| T-1.5 | Create Dockerfiles for frontend and backend | P0 | T-1.2, T-1.3 |
| T-1.6 | Create `.env.example` with all required environment variables | P0 | T-1.4 |
| T-1.7 | Set up Alembic for database migrations | P0 | T-1.2 |

**Deliverable:** `docker-compose up` boots all services; frontend serves blank page; API returns health check.

---

## Block 2: Database Models & Migrations

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| T-2.1 | Define SQLAlchemy models: `User`, `Wallet`, `Transaction` | P0 | T-1.7 |
| T-2.2 | Define SQLAlchemy models: `League`, `Match`, `MatchOdds` | P0 | T-1.7 |
| T-2.3 | Define SQLAlchemy models: `Ticket`, `Selection` | P0 | T-1.7 |
| T-2.4 | Create Alembic migration for all tables with indexes and constraints | P0 | T-2.1–T-2.3 |
| T-2.5 | Add seed data script (demo leagues, matches, admin user) | P1 | T-2.4 |

**Deliverable:** `alembic upgrade head` creates all tables; seed script populates demo data.

---

## Block 3: Authentication & User Management API

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| T-3.1 | Implement `/api/auth/register` — phone + password, bcrypt hashing, wallet creation | P0 | T-2.1 |
| T-3.2 | Implement `/api/auth/login` — credential validation, JWT generation (access + refresh) | P0 | T-2.1 |
| T-3.3 | Implement `/api/auth/refresh` — refresh token rotation | P0 | T-3.2 |
| T-3.4 | Implement `/api/auth/me` — return current user profile | P1 | T-3.2 |
| T-3.5 | Create JWT middleware + dependency injection for route protection | P0 | T-3.2 |
| T-3.6 | Create admin role guard middleware | P0 | T-3.5 |
| T-3.7 | Implement rate limiting middleware (100/min auth, 30/min anon) | P1 | T-3.5 |

**Deliverable:** Users can register, login, and access protected endpoints with JWT.

---

## Block 4: Match & Odds Engine (Core)

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| T-4.1 | Implement `GET /api/matches` — list active matches grouped by league with current odds | P0 | T-2.2 |
| T-4.2 | Implement `GET /api/matches/{id}` — single match with odds history | P1 | T-2.2 |
| T-4.3 | Implement `GET /api/leagues` — list all leagues | P1 | T-2.2 |
| T-4.4 | Implement `POST /api/admin/matches` — create match with initial odds | P0 | T-3.6, T-2.2 |
| T-4.5 | Implement `POST /api/admin/leagues` — create league | P0 | T-3.6, T-2.2 |
| T-4.6 | Implement `PATCH /api/admin/matches/{id}/odds` — update odds + Redis publish | P0 | T-4.4 |
| T-4.7 | Set up Redis connection pool and pub/sub publisher utility | P0 | T-1.4 |
| T-4.8 | Implement Redis odds caching (GET/SET with 60s TTL) | P1 | T-4.7 |

**Deliverable:** Admin can create matches/leagues, update odds; public can query match listings. Odds changes published to Redis.

---

## Block 5: Real-Time WebSocket Server

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| T-5.1 | Create WebSocket server entry point (`ws_server.py`) with FastAPI | P0 | T-4.7 |
| T-5.2 | Implement WS endpoint `/ws/odds` with JWT auth in handshake | P0 | T-3.5, T-5.1 |
| T-5.3 | Implement subscription message handling (subscribe/unsubscribe to match channels) | P0 | T-5.2 |
| T-5.4 | Implement Redis subscriber → broadcast to connected WS clients | P0 | T-5.3 |
| T-5.5 | Add connection health check (ping/pong) and graceful disconnect | P1 | T-5.2 |
| T-5.6 | Serve cached odds snapshot to new subscribers from Redis | P1 | T-4.8, T-5.3 |

**Deliverable:** Clients receive real-time odds updates within 500ms of admin change. Auto-reconnect supported.

---

## Block 6: Bet Slip & Ticket Placement

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| T-6.1 | Implement `POST /api/tickets` — validate selections, lock odds, deduct stake, create ticket | P0 | T-3.5, T-2.3 |
| T-6.2 | Implement wallet balance validation with row-level locking | P0 | T-6.1 |
| T-6.3 | Implement accumulator odds calculation (multiply selection odds) | P0 | T-6.1 |
| T-6.4 | Implement `GET /api/tickets` — list user tickets with pagination | P1 | T-6.1 |
| T-6.5 | Implement `GET /api/tickets/{id}` — full ticket detail with selections | P1 | T-6.1 |
| T-6.6 | Add odds-change detection: reject bet if odds moved since selection | P1 | T-6.1, T-4.8 |

**Deliverable:** Punters can place single/accumulator bets with atomic wallet deduction and locked odds.

---

## Block 7: Wallet & Payment Gateway

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| T-7.1 | Implement `GET /api/wallet` — return real + bonus balances | P0 | T-3.5, T-2.1 |
| T-7.2 | Implement `POST /api/wallet/deposit` — initiate deposit, create pending transaction | P0 | T-7.1 |
| T-7.3 | Implement `POST /api/webhooks/payment` — simulated M-Pesa callback, confirm deposit | P0 | T-7.2 |
| T-7.4 | Implement `POST /api/wallet/withdraw` — validate balance, create pending withdrawal | P0 | T-7.1 |
| T-7.5 | Implement `GET /api/wallet/transactions` — paginated transaction history | P1 | T-7.1 |
| T-7.6 | Implement balance priority logic (spend bonus before real, configurable) | P1 | T-7.1 |

**Deliverable:** Full wallet lifecycle — deposits (simulated), withdrawals, transaction ledger.

---

## Block 8: Admin Dashboard & Match Settlement

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| T-8.1 | Implement `POST /api/admin/matches/{id}/settle` — input result, evaluate all tickets | P0 | T-6.1, T-4.4 |
| T-8.2 | Build settlement worker: async payout loop with row-level wallet locking | P0 | T-8.1 |
| T-8.3 | Implement idempotency guard (prevent duplicate payouts on re-settlement) | P0 | T-8.2 |
| T-8.4 | Implement retry logic with exponential backoff (3 retries: 2s, 4s, 8s) | P1 | T-8.2 |
| T-8.5 | Implement `GET /api/admin/liability` — aggregate potential payout per match | P0 | T-6.1 |
| T-8.6 | Implement `GET /api/admin/dashboard` — stats (active bets, total stakes, users) | P1 | T-6.1 |

**Deliverable:** Admin can settle matches; winning punters auto-credited; liability tracked.

---

## Block 9: Frontend — Core Layout & Match Grid

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| T-9.1 | Set up React Router, global layout, responsive shell, footer ("Built by P.o.Riot") | P0 | T-1.3 |
| T-9.2 | Create API service layer (Axios instance with JWT interceptor) | P0 | T-9.1 |
| T-9.3 | Build MatchGrid component — league-grouped list with virtualized scrolling | P0 | T-9.2 |
| T-9.4 | Build OddsCell component — 1/X/2 buttons with selection toggle state | P0 | T-9.3 |
| T-9.5 | Implement odds flash animations (green up-arrow, red down-arrow on change) | P0 | T-9.4 |
| T-9.6 | Connect WebSocket hook for real-time odds updates | P0 | T-9.5 |
| T-9.7 | Implement React Query caching for match list (30s stale time) | P1 | T-9.3 |

**Deliverable:** Live match grid with real-time odds updates and visual indicators.

---

## Block 10: Frontend — Bet Slip & Placement Flow

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| T-10.1 | Create Zustand bet slip store (add/remove selections, calculate totals) | P0 | T-9.4 |
| T-10.2 | Build BetSlip drawer component (mobile slide-up) | P0 | T-10.1 |
| T-10.3 | Build BetSlip sidebar component (desktop sticky) | P0 | T-10.1 |
| T-10.4 | Implement stake input with live potential winnings calculation | P0 | T-10.2 |
| T-10.5 | Implement bet placement API call with success/error feedback | P0 | T-10.4 |
| T-10.6 | Add odds-change warning modal before submission | P1 | T-10.5 |
| T-10.7 | Persist bet slip to localStorage for session continuity | P1 | T-10.1 |

**Deliverable:** Full bet slip UX — add/remove selections, accumulator math, place bet.

---

## Block 11: Frontend — Auth, Wallet & My Bets

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| T-11.1 | Build Login page (phone + PIN/password) | P0 | T-9.2 |
| T-11.2 | Build Register page | P0 | T-9.2 |
| T-11.3 | Implement auth context with token storage and auto-refresh | P0 | T-11.1 |
| T-11.4 | Build Wallet page — balance display, deposit form, withdraw form | P0 | T-11.3 |
| T-11.5 | Build Transaction history list | P1 | T-11.4 |
| T-11.6 | Build My Bets page — ticket list with status badges | P1 | T-11.3 |
| T-11.7 | Add protected route wrapper (redirect to login if unauthenticated) | P0 | T-11.3 |

**Deliverable:** Complete auth flow, wallet management, and bet history views.

---

## Block 12: Frontend — Admin Dashboard

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| T-12.1 | Build Admin layout with navigation (Dashboard, Matches, Settlement) | P0 | T-11.3 |
| T-12.2 | Build Match creation form (league, teams, kickoff, initial odds) | P0 | T-12.1 |
| T-12.3 | Build Odds update panel with live preview | P0 | T-12.2 |
| T-12.4 | Build Match settlement form (input score → trigger settle API) | P0 | T-12.1 |
| T-12.5 | Build Liability dashboard — table of matches with potential payouts | P0 | T-12.1 |
| T-12.6 | Build aggregate stats cards (active bets, total stakes, registered users) | P1 | T-12.1 |

**Deliverable:** Fully functional admin console for match/odds management and settlement.

---

## Block 13: Integration, Polish & Deployment

| ID | Task | Priority | Dependencies |
|----|------|----------|--------------|
| T-13.1 | End-to-end integration test: register → deposit → place bet → settle → payout | P0 | All |
| T-13.2 | Verify Docker Compose full-stack boot (all services healthy) | P0 | All |
| T-13.3 | Add loading skeletons and error boundaries to frontend | P1 | Block 9–12 |
| T-13.4 | Responsive QA: verify all views at 360px, 768px, 1280px breakpoints | P0 | Block 9–12 |
| T-13.5 | Verify footer "Built by P.o.Riot" renders on all pages | P0 | T-9.1 |
| T-13.6 | Write README.md with setup instructions | P1 | T-13.2 |
| T-13.7 | Create PR with clean commit history | P0 | T-13.6 |

**Deliverable:** Production-ready, merge-ready pull request with full documentation.

---

## Execution Priority Summary

| Phase | Blocks | Parallelizable |
|-------|--------|----------------|
| Infrastructure | 1 | Sequential |
| Data Layer | 2 | Sequential (after Block 1) |
| Backend Core | 3, 4, 5, 6, 7, 8 | Blocks 3–4 parallel; 5–6 depend on 4; 7–8 depend on 6 |
| Frontend | 9, 10, 11, 12 | Block 9 first; 10–12 parallel after 9 |
| Integration | 13 | Sequential (final) |

---

*Built by P.o.Riot | Credits P.o.Riot*
