import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List
from decimal import Decimal
from app.database import get_db
from app.models.user import User
from app.models.wallet import Wallet, Transaction, TransactionType, TransactionStatus
from app.auth import get_current_user

router = APIRouter()


class WalletResponse(BaseModel):
    id: str
    real_balance: float
    bonus_balance: float
    total_balance: float


class DepositRequest(BaseModel):
    amount: float
    phone: str  # M-Pesa phone for simulation


class WithdrawRequest(BaseModel):
    amount: float
    phone: str


class TransactionResponse(BaseModel):
    id: str
    type: str
    amount: float
    balance_after: float
    status: str
    reference_id: str | None
    created_at: str


class PaymentWebhook(BaseModel):
    transaction_id: str
    status: str  # "success" or "failed"
    amount: float


@router.get("", response_model=WalletResponse)
async def get_wallet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user wallet balances."""
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id)
    )
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    return WalletResponse(
        id=wallet.id,
        real_balance=float(wallet.real_balance),
        bonus_balance=float(wallet.bonus_balance),
        total_balance=float(wallet.real_balance + wallet.bonus_balance),
    )


@router.post("/deposit", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def initiate_deposit(
    req: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate a deposit (simulated M-Pesa STK push)."""
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id).with_for_update()
    )
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    # In production, this would trigger an STK push to M-Pesa
    # For simulation, we auto-confirm the deposit
    wallet.real_balance += Decimal(str(req.amount))
    new_balance = wallet.real_balance + wallet.bonus_balance

    transaction = Transaction(
        wallet_id=wallet.id,
        type=TransactionType.DEPOSIT,
        amount=Decimal(str(req.amount)),
        balance_after=new_balance,
        reference_id=str(uuid.uuid4()),
        status=TransactionStatus.COMPLETED,
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)

    return TransactionResponse(
        id=transaction.id,
        type=transaction.type.value,
        amount=float(transaction.amount),
        balance_after=float(transaction.balance_after),
        status=transaction.status.value,
        reference_id=transaction.reference_id,
        created_at=transaction.created_at.isoformat(),
    )


@router.post("/withdraw", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def initiate_withdrawal(
    req: WithdrawRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate a withdrawal."""
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id).with_for_update()
    )
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    if wallet.real_balance < Decimal(str(req.amount)):
        raise HTTPException(status_code=400, detail="Insufficient real balance for withdrawal")

    wallet.real_balance -= Decimal(str(req.amount))
    new_balance = wallet.real_balance + wallet.bonus_balance

    transaction = Transaction(
        wallet_id=wallet.id,
        type=TransactionType.WITHDRAWAL,
        amount=-Decimal(str(req.amount)),
        balance_after=new_balance,
        reference_id=str(uuid.uuid4()),
        status=TransactionStatus.COMPLETED,
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)

    return TransactionResponse(
        id=transaction.id,
        type=transaction.type.value,
        amount=float(transaction.amount),
        balance_after=float(transaction.balance_after),
        status=transaction.status.value,
        reference_id=transaction.reference_id,
        created_at=transaction.created_at.isoformat(),
    )


@router.get("/transactions", response_model=List[TransactionResponse])
async def list_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List transaction history."""
    wallet_result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id)
    )
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    result = await db.execute(
        select(Transaction)
        .where(Transaction.wallet_id == wallet.id)
        .order_by(Transaction.created_at.desc())
        .limit(50)
    )
    transactions = result.scalars().all()

    return [
        TransactionResponse(
            id=t.id,
            type=t.type.value,
            amount=float(t.amount),
            balance_after=float(t.balance_after),
            status=t.status.value,
            reference_id=t.reference_id,
            created_at=t.created_at.isoformat(),
        )
        for t in transactions
    ]
