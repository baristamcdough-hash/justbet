import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, ForeignKey, Numeric, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class TicketStatus(str, enum.Enum):
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"
    VOID = "void"
    CASHOUT = "cashout"


class MarketType(str, enum.Enum):
    HOME = "home"
    DRAW = "draw"
    AWAY = "away"


class SelectionResult(str, enum.Enum):
    PENDING = "pending"
    WON = "won"
    LOST = "lost"
    VOID = "void"


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    stake: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_odds: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    potential_win: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus), default=TicketStatus.ACTIVE, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    settled_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="tickets")
    selections = relationship("Selection", back_populates="ticket", cascade="all, delete-orphan")


class Selection(Base):
    __tablename__ = "selections"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tickets.id"), nullable=False, index=True
    )
    match_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("matches.id"), nullable=False, index=True
    )
    market: Mapped[MarketType] = mapped_column(SAEnum(MarketType), nullable=False)
    locked_odds: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    result: Mapped[SelectionResult] = mapped_column(
        SAEnum(SelectionResult), default=SelectionResult.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    ticket = relationship("Ticket", back_populates="selections")
    match = relationship("Match", back_populates="selections")
