"""Refund one verified Telegram Stars payment and revoke its entitlement."""

import argparse
import asyncio

from telegram import Bot

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services import billing


async def refund(user_id: int, charge_id: str) -> None:
    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not configured")
    async with Bot(settings.bot_token) as bot:
        await bot.refund_star_payment(user_id, charge_id)
    async with SessionFactory() as session:
        await billing.mark_payment_refunded(session, user_id, charge_id)
    print(f"Refunded {charge_id} for user {user_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("user_id", type=int)
    parser.add_argument("charge_id")
    args = parser.parse_args()
    asyncio.run(refund(args.user_id, args.charge_id))


if __name__ == "__main__":
    main()
