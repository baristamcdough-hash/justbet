import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, ForeignKey, Numeric, DateTime, Integer, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class MatchStatus(str, enum.Enum):
    UPCOMING = "upcoming"
    LIVE = "live"
    ENDED = "ended"
    SETTLED = "settled"
    CANCELLED = "cancelled"


class MatchResult(str, enum.Enum):
    HOME_WIN = "home_win"
    DRAW = "draw"
    AWAY_WIN = "away_win"
    CANCELLED = "cancelled"


class League(Base):
    __tablename__ = "leagues"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sport: Mapped[str] = mapped_column(String(50), default="football", nullable=False)
    country: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    matches = relationship("Match", back_populates="league")


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    league_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("leagues.id"), nullable=False, index=True
    )
    home_team: Mapped[str] = mapped_column(String(100), nullable=False)
    away_team: Mapped[str] = mapped_column(String(100), nullable=False)
    kickoff_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[MatchStatus] = mapped_column(
        SAEnum(MatchStatus), default=MatchStatus.UPCOMING, nullable=False
    )
    home_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    away_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result: Mapped[MatchResult] = mapped_column(SAEnum(MatchResult), nullable=True)
    settled_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Current odds (denormalized for quick access)
    home_odds: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), default=Decimal("1.00"), nullable=False
    )
    draw_odds: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), default=Decimal("1.00"), nullable=False
    )
    away_odds: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), default=Decimal("1.00"), nullable=False
    )

    # Relationships
    league = relationship("League", back_populates="matches")
    odds_history = relationship("MatchOdds", back_populates="match")
    selections = relationship("Selection", back_populates="match")


class MatchOdds(Base):
    __tablename__ = "match_odds"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    match_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("matches.id"), nullable=False, index=True
    )
    home_odds: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    draw_odds: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    away_odds: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    match = relationship("Match", back_populates="odds_history")
