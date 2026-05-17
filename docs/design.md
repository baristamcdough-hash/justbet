# JustBet Sportsbook — System Architecture & Technical Design

> **Version:** 1.0  
> **Date:** 2026-05-17  
> **Credits:** Built by P.o.Riot  

---

## 1. High-Level Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DOCKER COMPOSE                                  │
├─────────────┬─────────────┬─────────────────┬──────────────┬───────────────┤
│  Frontend   │   API       │  WS Server      │  PostgreSQL  │    Redis      │
│  (React+    │  (FastAPI)  │  (FastAPI WS)   │  (Port 5432) │  (Port 6379)  │
│   Vite)     │  Port 8000  │  Port 8001      │              │               │
│  Port 3000  │             │                 │              │               │
└──────┬──────┴──────┬──────┴────────┬────────┴──────┬───────┴───────┬───────┘
       │             │               │               │               │
       │  HTTP/REST  │               │  SQL/ORM      │  Pub/Sub +    │
       │◄───────────►│               │◄─────────────►│  Cache Get/Set│
       │             │               │               │◄─────────────►│
       │  WebSocket  │               │               │               │
       │◄────────────────────────────►│               │               │
       │             │  Publish Odds │               │               │
       │             │──────────────►│───────────────────────────────►│
       │             │               │  Subscribe    │               │
       │             │               │◄──────────────────────────────│
       └─────────────┴───────────────┴───────────────┴───────────────┘
```

### Container Services

| Service | Image/Build | Port | Purpose |
|---------|-------------|------|---------|
| `frontend` | Node 20 + Vite | 3000 | React SPA serving mobile-first UI |
| `api` | Python 3.12 + FastAPI | 8000 | REST API (auth, wallet, admin, matches, bets) |
| `ws` | Python 3.12 + FastAPI | 8001 | Dedicated WebSocket server for odds streaming |
| `postgres` | postgres:16-alpine | 5432 | Persistent data store |
| `redis` | redis:7-alpine | 6379 | Pub/Sub message bus + odds cache |

---

## 2. Real-Time Odds Streaming — Redis Pub/Sub + WebSocket Flow

```
┌───────────┐    POST /admin/matches/{id}/odds    ┌───────────┐
│   Admin   │────────────────────────────────────►│  API      │
│  Console  │                                      │  Server   │
└───────────┘                                      └─────┬─────┘
                                                         │
                                                    PUBLISH to
                                                  "odds:{match_id}"
                                                         │
                                                         ▼
                                                   ┌───────────┐
                                                   │   Redis    │
                                                   │  Pub/Sub   │
                                                   └─────┬─────┘
                                                         │
                                                    SUBSCRIBE
                                                  "odds:{match_id}"
                                                         │
                                                         ▼
┌───────────┐     WebSocket frame (JSON)          ┌───────────┐
│  Punter   │◄────────────────────────────────────│    WS     │
│  Browser  │                                      │  Server   │
└───────────┘                                      └───────────┘
```

### Message Format (Odds Delta)

```json
{
  "type": "odds_update",
  "match_id": "uuid",
  "timestamp": "2026-05-17T14:30:00Z",
  "odds": {
    "home": 2.15,
    "draw": 3.40,
    "away": 3.10
  },
  "previous": {
    "home": 2.10,
    "draw": 3.40,
    "away": 3.20
  }
}
```

### WebSocket Connection Lifecycle

1. Client connects: `ws://host:8001/ws/odds?token=<JWT>`
2. Server validates JWT in handshake
3. Client sends subscription: `{"action": "subscribe", "match_ids": ["uuid1", "uuid2"]}`
4. Server subscribes to Redis channels `odds:uuid1`, `odds:uuid2`
5. On publish → server forwards delta frame to client
6. On disconnect → server unsubscribes from Redis channels
7. Client auto-reconnects with exponential backoff (1s → 2s → 4s → ... → 30s max)

---

## 3. Entity-Relationship Schema

```
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│      users       │       │     wallets      │       │  transactions    │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ id (UUID) PK     │──1:1─►│ id (UUID) PK     │──1:N─►│ id (UUID) PK     │
│ phone (unique)   │       │ user_id FK       │       │ wallet_id FK     │
│ password_hash    │       │ real_balance     │       │ type (enum)      │
│ role (enum)      │       │ bonus_balance    │       │ amount (decimal) │
│ created_at       │       │ updated_at       │       │ balance_after    │
│ updated_at       │       └──────────────────┘       │ reference_id     │
└──────────────────┘                                   │ status (enum)    │
                                                       │ created_at       │
                                                       └──────────────────┘

┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│     leagues      │       │     matches      │       │   match_odds     │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ id (UUID) PK     │──1:N─►│ id (UUID) PK     │──1:N─►│ id (UUID) PK     │
│ name             │       │ league_id FK     │       │ match_id FK      │
│ sport            │       │ home_team        │       │ home_odds        │
│ country          │       │ away_team        │       │ draw_odds        │
│ created_at       │       │ kickoff_time     │       │ away_odds        │
└──────────────────┘       │ status (enum)    │       │ timestamp        │
                           │ home_score       │       └──────────────────┘
                           │ away_score       │
                           │ result (enum)    │
                           │ settled_at       │
                           │ created_at       │
                           └──────────────────┘

┌──────────────────┐       ┌──────────────────┐
│     tickets      │       │   selections     │
├──────────────────┤       ├──────────────────┤
│ id (UUID) PK     │──1:N─►│ id (UUID) PK     │
│ user_id FK       │       │ ticket_id FK     │
│ stake (decimal)  │       │ match_id FK      │
│ total_odds       │       │ market (enum)    │
│ potential_win    │       │ locked_odds      │
│ status (enum)    │       │ result (enum)    │
│ created_at       │       │ created_at       │
│ settled_at       │       └──────────────────┘
└──────────────────┘
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

### 4.1 Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | None | Register with phone + password |
| POST | `/api/auth/login` | None | Login → JWT access + refresh tokens |
| POST | `/api/auth/refresh` | Refresh Token | Get new access token |
| GET | `/api/auth/me` | JWT | Get current user profile |

### 4.2 Matches & Odds (Public)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/matches` | None | List matches (grouped by league, with current odds) |
| GET | `/api/matches/{id}` | None | Get single match with full odds history |
| GET | `/api/leagues` | None | List all leagues |

### 4.3 Bet Slip & Tickets

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/tickets` | JWT | Place a bet (array of selections + stake) |
| GET | `/api/tickets` | JWT | List user's tickets with status |
| GET | `/api/tickets/{id}` | JWT | Get ticket details |

### 4.4 Wallet & Transactions

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/wallet` | JWT | Get wallet balances |
| POST | `/api/wallet/deposit` | JWT | Initiate deposit (simulated M-Pesa) |
| POST | `/api/wallet/withdraw` | JWT | Initiate withdrawal |
| GET | `/api/wallet/transactions` | JWT | List transaction history |
| POST | `/api/webhooks/payment` | API Key | Payment gateway callback |

### 4.5 Admin Operations

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/admin/leagues` | Admin | Create league |
| POST | `/api/admin/matches` | Admin | Create match with initial odds |
| PATCH | `/api/admin/matches/{id}/odds` | Admin | Update live odds (triggers Redis publish) |
| POST | `/api/admin/matches/{id}/settle` | Admin | Settle match with result |
| GET | `/api/admin/liability` | Admin | Get liability per match |
| GET | `/api/admin/dashboard` | Admin | Aggregate stats (active bets, revenue, users) |

### 4.6 WebSocket

| Endpoint | Auth | Description |
|----------|------|-------------|
| `ws://host:8001/ws/odds?token=<JWT>` | JWT (query) | Real-time odds stream |

---

## 5. Settlement Worker — Async Payout Pipeline

```
┌───────────┐     POST /admin/matches/{id}/settle     ┌───────────┐
│   Admin   │────────────────────────────────────────►│  API      │
└───────────┘                                          └─────┬─────┘
                                                             │
                                                    1. Mark match as "settled"
                                                    2. Query all tickets with 
                                                       selections on this match
                                                    3. Evaluate each selection
                                                    4. For fully-won tickets:
                                                             │
                                                             ▼
                                                    ┌───────────────┐
                                                    │  Background   │
                                                    │  Task Queue   │
                                                    │  (asyncio)    │
                                                    └───────┬───────┘
                                                            │
                                                   For each winning ticket:
                                                            │
                                                            ▼
                                              ┌─────────────────────────────┐
                                              │  BEGIN TRANSACTION          │
                                              │  1. Lock wallet row (FOR    │
                                              │     UPDATE)                 │
                                              │  2. Credit real_balance     │
                                              │     += stake × locked_odds  │
                                              │  3. Insert transaction      │
                                              │     record                  │
                                              │  4. Update ticket status    │
                                              │     = 'won'                 │
                                              │  COMMIT                     │
                                              └─────────────────────────────┘
                                                            │
                                                   On Failure (max 3 retries):
                                                            │
                                                            ▼
                                              ┌─────────────────────────────┐
                                              │  Exponential Backoff:       │
                                              │  Retry 1: 2s               │
                                              │  Retry 2: 4s               │
                                              │  Retry 3: 8s               │
                                              │  → Alert Admin on failure  │
                                              └─────────────────────────────┘
```

### Idempotency Guarantee

- Each ticket settlement is guarded by a status check: only tickets in `active` status are processed
- The ticket ID is used as an idempotency key in the transaction `reference_id`
- Re-running settlement on an already-settled match produces zero new transactions

---

## 6. Caching Strategy (Redis)

| Key Pattern | Value | TTL | Purpose |
|-------------|-------|-----|---------|
| `odds:current:{match_id}` | JSON odds snapshot | 60s | Serve latest odds to new WS connections |
| `match:list:active` | JSON array of active matches | 30s | Fast match listing without DB query |
| `session:{user_id}` | JWT metadata | 15min | Rate limit tracking |
| `ratelimit:{ip}` | Request counter | 60s | Anonymous rate limiting |

---

## 7. Frontend Architecture

```
src/
├── components/
│   ├── MatchGrid/          # League-grouped match list with odds cells
│   ├── BetSlip/            # Drawer (mobile) / Sidebar (desktop)
│   ├── OddsCell/           # Individual odds button with flash animation
│   ├── Wallet/             # Balance display, deposit/withdraw forms
│   ├── Auth/               # Login/Register forms
│   └── Admin/              # Dashboard, match management, settlement
├── hooks/
│   ├── useWebSocket.ts     # WebSocket connection manager with reconnect
│   ├── useBetSlip.ts       # Bet slip state management
│   └── useAuth.ts          # JWT token management
├── stores/
│   └── betSlipStore.ts     # Zustand store for bet selections
├── services/
│   ├── api.ts              # Axios/fetch wrapper with interceptors
│   └── ws.ts               # WebSocket client singleton
├── pages/
│   ├── Home.tsx            # Match grid (default view)
│   ├── MyBets.tsx          # Ticket history
│   ├── WalletPage.tsx      # Wallet management
│   └── AdminDashboard.tsx  # Admin panel
├── types/
│   └── index.ts            # TypeScript interfaces
└── App.tsx                 # Router + layout + footer ("Built by P.o.Riot")
```

### State Management

| Concern | Solution |
|---------|----------|
| Server state (matches, tickets) | React Query with 30s stale time |
| Real-time odds | WebSocket → Zustand store → React Query cache invalidation |
| Bet slip selections | Zustand (persisted to localStorage) |
| Auth tokens | React Context + httpOnly cookies (refresh) |

### Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| < 360px | Compact single-column, collapsed odds |
| 360–768px | Mobile: full match grid, bottom bet slip drawer |
| 768–1280px | Tablet: 2-column, floating bet slip |
| > 1280px | Desktop: 3-column grid + sticky right sidebar |

---

## 8. Security Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Security Layers                      │
├─────────────────────────────────────────────────────┤
│ Layer 1: Network                                     │
│   • CORS whitelist (frontend origin only)           │
│   • Rate limiting (100/min auth, 30/min anon)       │
│   • Request size limits (1MB max body)              │
├─────────────────────────────────────────────────────┤
│ Layer 2: Authentication                              │
│   • JWT RS256 signing (access: 15min, refresh: 7d)  │
│   • Password hashing: bcrypt cost=12               │
│   • WebSocket auth via query token                  │
├─────────────────────────────────────────────────────┤
│ Layer 3: Authorization                               │
│   • Role-based: punter vs admin                     │
│   • Resource ownership validation                   │
│   • Admin endpoints isolated under /api/admin/*     │
├─────────────────────────────────────────────────────┤
│ Layer 4: Data Integrity                              │
│   • Row-level locking on wallet operations          │
│   • Immutable transaction ledger                    │
│   • Idempotent settlement operations               │
└─────────────────────────────────────────────────────┘
```

---

## 9. Docker Compose Topology

```yaml
# Simplified schema (full file in /docker-compose.yml)
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [api]
    environment:
      - VITE_API_URL=http://api:8000
      - VITE_WS_URL=ws://ws:8001

  api:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [postgres, redis]
    environment:
      - DATABASE_URL=postgresql+asyncpg://...
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET=...

  ws:
    build: ./backend
    command: uvicorn ws_server:app --host 0.0.0.0 --port 8001
    ports: ["8001:8001"]
    depends_on: [redis]
    environment:
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET=...

  postgres:
    image: postgres:16-alpine
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

volumes:
  pgdata:
```

---

## 10. Deployment & Scaling Notes

| Concern | Strategy |
|---------|----------|
| Horizontal WS scaling | Multiple `ws` containers + Redis Pub/Sub ensures all clients receive updates regardless of which node they're connected to |
| Database migrations | Alembic (Python) — auto-run on API container startup via entrypoint script |
| Zero-downtime deploy | Rolling updates via Docker Compose profiles or orchestrator |
| Monitoring | Structured JSON logging → stdout (Docker captures); health check endpoints |
| Backup | PostgreSQL pg_dump scheduled via cron container or external job |

---

*Built by P.o.Riot | Credits P.o.Riot*
