from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import auth, matches, tickets, wallet, admin

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="JustBet Sportsbook API — Built by P.o.Riot",
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
    return {"status": "healthy", "service": "api", "credits": "Built by P.o.Riot"}


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(matches.router, prefix="/api", tags=["Matches"])
app.include_router(tickets.router, prefix="/api/tickets", tags=["Tickets"])
app.include_router(wallet.router, prefix="/api/wallet", tags=["Wallet"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
