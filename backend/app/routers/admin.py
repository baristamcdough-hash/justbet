import json
import asyncio
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import List, Optional
from app.database import get_db
from app.models.user import User
from app.models.wallet import Wallet, Transaction, TransactionType, TransactionStatus
from app.models.match import League, Match, MatchOdds, MatchStatus, MatchResult
from app.models.ticket import Ticket, Selection, TicketStatus, SelectionResult, MarketType
from app.auth import get_admin_user
from app.redis_client import get_redis

router = APIRouter()


class CreateLeagueRequest(BaseModel):
    name: str
    sport: str = "football"
    country: Optional[str] = None


class CreateMatchRequest(BaseModel):
    league_id: str
    home_team: str
    away_team: str
    kickoff_time: str
    home_odds: float
    draw_odds: float
    away_odds: float


class UpdateOddsRequest(BaseModel):
    home_odds: float
    draw_odds: float
    away_odds: float


class SettleMatchRequest(BaseModel):
    home_score: int
    away_score: int


class LiabilityResponse(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    total_stakes: float
    total_potential_payout: float
    active_tickets: int


class DashboardResponse(BaseModel):
    total_users: int
    active_tickets: int
    total_stakes_today: float
    total_liability: float


@router.post("/leagues", status_code=status.HTTP_201_CREATED)
async def create_league(
    req: CreateLeagueRequest,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    league = League(name=req.name, sport=req.sport, country=req.country)
    db.add(league)
    await db.commit()
    await db.refresh(league)
    return {"id": league.id, "name": league.name, "sport": league.sport, "country": league.country}


@router.post("/matches", status_code=status.HTTP_201_CREATED)
async def create_match(
    req: CreateMatchRequest,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate league exists
    league_result = await db.execute(select(League).where(League.id == req.league_id))
    if not league_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="League not found")

    match = Match(
        league_id=req.league_id,
        home_team=req.home_team,
        away_team=req.away_team,
        kickoff_time=datetime.fromisoformat(req.kickoff_time),
        home_odds=Decimal(str(req.home_odds)),
        draw_odds=Decimal(str(req.draw_odds)),
        away_odds=Decimal(str(req.away_odds)),
        status=MatchStatus.UPCOMING,
    )
    db.add(match)
    await db.flush()

    # Record initial odds in history
    odds_record = MatchOdds(
        match_id=match.id,
        home_odds=match.home_odds,
        draw_odds=match.draw_odds,
        away_odds=match.away_odds,
    )
    db.add(odds_record)
    await db.commit()
    await db.refresh(match)

    # Cache in Redis
    redis = get_redis()
    await redis.setex(
        f"odds:current:{match.id}",
        60,
        json.dumps({
            "home": float(match.home_odds),
            "draw": float(match.draw_odds),
            "away": float(match.away_odds),
        }),
    )

    return {
        "id": match.id,
        "home_team": match.home_team,
        "away_team": match.away_team,
        "kickoff_time": match.kickoff_time.isoformat(),
        "odds": {
            "home": float(match.home_odds),
            "draw": float(match.draw_odds),
            "away": float(match.away_odds),
        },
    }


@router.patch("/matches/{match_id}/odds")
async def update_odds(
    match_id: str,
    req: UpdateOddsRequest,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update match odds and publish to Redis for real-time broadcast."""
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    if match.status in (MatchStatus.SETTLED, MatchStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="Cannot update odds for settled/cancelled match")

    # Store previous odds for delta
    previous = {
        "home": float(match.home_odds),
        "draw": float(match.draw_odds),
        "away": float(match.away_odds),
    }

    # Update match odds
    match.home_odds = Decimal(str(req.home_odds))
    match.draw_odds = Decimal(str(req.draw_odds))
    match.away_odds = Decimal(str(req.away_odds))

    # Record in odds history
    odds_record = MatchOdds(
        match_id=match.id,
        home_odds=match.home_odds,
        draw_odds=match.draw_odds,
        away_odds=match.away_odds,
    )
    db.add(odds_record)
    await db.commit()

    # Publish to Redis
    new_odds = {
        "home": float(match.home_odds),
        "draw": float(match.draw_odds),
        "away": float(match.away_odds),
    }

    redis = get_redis()
    message = json.dumps({
        "type": "odds_update",
        "match_id": match_id,
        "timestamp": datetime.utcnow().isoformat(),
        "odds": new_odds,
        "previous": previous,
    })

    # Publish to channel and update cache
    await redis.publish(f"odds:{match_id}", message)
    await redis.setex(f"odds:current:{match_id}", 60, json.dumps(new_odds))

    return {"match_id": match_id, "odds": new_odds, "previous": previous}


@router.post("/matches/{match_id}/settle")
async def settle_match(
    match_id: str,
    req: SettleMatchRequest,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Settle a match and process winning tickets."""
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    if match.status == MatchStatus.SETTLED:
        raise HTTPException(status_code=400, detail="Match already settled")

    # Determine result
    match.home_score = req.home_score
    match.away_score = req.away_score

    if req.home_score > req.away_score:
        match.result = MatchResult.HOME_WIN
    elif req.home_score < req.away_score:
        match.result = MatchResult.AWAY_WIN
    else:
        match.result = MatchResult.DRAW

    match.status = MatchStatus.SETTLED
    match.settled_at = datetime.utcnow()

    # Map result to winning market
    winning_market = {
        MatchResult.HOME_WIN: MarketType.HOME,
        MatchResult.DRAW: MarketType.DRAW,
        MatchResult.AWAY_WIN: MarketType.AWAY,
    }[match.result]

    # Get all selections for this match
    sel_result = await db.execute(
        select(Selection)
        .where(Selection.match_id == match_id, Selection.result == SelectionResult.PENDING)
        .options(selectinload(Selection.ticket))
    )
    selections = sel_result.scalars().all()

    # Evaluate each selection
    for sel in selections:
        if sel.market == winning_market:
            sel.result = SelectionResult.WON
        else:
            sel.result = SelectionResult.LOST

    await db.commit()

    # Now evaluate all affected tickets
    ticket_ids = set(sel.ticket_id for sel in selections)
    for ticket_id in ticket_ids:
        ticket_result = await db.execute(
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .options(selectinload(Ticket.selections))
        )
        ticket = ticket_result.scalar_one_or_none()
        if not ticket or ticket.status != TicketStatus.ACTIVE:
            continue

        # Check if all selections are resolved
        all_resolved = all(s.result != SelectionResult.PENDING for s in ticket.selections)
        if not all_resolved:
            continue

        # Check if all selections won
        all_won = all(s.result == SelectionResult.WON for s in ticket.selections)
        if all_won:
            ticket.status = TicketStatus.WON
            ticket.settled_at = datetime.utcnow()
            # Process payout
            await _process_payout(db, ticket)
        else:
            ticket.status = TicketStatus.LOST
            ticket.settled_at = datetime.utcnow()

    await db.commit()

    return {
        "match_id": match_id,
        "result": match.result.value,
        "score": f"{match.home_score}-{match.away_score}",
        "tickets_processed": len(ticket_ids),
    }


async def _process_payout(db: AsyncSession, ticket: Ticket, retries: int = 3):
    """Process payout for a winning ticket with retry logic."""
    for attempt in range(retries):
        try:
            # Lock wallet
            wallet_result = await db.execute(
                select(Wallet)
                .where(Wallet.user_id == ticket.user_id)
                .with_for_update()
            )
            wallet = wallet_result.scalar_one_or_none()
            if not wallet:
                return

            # Idempotency check — ensure no existing winning transaction for this ticket
            existing = await db.execute(
                select(Transaction)
                .where(
                    Transaction.reference_id == ticket.id,
                    Transaction.type == TransactionType.BET_WINNING,
                )
            )
            if existing.scalar_one_or_none():
                return  # Already paid

            # Credit wallet
            payout = ticket.potential_win
            wallet.real_balance += payout
            new_balance = wallet.real_balance + wallet.bonus_balance

            transaction = Transaction(
                wallet_id=wallet.id,
                type=TransactionType.BET_WINNING,
                amount=payout,
                balance_after=new_balance,
                reference_id=ticket.id,
                status=TransactionStatus.COMPLETED,
            )
            db.add(transaction)
            return  # Success

        except Exception:
            if attempt < retries - 1:
                await asyncio.sleep(2 ** (attempt + 1))  # 2s, 4s, 8s
            else:
                # Final failure — log alert (in production, notify admin)
                pass


@router.get("/liability", response_model=List[LiabilityResponse])
async def get_liability(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get financial liability per active match."""
    # Get matches with active tickets
    result = await db.execute(
        select(Match)
        .where(Match.status.in_([MatchStatus.UPCOMING, MatchStatus.LIVE]))
    )
    matches = result.scalars().all()

    liability_data = []
    for match in matches:
        # Get active tickets with selections on this match
        ticket_result = await db.execute(
            select(Ticket)
            .join(Selection, Selection.ticket_id == Ticket.id)
            .where(
                Selection.match_id == match.id,
                Ticket.status == TicketStatus.ACTIVE,
            )
        )
        tickets = ticket_result.scalars().all()

        total_stakes = sum(float(t.stake) for t in tickets)
        total_potential = sum(float(t.potential_win) for t in tickets)

        liability_data.append(LiabilityResponse(
            match_id=match.id,
            home_team=match.home_team,
            away_team=match.away_team,
            total_stakes=total_stakes,
            total_potential_payout=total_potential,
            active_tickets=len(tickets),
        ))

    return liability_data


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get admin dashboard aggregate stats."""
    from app.models.user import User as UserModel

    # Total users
    user_count = await db.execute(select(func.count(UserModel.id)))
    total_users = user_count.scalar() or 0

    # Active tickets
    active_count = await db.execute(
        select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.ACTIVE)
    )
    active_tickets = active_count.scalar() or 0

    # Total stakes (all time)
    stakes_sum = await db.execute(
        select(func.sum(Ticket.stake))
    )
    total_stakes = float(stakes_sum.scalar() or 0)

    # Total liability (active tickets potential payout)
    liability_sum = await db.execute(
        select(func.sum(Ticket.potential_win))
        .where(Ticket.status == TicketStatus.ACTIVE)
    )
    total_liability = float(liability_sum.scalar() or 0)

    return DashboardResponse(
        total_users=total_users,
        active_tickets=active_tickets,
        total_stakes_today=total_stakes,
        total_liability=total_liability,
    )
