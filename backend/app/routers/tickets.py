from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List
from decimal import Decimal
from app.database import get_db
from app.config import get_settings
from app.models.user import User
from app.models.wallet import Wallet, Transaction, TransactionType, TransactionStatus
from app.models.ticket import Ticket, Selection, TicketStatus, MarketType
from app.models.match import Match, MatchStatus
from app.auth import get_current_user

router = APIRouter()
settings = get_settings()


class SelectionInput(BaseModel):
    match_id: str
    market: str  # "home", "draw", "away"
    odds: float


class PlaceBetRequest(BaseModel):
    selections: List[SelectionInput]
    stake: float


class SelectionResponse(BaseModel):
    id: str
    match_id: str
    market: str
    locked_odds: float
    result: str


class TicketResponse(BaseModel):
    id: str
    stake: float
    total_odds: float
    potential_win: float
    status: str
    currency: str = "KES"
    created_at: str
    selections: List[SelectionResponse]


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def place_bet(
    req: PlaceBetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Place a bet with one or more selections (KES)."""
    if not req.selections:
        raise HTTPException(status_code=400, detail="At least one selection required")

    if len(req.selections) > settings.MAX_SELECTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.MAX_SELECTIONS} selections per slip",
        )

    if req.stake < settings.MIN_STAKE:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum stake is KES {settings.MIN_STAKE:,}",
        )

    if req.stake > settings.MAX_STAKE:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum stake is KES {settings.MAX_STAKE:,}",
        )

    # Validate all matches exist and are active
    match_ids = [s.match_id for s in req.selections]
    result = await db.execute(select(Match).where(Match.id.in_(match_ids)))
    matches = {m.id: m for m in result.scalars().all()}

    for sel in req.selections:
        match = matches.get(sel.match_id)
        if not match:
            raise HTTPException(status_code=400, detail=f"Match {sel.match_id} not found")
        if match.status not in (MatchStatus.UPCOMING, MatchStatus.LIVE):
            raise HTTPException(status_code=400, detail=f"Match {sel.match_id} is not accepting bets")

    # Calculate total odds (accumulator)
    total_odds = Decimal("1.00")
    for sel in req.selections:
        total_odds *= Decimal(str(sel.odds))
    total_odds = round(total_odds, 2)

    stake = Decimal(str(req.stake))
    potential_win = round(stake * total_odds, 2)

    # Enforce max potential win (KES)
    if potential_win > settings.MAX_POTENTIAL_WIN:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum potential win is KES {settings.MAX_POTENTIAL_WIN:,}. Reduce stake or selections.",
        )

    # Lock wallet and validate balance
    wallet_result = await db.execute(
        select(Wallet)
        .where(Wallet.user_id == current_user.id)
        .with_for_update()
    )
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=400, detail="Wallet not found")

    total_balance = wallet.real_balance + wallet.bonus_balance
    if total_balance < stake:
        raise HTTPException(
            status_code=400,
            detail="Salio haitoshi — Insufficient balance. Please deposit to continue.",
        )

    # Deduct from bonus first, then real balance
    remaining_stake = stake
    if wallet.bonus_balance > 0:
        if wallet.bonus_balance >= remaining_stake:
            wallet.bonus_balance -= remaining_stake
            remaining_stake = Decimal("0.00")
        else:
            remaining_stake -= wallet.bonus_balance
            wallet.bonus_balance = Decimal("0.00")

    if remaining_stake > 0:
        wallet.real_balance -= remaining_stake

    # Create ticket
    ticket = Ticket(
        user_id=current_user.id,
        stake=stake,
        total_odds=total_odds,
        potential_win=potential_win,
        status=TicketStatus.ACTIVE,
    )
    db.add(ticket)
    await db.flush()

    # Create selections
    for sel in req.selections:
        selection = Selection(
            ticket_id=ticket.id,
            match_id=sel.match_id,
            market=MarketType(sel.market),
            locked_odds=Decimal(str(sel.odds)),
        )
        db.add(selection)

    # Create transaction record
    new_balance = wallet.real_balance + wallet.bonus_balance
    transaction = Transaction(
        wallet_id=wallet.id,
        type=TransactionType.BET_STAKE,
        amount=-stake,
        balance_after=new_balance,
        reference_id=ticket.id,
        status=TransactionStatus.COMPLETED,
    )
    db.add(transaction)

    await db.commit()
    await db.refresh(ticket, ["selections"])

    return TicketResponse(
        id=ticket.id,
        stake=float(ticket.stake),
        total_odds=float(ticket.total_odds),
        potential_win=float(ticket.potential_win),
        status=ticket.status.value,
        currency="KES",
        created_at=ticket.created_at.isoformat(),
        selections=[
            SelectionResponse(
                id=s.id,
                match_id=s.match_id,
                market=s.market.value,
                locked_odds=float(s.locked_odds),
                result=s.result.value,
            )
            for s in ticket.selections
        ],
    )


@router.get("", response_model=List[TicketResponse])
async def list_tickets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's tickets (KES)."""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Ticket)
        .where(Ticket.user_id == current_user.id)
        .options(selectinload(Ticket.selections))
        .order_by(Ticket.created_at.desc())
        .limit(50)
    )
    tickets = result.scalars().all()

    return [
        TicketResponse(
            id=t.id,
            stake=float(t.stake),
            total_odds=float(t.total_odds),
            potential_win=float(t.potential_win),
            status=t.status.value,
            currency="KES",
            created_at=t.created_at.isoformat(),
            selections=[
                SelectionResponse(
                    id=s.id,
                    match_id=s.match_id,
                    market=s.market.value,
                    locked_odds=float(s.locked_odds),
                    result=s.result.value,
                )
                for s in t.selections
            ],
        )
        for t in tickets
    ]


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get single ticket detail (KES)."""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Ticket)
        .where(Ticket.id == ticket_id, Ticket.user_id == current_user.id)
        .options(selectinload(Ticket.selections))
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return TicketResponse(
        id=ticket.id,
        stake=float(ticket.stake),
        total_odds=float(ticket.total_odds),
        potential_win=float(ticket.potential_win),
        status=ticket.status.value,
        currency="KES",
        created_at=ticket.created_at.isoformat(),
        selections=[
            SelectionResponse(
                id=s.id,
                match_id=s.match_id,
                market=s.market.value,
                locked_odds=float(s.locked_odds),
                result=s.result.value,
            )
            for s in ticket.selections
        ],
    )
