import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from app.config import get_settings
from app.database import AsyncSessionLocal
from app.routers import auth, matches, tickets, wallet, admin

settings = get_settings()
logger = logging.getLogger("justbet.startup")


async def seed_first_admin():
    """Auto-seed admin account on first boot if FIRST_ADMIN_PHONE is configured."""
    if not settings.FIRST_ADMIN_PHONE or not settings.FIRST_ADMIN_PIN:
        return

    from app.models.user import User, UserRole
    from app.models.wallet import Wallet
    from app.auth import hash_password

    async with AsyncSessionLocal() as db:
        # Check if any users exist
        result = await db.execute(select(func.count(User.id)))
        user_count = result.scalar() or 0

        if user_count > 0:
            return  # Users already exist, skip seeding

        # Create first admin
        admin_user = User(
            phone=settings.FIRST_ADMIN_PHONE,
            password_hash=hash_password(settings.FIRST_ADMIN_PIN),
            role=UserRole.ADMIN,
        )
        db.add(admin_user)
        await db.flush()

        # Create admin wallet
        admin_wallet = Wallet(user_id=admin_user.id)
        db.add(admin_wallet)
        await db.commit()

        logger.info(
            f"First admin seeded: phone={settings.FIRST_ADMIN_PHONE}, role=admin"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — seed admin on startup."""
    await seed_first_admin()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    description="JustBet Sportsbook API — Kenya (KES) — Built by P.o.Riot",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "api",
        "currency": settings.DEFAULT_CURRENCY,
        "credits": "Built by P.o.Riot",
    }


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(matches.router, prefix="/api", tags=["Matches"])
app.include_router(tickets.router, prefix="/api/tickets", tags=["Tickets"])
app.include_router(wallet.router, prefix="/api/wallet", tags=["Wallet"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
