import re
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, field_validator
from typing import Optional
from app.database import get_db
from app.config import get_settings
from app.models.user import User, UserRole
from app.models.wallet import Wallet
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
)

router = APIRouter()
settings = get_settings()

# Kenyan phone regex: 07XXXXXXXX or +254XXXXXXXXX or 254XXXXXXXXX
PHONE_REGEX = re.compile(r"^(?:\+?254|0)7\d{8}$")


def normalize_phone(phone: str) -> str:
    """Normalize phone to 07XXXXXXXX format."""
    phone = phone.strip().replace(" ", "")
    if phone.startswith("+254"):
        phone = "0" + phone[4:]
    elif phone.startswith("254") and len(phone) == 12:
        phone = "0" + phone[3:]
    return phone


def validate_phone_format(phone: str) -> str:
    """Validate Kenyan phone number format."""
    normalized = normalize_phone(phone)
    if not PHONE_REGEX.match(normalized):
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number. Use format: 07XXXXXXXX or +254XXXXXXXXX",
        )
    return normalized


def validate_pin(pin: str) -> None:
    """Validate 4-digit numeric PIN."""
    if not pin.isdigit() or len(pin) != 4:
        raise HTTPException(
            status_code=400,
            detail="PIN must be exactly 4 digits",
        )


class RegisterRequest(BaseModel):
    phone: str
    pin: str  # 4-digit numeric PIN


class LoginRequest(BaseModel):
    phone: str
    pin: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    phone: str
    role: str
    currency: str = "KES"
    created_at: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register with Kenyan phone number + 4-digit PIN."""
    # Validate inputs
    phone = validate_phone_format(req.phone)
    validate_pin(req.pin)

    # Check if phone already exists
    existing = await db.execute(select(User).where(User.phone == phone))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number already registered",
        )

    # Create user
    user = User(
        phone=phone,
        password_hash=hash_password(req.pin),
        role=UserRole.PUNTER,
    )
    db.add(user)
    await db.flush()

    # Create wallet (KES)
    wallet = Wallet(user_id=user.id)
    db.add(wallet)
    await db.commit()

    # Generate tokens
    access_token = create_access_token(user.id, user.role.value)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with phone + 4-digit PIN."""
    phone = normalize_phone(req.phone)

    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.pin, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or PIN",
        )

    access_token = create_access_token(user.id, user.role.value)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Rotate access token using refresh token."""
    from jose import jwt, JWTError

    try:
        payload = jwt.decode(
            req.refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        token_type = payload.get("type")
        if not user_id or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(user.id, user.role.value)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse(
        id=current_user.id,
        phone=current_user.phone,
        role=current_user.role.value,
        currency="KES",
        created_at=current_user.created_at.isoformat(),
    )


@router.post("/admin/create", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin(
    req: RegisterRequest,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Create an admin account (requires ADMIN_SECRET_TOKEN header)."""
    if not settings.ADMIN_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Admin creation disabled")

    if x_admin_token != settings.ADMIN_SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token")

    phone = validate_phone_format(req.phone)
    validate_pin(req.pin)

    existing = await db.execute(select(User).where(User.phone == phone))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Phone already registered")

    user = User(
        phone=phone,
        password_hash=hash_password(req.pin),
        role=UserRole.ADMIN,
    )
    db.add(user)
    await db.flush()

    wallet = Wallet(user_id=user.id)
    db.add(wallet)
    await db.commit()

    return UserResponse(
        id=user.id,
        phone=user.phone,
        role=user.role.value,
        currency="KES",
        created_at=user.created_at.isoformat(),
    )
