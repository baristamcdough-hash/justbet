from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import List, Optional
from app.database import get_db
from app.models.match import League, Match, MatchStatus

router = APIRouter()


class OddsResponse(BaseModel):
    home: float
    draw: float
    away: float


class MatchResponse(BaseModel):
    id: str
    home_team: str
    away_team: str
    kickoff_time: str
    status: str
    home_score: int
    away_score: int
    odds: OddsResponse


class LeagueWithMatches(BaseModel):
    id: str
    name: str
    sport: str
    country: Optional[str]
    matches: List[MatchResponse]


@router.get("/matches", response_model=List[LeagueWithMatches])
async def get_matches(db: AsyncSession = Depends(get_db)):
    """Get all active matches grouped by league."""
    result = await db.execute(
        select(League)
        .options(selectinload(League.matches))
        .order_by(League.name)
    )
    leagues = result.scalars().all()

    response = []
    for league in leagues:
        active_matches = [
            m for m in league.matches
            if m.status in (MatchStatus.UPCOMING, MatchStatus.LIVE)
        ]
        if not active_matches:
            continue

        league_data = LeagueWithMatches(
            id=league.id,
            name=league.name,
            sport=league.sport,
            country=league.country,
            matches=[
                MatchResponse(
                    id=m.id,
                    home_team=m.home_team,
                    away_team=m.away_team,
                    kickoff_time=m.kickoff_time.isoformat(),
                    status=m.status.value,
                    home_score=m.home_score,
                    away_score=m.away_score,
                    odds=OddsResponse(
                        home=float(m.home_odds),
                        draw=float(m.draw_odds),
                        away=float(m.away_odds),
                    ),
                )
                for m in sorted(active_matches, key=lambda x: x.kickoff_time)
            ],
        )
        response.append(league_data)

    return response


@router.get("/matches/{match_id}", response_model=MatchResponse)
async def get_match(match_id: str, db: AsyncSession = Depends(get_db)):
    """Get single match details."""
    result = await db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one_or_none()
    if not match:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Match not found")

    return MatchResponse(
        id=match.id,
        home_team=match.home_team,
        away_team=match.away_team,
        kickoff_time=match.kickoff_time.isoformat(),
        status=match.status.value,
        home_score=match.home_score,
        away_score=match.away_score,
        odds=OddsResponse(
            home=float(match.home_odds),
            draw=float(match.draw_odds),
            away=float(match.away_odds),
        ),
    )


@router.get("/leagues")
async def get_leagues(db: AsyncSession = Depends(get_db)):
    """List all leagues."""
    result = await db.execute(select(League).order_by(League.name))
    leagues = result.scalars().all()
    return [
        {"id": l.id, "name": l.name, "sport": l.sport, "country": l.country}
        for l in leagues
    ]
