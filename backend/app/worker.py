"""
Background Settlement Worker
Continuously processes pending match settlements and wallet credit payouts.
Runs as a standalone process on Render Background Worker tier.

Built by P.o.Riot
"""
import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.match import Match, MatchStatus
from app.models.ticket import Ticket, Selection, TicketStatus, SelectionResult
from app.models.wallet import Wallet, Transaction, TransactionType, TransactionStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("settlement-worker")

POLL_INTERVAL_SECONDS = 5
MAX_PAYOUT_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds: 2, 4, 8


async def process_pending_payouts():
    """Find all WON tickets without a corresponding payout transaction and credit wallets."""
    async with AsyncSessionLocal() as db:
        try:
            # Find WON tickets that haven't been paid yet
            result = await db.execute(
                select(Ticket)
                .where(Ticket.status == TicketStatus.WON)
                .options(selectinload(Ticket.selections))
                .limit(50)
            )
            won_tickets = result.scalars().all()

            for ticket in won_tickets:
                await _process_single_payout(db, ticket)

        except Exception as e:
            logger.error(f"Error in payout processing loop: {e}")
            await db.rollback()


async def _process_single_payout(db: AsyncSession, ticket: Ticket):
    """Process payout for a single winning ticket with retry logic and idempotency."""
    for attempt in range(MAX_PAYOUT_RETRIES):
        try:
            # Idempotency check: skip if payout already exists
            existing = await db.execute(
                select(Transaction).where(
                    Transaction.reference_id == ticket.id,
                    Transaction.type == TransactionType.BET_WINNING,
                    Transaction.status == TransactionStatus.COMPLETED,
                )
            )
            if existing.scalar_one_or_none():
                logger.debug(f"Ticket {ticket.id} already paid, skipping")
                return

            # Lock wallet row to prevent concurrent balance mutations
            wallet_result = await db.execute(
                select(Wallet)
                .where(Wallet.user_id == ticket.user_id)
                .with_for_update()
            )
            wallet = wallet_result.scalar_one_or_none()
            if not wallet:
                logger.warning(f"Wallet not found for user {ticket.user_id}")
                return

            # Credit the wallet
            payout_amount = ticket.potential_win
            wallet.real_balance += payout_amount
            new_balance = wallet.real_balance + wallet.bonus_balance

            # Create transaction record
            transaction = Transaction(
                wallet_id=wallet.id,
                type=TransactionType.BET_WINNING,
                amount=payout_amount,
                balance_after=new_balance,
                reference_id=ticket.id,
                status=TransactionStatus.COMPLETED,
            )
            db.add(transaction)
            await db.commit()

            logger.info(
                f"Payout successful: ticket={ticket.id}, "
                f"user={ticket.user_id}, amount={payout_amount}"
            )
            return  # Success — exit retry loop

        except Exception as e:
            await db.rollback()
            if attempt < MAX_PAYOUT_RETRIES - 1:
                backoff = RETRY_BACKOFF_BASE ** (attempt + 1)
                logger.warning(
                    f"Payout attempt {attempt + 1} failed for ticket {ticket.id}: {e}. "
                    f"Retrying in {backoff}s..."
                )
                await asyncio.sleep(backoff)
            else:
                logger.error(
                    f"Payout FAILED after {MAX_PAYOUT_RETRIES} attempts for "
                    f"ticket {ticket.id}: {e}"
                )


async def process_settled_matches():
    """
    Check for recently settled matches and ensure all related tickets
    have been properly evaluated (catch-up for any missed during API settlement).
    """
    async with AsyncSessionLocal() as db:
        try:
            # Find settled matches from the last hour that might have pending selections
            result = await db.execute(
                select(Match).where(Match.status == MatchStatus.SETTLED)
            )
            settled_matches = result.scalars().all()

            for match in settled_matches:
                # Find any PENDING selections for this settled match
                sel_result = await db.execute(
                    select(Selection).where(
                        Selection.match_id == match.id,
                        Selection.result == SelectionResult.PENDING,
                    )
                )
                pending_selections = sel_result.scalars().all()

                if pending_selections:
                    logger.info(
                        f"Found {len(pending_selections)} pending selections "
                        f"for settled match {match.id}"
                    )
                    # These shouldn't exist after settlement, but handle gracefully
                    for sel in pending_selections:
                        sel.result = SelectionResult.VOID
                    await db.commit()

        except Exception as e:
            logger.error(f"Error in settled match check: {e}")
            await db.rollback()


async def main():
    """Main worker loop — polls for pending payouts and settled match reconciliation."""
    logger.info("Settlement worker starting...")
    logger.info(f"Poll interval: {POLL_INTERVAL_SECONDS}s")
    logger.info(f"Max retries per payout: {MAX_PAYOUT_RETRIES}")
    logger.info("Built by P.o.Riot")

    while True:
        try:
            await process_pending_payouts()
            await process_settled_matches()
        except Exception as e:
            logger.error(f"Unhandled error in worker loop: {e}")

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
