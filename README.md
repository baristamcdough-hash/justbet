# JustBet — Real-Time Sportsbook Platform

> **Built by P.o.Riot** | Credits P.o.Riot

A production-ready, mobile-first sports betting web application featuring real-time odds streaming via WebSockets, accumulator bet slips, wallet management, and a full admin dashboard with match settlement capabilities.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| State | Zustand (bet slip) + React Query (server state) |
| Real-Time | WebSocket + Redis Pub/Sub |
| Backend | Python 3.12 + FastAPI |
| Database | PostgreSQL 16 + SQLAlchemy (async) |
| Cache | Redis 7 |
| Auth | JWT (access + refresh tokens) + bcrypt |
| Containers | Docker + Docker Compose |

---

## Features

### Punter (End User)
- Browse live & upcoming matches grouped by league
- Real-time odds updates with green/red flash indicators
- Mobile slide-up bet slip drawer / desktop sticky sidebar
- Accumulator bet placement with instant potential win calculation
- Phone + PIN authentication
- Wallet with deposits (simulated M-Pesa) and withdrawals
- Full transaction history & bet history

### Admin / Operator
- Create leagues and matches with initial odds
- Live odds updates (pushed in real-time to all connected clients)
- Match settlement with automatic payout to winning tickets
- Financial liability dashboard per active match
- Aggregate stats (users, active bets, total stakes)

---

## Quick Start

### Prerequisites
- Docker & Docker Compose installed
- Git

### 1. Clone & Configure
```bash
git clone <repository-url>
cd justbet
cp .env.example .env
```

### 2. Start All Services
```bash
docker-compose up --build
```

### 3. Access the Application
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| WebSocket | ws://localhost:8001/ws/odds |

### 4. Run Database Migrations
```bash
docker-compose exec api alembic upgrade head
```

### 5. Seed Demo Data (Optional)
```bash
docker-compose exec api python -m app.seed
```

---

## Project Structure

```
justbet/
├── backend/
│   ├── app/
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── routers/      # FastAPI route handlers
│   │   ├── auth.py       # JWT + bcrypt auth utilities
│   │   ├── config.py     # Pydantic settings
│   │   ├── database.py   # Async engine & session
│   │   ├── redis_client.py
│   │   ├── main.py       # API entry point
│   │   └── ws_server.py  # WebSocket entry point
│   ├── alembic/          # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # MatchGrid, BetSlip, OddsCell, Navbar, Footer
│   │   ├── pages/        # Home, Login, Register, Wallet, MyBets, Admin
│   │   ├── stores/       # Zustand (betSlip, auth)
│   │   ├── services/     # API client, WebSocket service
│   │   ├── hooks/        # useWebSocket
│   │   ├── types/        # TypeScript interfaces
│   │   └── App.tsx       # Router + Layout
│   ├── Dockerfile
│   └── package.json
├── docs/
│   ├── requirements.md   # EARS notation requirements
│   ├── design.md         # System architecture
│   └── tasks.md          # Implementation breakdown
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## API Endpoints

### Public
- `GET /api/matches` — Match grid (grouped by league)
- `GET /api/leagues` — All leagues

### Auth
- `POST /api/auth/register` — Register (phone + password)
- `POST /api/auth/login` — Login → JWT tokens
- `POST /api/auth/refresh` — Refresh access token
- `GET /api/auth/me` — Current user profile

### Protected (JWT Required)
- `POST /api/tickets` — Place bet
- `GET /api/tickets` — List my tickets
- `GET /api/wallet` — Wallet balance
- `POST /api/wallet/deposit` — Deposit funds
- `POST /api/wallet/withdraw` — Withdraw funds
- `GET /api/wallet/transactions` — Transaction history

### Admin Only
- `POST /api/admin/leagues` — Create league
- `POST /api/admin/matches` — Create match
- `PATCH /api/admin/matches/{id}/odds` — Update odds (triggers WebSocket broadcast)
- `POST /api/admin/matches/{id}/settle` — Settle match (auto-payout)
- `GET /api/admin/liability` — Liability per match
- `GET /api/admin/dashboard` — Aggregate stats

---

## Architecture Highlights

- **Real-Time Odds:** Admin updates odds → Redis PUBLISH → WS Server SUBSCRIBEs → broadcasts to all connected clients within 500ms
- **Atomic Wallet Operations:** Row-level locking (SELECT FOR UPDATE) prevents race conditions on balance mutations
- **Idempotent Settlement:** Re-settling a match produces zero duplicate payouts (reference_id guard)
- **Mobile-First:** All components designed for 360px minimum, with breakpoints at 768px and 1280px

---

## License

Private — All rights reserved.

---

*Built by P.o.Riot | Credits P.o.Riot*
