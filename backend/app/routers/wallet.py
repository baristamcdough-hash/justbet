import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from app.database import get_db
from app.config import get_settings
from app.models.user import User
from app.models.wallet import Wallet, Transaction, TransactionType, TransactionStatus
from app.auth import get_current_user

router = APIRouter()
settings = get_settings()


class WalletResponse(BaseModel):
    id: str
    real_balance: float
    bonus_balance: float
    total_balance: float
    currency: str = "KES"


class DepositRequest(BaseModel):
    amount: float
    phone: str  # M-Pesa phone number (254XXXXXXXXX)


class DepositResponse(BaseModel):
    """Simulated M-Pesa STK Push response."""
    checkout_request_id: str
    merchant_request_id: str
    response_code: str
    response_description: str
    customer_message: str
    transaction_id: str
    amount: float
    currency: str = "KES"
    status: str


class WithdrawRequest(BaseModel):
    amount: float
    phone: str


class WithdrawResponse(BaseModel):
    transaction_id: str
    amount: float
    phone: str
    currency: str = "KES"
    status: str
    message: str


class TransactionResponse(BaseModel):
    id: str
    type: str
    amount: float
    balance_after: float
    status: str
    reference_id: Optional[str]
    checkout_request_id: Optional[str] = None
    currency: str = "KES"
    created_at: str


class MpesaCallbackBody(BaseModel):
    """Simulated Daraja STK callback format."""

    class StkCallback(BaseModel):
        MerchantRequestID: str
        CheckoutRequestID: str
        ResultCode: int
        ResultDesc: str

    class Body(BaseModel):
        stkCallback: "MpesaCallbackBody.StkCallback"

    Body: "MpesaCallbackBody.Body"


@router.get("", response_model=WalletResponse)
async def get_wallet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user wallet balances (KES)."""
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
        currency="KES",
    )


@router.post("/deposit", response_model=DepositResponse, status_code=status.HTTP_201_CREATED)
async def initiate_deposit(
    req: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate M-Pesa STK Push deposit (simulated Daraja API).
    Min: KES 100, Max: KES 150,000.
    Auto-confirms after simulated delay.
    """
    # Validate amount limits (KES)
    if req.amount < settings.MIN_DEPOSIT:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum deposit is KES {settings.MIN_DEPOSIT:,}",
        )
    if req.amount > settings.MAX_DEPOSIT:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum deposit is KES {settings.MAX_DEPOSIT:,}",
        )

    result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id).with_for_update()
    )
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    # Generate M-Pesa-style identifiers
    checkout_request_id = f"ws_CO_{uuid.uuid4().hex[:20].upper()}"
    merchant_request_id = str(uuid.uuid4())

    # Simulate instant confirmation (in production, this would be async via callback)
    wallet.real_balance += Decimal(str(req.amount))
    new_balance = wallet.real_balance + wallet.bonus_balance

    transaction = Transaction(
        wallet_id=wallet.id,
        type=TransactionType.DEPOSIT,
        amount=Decimal(str(req.amount)),
        balance_after=new_balance,
        reference_id=merchant_request_id,
        checkout_request_id=checkout_request_id,
        status=TransactionStatus.COMPLETED,
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)

    return DepositResponse(
        checkout_request_id=checkout_request_id,
        merchant_request_id=merchant_request_id,
        response_code="0",
        response_description="Success. Request accepted for processing",
        customer_message="Success. Request accepted for processing. Please enter your M-Pesa PIN.",
        transaction_id=transaction.id,
        amount=float(req.amount),
        currency="KES",
        status="completed",
    )


@router.post("/withdraw", response_model=WithdrawResponse, status_code=status.HTTP_201_CREATED)
async def initiate_withdrawal(
    req: WithdrawRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate M-Pesa B2C withdrawal (simulated).
    Min: KES 100, Max: KES 70,000.
    """
    # Validate amount limits (KES)
    if req.amount < settings.MIN_WITHDRAWAL:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum withdrawal is KES {settings.MIN_WITHDRAWAL:,}",
        )
    if req.amount > settings.MAX_WITHDRAWAL:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum withdrawal is KES {settings.MAX_WITHDRAWAL:,}",
        )

    result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id).with_for_update()
    )
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    if wallet.real_balance < Decimal(str(req.amount)):
        raise HTTPException(
            status_code=400,
            detail="Salio haitoshi — Insufficient balance for withdrawal",
        )

    wallet.real_balance -= Decimal(str(req.amount))
    new_balance = wallet.real_balance + wallet.bonus_balance

    transaction = Transaction(
        wallet_id=wallet.id,
        type=TransactionType.WITHDRAWAL,
        amount=-Decimal(str(req.amount)),
        balance_after=new_balance,
        reference_id=str(uuid.uuid4()),
        checkout_request_id=f"b2c_{uuid.uuid4().hex[:16].upper()}",
        status=TransactionStatus.COMPLETED,
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)

    return WithdrawResponse(
        transaction_id=transaction.id,
        amount=float(req.amount),
        phone=req.phone,
        currency="KES",
        status="completed",
        message=f"KES {req.amount:,.2f} sent to {req.phone} via M-Pesa",
    )


@router.post("/webhooks/mpesa/callback")
async def mpesa_callback(payload: dict):
    """
    Simulated M-Pesa Daraja STK Push callback endpoint.
    In production, Safaricom calls this URL after STK Push completes.
    """
    # Extract from Daraja callback format
    try:
        stk_callback = payload.get("Body", {}).get("stkCallback", {})
        checkout_request_id = stk_callback.get("CheckoutRequestID")
        result_code = stk_callback.get("ResultCode")

        if not checkout_request_id:
            return {"ResultCode": 1, "ResultDesc": "Missing CheckoutRequestID"}

        # In production: look up pending transaction by checkout_request_id
        # and confirm/reject based on ResultCode
        return {
            "ResultCode": 0,
            "ResultDesc": "Callback received successfully",
        }
    except Exception:
        return {"ResultCode": 1, "ResultDesc": "Invalid callback format"}


@router.get("/transactions", response_model=List[TransactionResponse])
async def list_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List transaction history (KES)."""
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
            checkout_request_id=t.checkout_request_id,
            currency="KES",
            created_at=t.created_at.isoformat(),
        )
        for t in transactions
    ]
