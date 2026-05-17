# JustBet Sportsbook — Implementation Tasks (v2 Kenya Localized)

> **Version:** 2.0  
> **Date:** 2026-05-17  
> **Market:** Kenya (KES · M-Pesa · Phone/PIN)  
> **Credits:** Built by P.o.Riot  

---

## Overview

Reorganized task blocks for the localized Kenyan sportsbook pivot. All monetary logic uses KES, authentication uses Phone + 4-digit PIN, deposits/withdrawals simulate M-Pesa Daraja STK Push/B2C, and the admin system supports environment-seeded first admin accounts.

---

## Block 1: Infrastructure & Scaffold ✅ COMPLETE

| ID | Task | Status |
|----|------|--------|
| T-1.1 | Monorepo structure (frontend/, backend/, docs/) | ✅ Done |
| T-1.2 | Backend: FastAPI + SQLAlchemy async + Alembic | ✅ Done |
| T-1.3 | Frontend: Vite + React 18 + TypeScript + Tailwind | ✅ Done |
| T-1.4 | docker-compose.yml (5 services) | ✅ Done |
| T-1.5 | Dockerfiles (frontend + backend) | ✅ Done |
| T-1.6 | .env.example with all variables | ✅ Done |
| T-1.7 | Alembic configuration | ✅ Done |

---

## Block 2: Database Models ✅ COMPLETE

| ID | Task | Status |
|----|------|--------|
| T-2.1 | User model (phone, pin_hash, role enum) | ✅ Done |
| T-2.2 | Wallet model (real_balance, bonus_balance, currency=KES) | ✅ Done |
| T-2.3 | Transaction model (type enum, checkout_request_id) | ✅ Done |
| T-2.4 | League, Match, MatchOdds models | ✅ Done |
| T-2.5 | Ticket, Selection models | ✅ Done |

---

## Block 3: Authentication — Phone/PIN + Admin Seeding 🔄 IN PROGRESS

| ID | Task | Priority | Status |
|----|------|----------|--------|
| T-3.1 | Update config.py: add FIRST_ADMIN_PHONE, FIRST_ADMIN_PIN, ADMIN_SECRET_TOKEN, MIN_STAKE, currency settings | P0 | 🔄 |
| T-3.2 | Implement admin auto-seeding on first boot (startup event checks users table) | P0 | 🔄 |
| T-3.3 | Validate phone format (07XX/+254XX) in registration | P0 | 🔄 |
| T-3.4 | Validate PIN is exactly 4 digits numeric | P0 | 🔄 |
| T-3.5 | Update JWT expiry to 30min access / 30d refresh | P0 | 🔄 |
| T-3.6 | Add ADMIN_SECRET_TOKEN header check for admin user creation | P0 | 🔄 |

---

## Block 4: Wallet & M-Pesa Simulation 🔄 IN PROGRESS

| ID | Task | Priority | Status |
|----|------|----------|--------|
| T-4.1 | Add KES min/max enforcement (deposit: 100–150k, withdraw: 100–70k, stake: 50–500k) | P0 | 🔄 |
| T-4.2 | Implement simulated STK Push flow (generate checkout_request_id, auto-confirm after 3s) | P0 | 🔄 |
| T-4.3 | Implement `/api/webhooks/mpesa/callback` with Daraja-style payload format | P0 | 🔄 |
| T-4.4 | Implement B2C withdrawal simulation | P0 | 🔄 |
| T-4.5 | Add `checkout_request_id` field to Transaction model | P1 | 🔄 |
| T-4.6 | Format all amounts as "KES X,XXX.XX" in API responses | P1 | 🔄 |

---

## Block 5: Match Engine & Real-Time Odds ✅ COMPLETE

| ID | Task | Status |
|----|------|--------|
| T-5.1 | GET /api/matches (grouped by league) | ✅ Done |
| T-5.2 | POST /api/admin/matches (create with odds) | ✅ Done |
| T-5.3 | PATCH /api/admin/matches/{id}/odds (update + Redis publish) | ✅ Done |
| T-5.4 | Redis pub/sub publisher utility | ✅ Done |
| T-5.5 | WebSocket /ws/odds endpoint with JWT auth | ✅ Done |
| T-5.6 | Redis subscriber → broadcast to WS clients | ✅ Done |
| T-5.7 | Cached odds snapshot for new subscribers | ✅ Done |

---

## Block 6: Bet Slip & Ticket Placement ✅ COMPLETE

| ID | Task | Status |
|----|------|--------|
| T-6.1 | POST /api/tickets (validate, lock odds, deduct, create) | ✅ Done |
| T-6.2 | Row-level wallet locking (FOR UPDATE) | ✅ Done |
| T-6.3 | Accumulator odds multiplication | ✅ Done |
| T-6.4 | Bonus-first spending priority | ✅ Done |
| T-6.5 | GET /api/tickets (user's tickets) | ✅ Done |

---

## Block 7: Admin Settlement & Payout Worker ✅ COMPLETE

| ID | Task | Status |
|----|------|--------|
| T-7.1 | POST /api/admin/matches/{id}/settle | ✅ Done |
| T-7.2 | Selection evaluation (won/lost based on result) | ✅ Done |
| T-7.3 | Background worker (python -m app.worker) | ✅ Done |
| T-7.4 | Idempotent payout (reference_id guard) | ✅ Done |
| T-7.5 | Exponential backoff retry (2s, 4s, 8s) | ✅ Done |
| T-7.6 | GET /api/admin/liability | ✅ Done |
| T-7.7 | GET /api/admin/dashboard (stats) | ✅ Done |

---

## Block 8: Frontend — Core ✅ COMPLETE

| ID | Task | Status |
|----|------|--------|
| T-8.1 | Router + layout + Footer ("Built by P.o.Riot") | ✅ Done |
| T-8.2 | API service (Axios + JWT interceptor + refresh) | ✅ Done |
| T-8.3 | MatchGrid component (league-grouped) | ✅ Done |
| T-8.4 | OddsCell with flash animations | ✅ Done |
| T-8.5 | WebSocket hook + real-time updates | ✅ Done |
| T-8.6 | BetSlip (mobile drawer + desktop sidebar) | ✅ Done |
| T-8.7 | Zustand store with localStorage persistence | ✅ Done |

---

## Block 9: Frontend — Localization Updates 🔄 IN PROGRESS

| ID | Task | Priority | Status |
|----|------|----------|--------|
| T-9.1 | Update all currency displays to "KES X,XXX" format | P0 | 🔄 |
| T-9.2 | Login page: phone input with +254 prefix, PIN input (4 digits, numeric keyboard) | P0 | 🔄 |
| T-9.3 | Register page: phone validation (07XX), PIN confirmation | P0 | 🔄 |
| T-9.4 | Wallet deposit: M-Pesa flow UI ("Enter M-Pesa PIN on phone" status) | P0 | 🔄 |
| T-9.5 | Wallet withdraw: M-Pesa B2C confirmation UI | P0 | 🔄 |
| T-9.6 | Min/max validation messages in KES (stake ≥ 50, deposit ≥ 100) | P0 | 🔄 |
| T-9.7 | Admin: match status toggle (Upcoming → Live → Ended) | P1 | 🔄 |

---

## Block 10: Deployment & Integration 🔄 IN PROGRESS

| ID | Task | Priority | Status |
|----|------|----------|--------|
| T-10.1 | Update render.yaml with FIRST_ADMIN_PHONE, FIRST_ADMIN_PIN, ADMIN_SECRET_TOKEN | P0 | ✅ Done |
| T-10.2 | Add admin seeding startup hook to main.py | P0 | 🔄 |
| T-10.3 | Verify docker-compose full boot with localized config | P0 | 🔄 |
| T-10.4 | Update .env.example with all new env vars | P0 | 🔄 |
| T-10.5 | Update README.md with Kenya-localized setup instructions | P1 | 🔄 |
| T-10.6 | Commit and push to PR branch | P0 | 🔄 |

---

## Execution Priority (Current Sprint)

| Priority | Blocks | Focus |
|----------|--------|-------|
| **NOW** | 3, 4, 9, 10 | Localization pivot: admin seeding, M-Pesa simulation, KES enforcement, frontend locale |
| DONE | 1, 2, 5, 6, 7, 8 | Core infrastructure, models, APIs, real-time, frontend shell |

---

## Phase 3/4 Implementation Checklist (Current)

### Backend Updates Required:
- [ ] `config.py` — Add FIRST_ADMIN_PHONE, FIRST_ADMIN_PIN, ADMIN_SECRET_TOKEN, currency limits
- [ ] `main.py` — Add startup event for admin auto-seeding
- [ ] `routers/auth.py` — Phone format validation (07XX/+254), PIN 4-digit check
- [ ] `routers/wallet.py` — KES min/max enforcement, M-Pesa STK Push simulation, Daraja webhook
- [ ] `models/wallet.py` — Add checkout_request_id to Transaction
- [ ] `.env.example` — Add all new environment variables

### Frontend Updates Required:
- [ ] `pages/Login.tsx` — Phone + PIN (numeric keypad hint)
- [ ] `pages/Register.tsx` — Phone format help, 4-digit PIN
- [ ] `pages/WalletPage.tsx` — M-Pesa deposit flow UI, KES formatting
- [ ] `components/BetSlip.tsx` — KES formatting, min stake warning
- [ ] `pages/MyBets.tsx` — KES formatting
- [ ] `pages/AdminDashboard.tsx` — Match status control, KES formatting
- [ ] All components — Consistent "KES" prefix on monetary values

---

*Built by P.o.Riot | Credits P.o.Riot*
