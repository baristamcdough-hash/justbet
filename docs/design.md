# JustBet Sportsbook — System Architecture & Technical Design (v2 Kenya)

> **Version:** 2.0 — Localized Kenyan Sportsbook  
> **Date:** 2026-05-17  
> **Market:** Kenya (KES · M-Pesa · Safaricom)  
> **Credits:** Built by P.o.Riot  

---

## 1. High-Level Architecture — Multi-Container Deployment

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          RENDER CLOUD (Oregon Region)                             │
├───────────────┬───────────────┬────────────────┬──────────────┬────────────────┤
│  Static Site  │  Web Service  │  Background    │  PostgreSQL  │  Redis KV      │
│  (Frontend)   │  (API + WS)   │  Worker        │  (Basic)     │  (Starter)     │
│  React/Vite   │  FastAPI      │  Settlement    │  Port 5432   │  Port 6379     │
│  Port 443     │  Port $PORT   │  Loop          │              │                │
└──────┬────────┴──────┬────────┴───────┬────────┴──────┬───────┴───────┬────────┘
       │               │                │               │               │
       │  HTTPS REST   │                │  SQL (asyncpg)│  Pub/Sub +    │
       │◄─────────────►│                │◄─────────────►│  Cache KV     │
       │               │  Internal Net  │               │◄─────────────►│
       │  WSS://       │◄──────────────►│               │               │
       │◄─────────────►│                │  Internal Net │               │
       │               │                │◄─────────────────────────────►│
       └───────────────┴────────────────┴───────────────┴───────────────┘
                              Render Private Networking
```

### Service Inventory

| Service | Runtime | Plan | Start Command | Purpose |
|---------|---------|------|---------------|---------|
| `justbet-frontend` | Static (Node 20) | Starter | `npm run build` → `dist/` | React SPA; mobile-first match grid & bet slip |
| `justbet-api` | Python 3.12 | Starter | `uvicorn app.main:app --port $PORT --workers 2` | REST API + embedded WebSocket endpoint |
| `justbet-settlement-worker` | Python 3.12 | Starter | `python -m app.worker` | Async payout processing loop |
| `justbet-db` | PostgreSQL 16 | Basic | Managed | User/wallet/ticket/match persistent storage |
| `justbet-redis` | Redis 7 | Starter | Managed | Pub/Sub broker + live odds cache |

---

## 2. Real-Time Odds Engine — Redis Pub/Sub + WebSocket

```
┌───────────┐    PATCH /api/admin/matches/{id}/odds   ┌───────────────┐
│   Admin   │────────────────────────────────────────►│  API Service  │
│  Browser  │                                          │  (FastAPI)    │
└───────────┘                                          └───────┬───────┘
                                                               │
                                                    ┌──────────┴──────────┐
                                                    │ 1. UPDATE matches   │
                                                    │    SET odds = new   │
                                                    │ 2. INSERT match_odds│
                                                    │    (history record) │
                                                    │ 3. PUBLISH Redis    │
                                                    │    "odds:{match_id}"│
                                                    │ 4. SETEX Redis      │
                                                    │    "odds:current:   │
                                                    │     {match_id}" 60s │
                                                    └──────────┬──────────┘
                                                               │
                                                          PUBLISH
                                                               │
                                                               ▼
                                                    ┌───────────────────┐
                                                    │   Redis Pub/Sub   │
                                                    │  channel: odds:*  │
                                                    └─────────┬─────────┘
                                                              │
                                                        SUBSCRIBE
                                                        (pattern)
                                                              │
                                                              ▼
┌──────────────┐   WebSocket JSON Frame            ┌───────────────────┐
│   Punter     │◄──────────────────────────────────│  WS Handler       │
│  (Mobile)    │                                    │  (embedded in API)│
└──────────────┘                                    └───────────────────┘
```

### WebSocket Odds Delta Frame

```json
{
  "type": "odds_update",
  "match_id": "a1b2c3d4-...",
  "timestamp": "2026-05-17T17:30:00+03:00",
  "odds": { "home": 2.15, "draw": 3.40, "away": 3.10 },
  "previous": { "home": 2.10, "draw": 3.40, "away": 3.20 }
}
```

### WebSocket Lifecycle

1. Client connects: `wss://justbet-api.onrender.com/ws/odds?token=<JWT>`
2. Server validates JWT (30min expiry) on handshake
3. Client sends: `{"action": "subscribe", "match_ids": ["uuid1", ...]}`
4. Server sends cached snapshot from Redis `odds:current:{id}`
5. Server subscribes to Redis `odds:{id}` channels via background listener
6. On PUBLISH → broadcast delta frame to subscribed clients
7. Ping/pong every 30s; client auto-reconnects on drop (1s→2s→4s→...→30s)

---

## 3. Entity-Relationship Schema (PostgreSQL 16)

```
┌────────────────────┐      ┌────────────────────┐      ┌────────────────────┐
│       users        │      │      wallets       │      │   transactions     │
├────────────────────┤      ├────────────────────┤      ├────────────────────┤
│ id (UUID) PK       │─1:1─►│ id (UUID) PK       │─1:N─►│ id (UUID) PK       │
│ phone (varchar 15) │      │ user_id FK UNIQUE   │      │ wallet_id FK       │
│   UNIQUE INDEX     │      │ real_balance DEC    │      │ type (enum)        │
│ pin_hash (bcrypt)  │      │ bonus_balance DEC   │      │ amount DEC         │
│ role (enum)        │      │ currency = 'KES'    │      │ balance_after DEC  │
│ created_at         │      │ updated_at          │      │ reference_id       │
│ updated_at         │      └────────────────────┘      │ checkout_request_id│
└────────────────────┘                                   │ status (enum)      │
                                                         │ created_at         │
                                                         └────────────────────┘

┌────────────────────┐      ┌────────────────────┐      ┌────────────────────┐
│      leagues       │      │      matches       │      │    match_odds      │
├────────────────────┤      ├────────────────────┤      ├────────────────────┤
│ id (UUID) PK       │─1:N─►│ id (UUID) PK       │─1:N─►│ id (UUID) PK       │
│ name               │      │ league_id FK       │      │ match_id FK        │
│ sport = 'football' │      │ home_team          │      │ home_odds DEC(6,2) │
│ country            │      │ away_team          │      │ draw_odds DEC(6,2) │
│ created_at         │      │ kickoff_time (EAT) │      │ away_odds DEC(6,2) │
└────────────────────┘      │ status (enum)      │      │ timestamp          │
                            │ home_score INT     │      └────────────────────┘
                            │ away_score INT     │
                            │ result (enum)      │
                            │ home_odds DEC(6,2) │ ← denormalized current
                            │ draw_odds DEC(6,2) │
                            │ away_odds DEC(6,2) │
                            │ settled_at         │
                            │ created_at         │
                            └────────────────────┘

┌────────────────────┐      ┌────────────────────┐
│      tickets       │      │    selections      │
├────────────────────┤      ├────────────────────┤
│ id (UUID) PK       │─1:N─►│ id (UUID) PK       │
│ user_id FK INDEX   │      │ ticket_id FK INDEX │
│ stake DEC(12,2)    │      │ match_id FK INDEX  │
│ total_odds DEC     │      │ market (enum)      │
│ potential_win DEC  │      │ locked_odds DEC    │
│ status (enum)      │      │ result (enum)      │
│ created_at         │      │ created_at         │
│ settled_at         │      └────────────────────┘
└────────────────────┘
```

### Enum Definitions

| Enum | Values |
|------|--------|
| `user_role` | `punter`, `admin` |
| `match_status` | `upcoming`, `live`, `ended`, `settled`, `cancelled` |
| `match_result` | `home_win`, `draw`, `away_win`, `cancelled` |
| `market_type` | `home`, `draw`, `away` |
| `selection_result` | `pending`, `won`, `lost`, `void` |
| `ticket_status` | `active`, `won`, `lost`, `void`, `cashout` |
| `transaction_type` | `deposit`, `withdrawal`, `bet_stake`, `bet_winning`, `bonus_credit`, `refund` |
| `transaction_status` | `pending`, `completed`, `failed`, `reversed` |

---

## 4. API Specification

### 4.1 Authentication (Phone + PIN)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | None | Register: phone (07XX) + 4-digit PIN → JWT |
| POST | `/api/auth/login` | None | Login: phone + PIN → access + refresh tokens |
| POST | `/api/auth/refresh` | Refresh | Rotate access token |
| GET | `/api/auth/me` | JWT | Current user profile |

### 4.2 Matches & Odds (Public — no auth)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/matches` | None | Matches grouped by league with current odds |
| GET | `/api/matches/{id}` | None | Single match + odds history |
| GET | `/api/leagues` | None | All leagues |

### 4.3 Bet Slip & Tickets (Punter)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/tickets` | JWT | Place bet: selections[] + stake (KES ≥ 50) |
| GET | `/api/tickets` | JWT | My tickets (paginated) |
| GET | `/api/tickets/{id}` | JWT | Ticket detail with selections |

### 4.4 Wallet & M-Pesa (Punter)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/wallet` | JWT | Balances (real + bonus in KES) |
| POST | `/api/wallet/deposit` | JWT | Initiate M-Pesa STK Push (KES 100–150,000) |
| POST | `/api/wallet/withdraw` | JWT | Initiate M-Pesa B2C (KES 100–70,000) |
| GET | `/api/wallet/transactions` | JWT | Transaction history (paginated) |
| POST | `/api/webhooks/mpesa/callback` | API Key | M-Pesa confirmation webhook |

### 4.5 Admin Operations

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/admin/leagues` | Admin | Create league |
| POST | `/api/admin/matches` | Admin | Create match + initial odds |
| PATCH | `/api/admin/matches/{id}/odds` | Admin | Update odds → Redis PUBLISH |
| PATCH | `/api/admin/matches/{id}/status` | Admin | Change status (upcoming→live→ended) |
| POST | `/api/admin/matches/{id}/settle` | Admin | Input score → evaluate → enqueue payouts |
| GET | `/api/admin/liability` | Admin | Liability per match (KES) |
| GET | `/api/admin/dashboard` | Admin | Aggregate stats |

### 4.6 WebSocket

| Endpoint | Auth | Description |
|----------|------|-------------|
| `wss://host/ws/odds?token=<JWT>` | JWT (query) | Real-time odds stream |

---

## 5. Settlement Worker — Background Payout Pipeline

```
┌─────────────┐   POST /admin/matches/{id}/settle   ┌─────────────────┐
│    Admin     │────────────────────────────────────►│   API Service   │
└─────────────┘                                      └────────┬────────┘
                                                              │
                                                    1. match.status = 'settled'
                                                    2. match.result = home_win|draw|away_win
                                                    3. Evaluate all selections for match
                                                    4. Mark tickets won/lost
                                                    5. For WON tickets: status = 'won'
                                                              │
                                                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    BACKGROUND WORKER (python -m app.worker)               │
│                                                                           │
│  Poll loop (every 5s):                                                   │
│    1. SELECT tickets WHERE status='won' AND no payout transaction exists │
│    2. For each winning ticket:                                           │
│       a. BEGIN TRANSACTION                                               │
│       b. SELECT wallet FOR UPDATE (row lock)                             │
│       c. Idempotency: check reference_id not already used               │
│       d. wallet.real_balance += ticket.potential_win                     │
│       e. INSERT transaction (type=bet_winning, ref=ticket.id)            │
│       f. COMMIT                                                          │
│    3. On failure: retry with backoff 2s → 4s → 8s (max 3 attempts)      │
│    4. After 3 failures: log CRITICAL, skip ticket, alert admin           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Idempotency Guarantee

- `reference_id` = ticket UUID in transaction table
- Worker checks `WHERE reference_id = ticket.id AND type = 'bet_winning'` before processing
- Re-running settlement on same match → zero new transactions

---

## 6. M-Pesa Integration (Simulated Daraja API)

### Deposit Flow (STK Push Simulation)

```
Punter                    API                     "M-Pesa" (Simulated)
  │                        │                              │
  │  POST /wallet/deposit  │                              │
  │  {amount: 500, phone}  │                              │
  │───────────────────────►│                              │
  │                        │  Create pending transaction  │
  │                        │  Generate checkout_request_id│
  │                        │                              │
  │  ◄─── 200 OK ─────────│                              │
  │  "Enter M-Pesa PIN"   │                              │
  │                        │──── (auto after 3s) ────────►│
  │                        │                              │
  │                        │◄─── Callback ───────────────│
  │                        │  {ResultCode: 0, Amount}     │
  │                        │                              │
  │                        │  Credit wallet               │
  │                        │  Mark txn completed          │
  │  ◄─── WS notification─│                              │
  │  "Deposit confirmed"  │                              │
```

### Request/Response Format (Daraja-style)

**STK Push Request:**
```json
{
  "BusinessShortCode": "174379",
  "TransactionType": "CustomerPayBillOnline",
  "Amount": 500,
  "PartyA": "254712345678",
  "PartyB": "174379",
  "PhoneNumber": "254712345678",
  "AccountReference": "JustBet",
  "TransactionDesc": "Deposit"
}
```

**Callback (simulated):**
```json
{
  "Body": {
    "stkCallback": {
      "MerchantRequestID": "uuid",
      "CheckoutRequestID": "ws_CO_xxxxx",
      "ResultCode": 0,
      "ResultDesc": "The service request is processed successfully.",
      "CallbackMetadata": {
        "Item": [
          {"Name": "Amount", "Value": 500.00},
          {"Name": "MpesaReceiptNumber", "Value": "QKJ3A9B7ZP"},
          {"Name": "PhoneNumber", "Value": 254712345678}
        ]
      }
    }
  }
}
```

---

## 7. Admin Console Specification

### Dashboard View
- **Stat Cards:** Total Users | Active Tickets | Total Stakes (KES) | Total Liability (KES)
- **Liability Table:** Per-match breakdown of `sum(potential_win)` for active tickets

### Match Management
- **Create Match:** League dropdown, Home/Away teams, Kickoff (EAT), Initial odds (1/X/2)
- **Update Odds:** Real-time slider/input per outcome → saves + publishes to Redis instantly
- **Change Status:** Buttons to transition: Upcoming → Live → Ended

### Settlement Panel
- **Select Match** (from ended matches list)
- **Input Score:** Home goals / Away goals
- **Settle Button:** Triggers `/api/admin/matches/{id}/settle`
- **Result Display:** Shows tickets processed, won/lost counts, total payout amount

### Environment-Based Admin Seeding
```
FIRST_ADMIN_PHONE=0712345678
FIRST_ADMIN_PIN=1234
ADMIN_SECRET_TOKEN=super-secret-admin-creation-key
```
On first boot (empty users table), the system auto-creates:
```python
User(phone="0712345678", pin_hash=bcrypt("1234"), role="admin")
Wallet(user_id=admin.id, real_balance=0, bonus_balance=0)
```

---

## 8. Caching Strategy (Redis)

| Key Pattern | Value | TTL | Purpose |
|-------------|-------|-----|---------|
| `odds:current:{match_id}` | JSON `{home, draw, away}` | 60s | Serve to new WS subscribers |
| `match:list:active` | JSON array of active matches | 30s | Fast match listing cache |
| `ratelimit:{ip}:{endpoint}` | Request counter | 60s | Per-IP rate limiting |
| `mpesa:checkout:{id}` | Pending deposit metadata | 300s | Track STK Push status |

---

## 9. Frontend Architecture (React 18 + TypeScript)

```
frontend/src/
├── components/
│   ├── MatchGrid.tsx       # League-grouped, compact, touch-optimized
│   ├── OddsCell.tsx        # 1/X/2 button with flash animation
│   ├── BetSlip.tsx         # Mobile drawer + desktop sidebar
│   ├── Navbar.tsx          # Logo, wallet badge, nav links
│   └── Footer.tsx          # "Built by P.o.Riot" permanent credit
├── pages/
│   ├── Home.tsx            # Match grid (default route)
│   ├── Login.tsx           # Phone + PIN form
│   ├── Register.tsx        # Phone + PIN + confirm PIN
│   ├── WalletPage.tsx      # KES balance, M-Pesa deposit/withdraw
│   ├── MyBets.tsx          # Ticket list with status badges
│   └── AdminDashboard.tsx  # Stats, match CRUD, settlement, odds update
├── stores/
│   ├── authStore.ts        # Zustand: user, tokens, login/logout
│   └── betSlipStore.ts     # Zustand: selections, stake, totals (persisted)
├── services/
│   ├── api.ts              # Axios with JWT interceptor + auto-refresh
│   └── ws.ts               # WebSocket singleton with reconnect
├── hooks/
│   └── useWebSocket.ts     # Subscribe to match odds channels
├── types/
│   └── index.ts            # TypeScript interfaces
└── App.tsx                 # Router + Layout + Footer
```

### State Management

| Concern | Solution |
|---------|----------|
| Server data (matches, tickets, wallet) | React Query (staleTime: 30s) |
| Real-time odds | WebSocket → Zustand → React Query cache invalidation |
| Bet slip | Zustand with `persist` middleware → localStorage |
| Auth | Zustand with token storage + auto-refresh interceptor |

---

## 10. Security Architecture

| Layer | Implementation |
|-------|---------------|
| Network | CORS (frontend origin only); rate limiting; HTTPS everywhere (Render default) |
| Auth | JWT HS256; access 30min + refresh 30d; PIN bcrypt(12) |
| Authorization | Role enum in JWT claims; admin guard middleware |
| Data | Row-level locking on wallets; immutable transaction ledger; idempotent settlement |
| Secrets | `JWT_SECRET` auto-generated; `FIRST_ADMIN_PIN` env-only; `ADMIN_SECRET_TOKEN` for admin creation |
| WS | Token-in-query validated on handshake; reject 4001 on invalid |

---

## 11. Render Deployment Topology

```yaml
# render.yaml provisions:
databases:
  - justbet-db (PostgreSQL 16, Basic plan)

services:
  - justbet-frontend (Static Site, Vite build)
  - justbet-api (Web Service, FastAPI, Starter plan)
  - justbet-settlement-worker (Background Worker)

keyValueStores:
  - justbet-redis (Starter plan, allkeys-lru)

# Environment variables include:
# FIRST_ADMIN_PHONE, FIRST_ADMIN_PIN, ADMIN_SECRET_TOKEN
# JWT_SECRET (auto-generated), DATABASE_URL, REDIS_URL
```

All services communicate via Render's internal private networking (10.x.x.x). External traffic hits only the frontend static site and API web service via HTTPS.

---

*Built by P.o.Riot | Credits P.o.Riot*
