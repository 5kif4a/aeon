"""Grant panel access from the command line.

The database is the only source of admin access, so this is how the first admin is created
in a fresh environment and how you get back in if the table is emptied by mistake. It needs
`DATABASE_URL` and nothing else - no running bot, no panel session.

Run it as a module, like the other scripts, so `app` resolves:

    uv run python -m scripts.grant_admin <telegram_id> [role_id] [--note "..."]
    uv run python -m scripts.grant_admin --list

It also takes DATABASE_URL from the environment, so it can be pointed at production.

`role_id` defaults to `owner`. The user has to have opened the bot at least once: access is
attached to an existing `users` row, and inserting one here would fake a signup in the
product metrics.
"""

import argparse
import asyncio

from app.db.models import AdminAccount, User
from app.db.session import SessionFactory, engine
from app.services import admin_access


async def show() -> None:
    async with SessionFactory() as session:
        rows = await admin_access.list_admins(session)
    if not rows:
        print("No admins. Nobody can open the panel; grant access to yourself first.")
        return
    for row in rows:
        name = row.user.name if row.user else "?"
        print(
            f"{row.user_id:>12}  {row.role_id:<12} {name} {('· ' + row.note) if row.note else ''}"
        )


async def grant(user_id: int, role_id: str, note: str) -> None:
    async with SessionFactory() as session:
        await admin_access.ensure_system_roles(session)
        roles = {row.role.id for row in await admin_access.list_roles(session)}
        if role_id not in roles:
            raise SystemExit(f"Unknown role {role_id!r}. Known roles: {', '.join(sorted(roles))}")
        if await session.get(User, user_id) is None:
            raise SystemExit(
                f"User {user_id} is unknown: they have to open the bot at least once first."
            )
        account = await session.get(AdminAccount, user_id)
        if account is None:
            session.add(AdminAccount(user_id=user_id, role_id=role_id, note=note))
            action = "granted"
        else:
            account.role_id = role_id
            if note:
                account.note = note
            action = "updated"
        await session.commit()
    print(f"{action}: {user_id} is now {role_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("user_id", nargs="?", type=int, help="Telegram user id")
    parser.add_argument("role_id", nargs="?", default=admin_access.OWNER_ROLE_ID)
    parser.add_argument("--note", default="granted from the command line")
    parser.add_argument("--list", action="store_true", help="print the current admins")
    args = parser.parse_args()

    async def run() -> None:
        try:
            if args.list or args.user_id is None:
                await show()
            else:
                await grant(args.user_id, args.role_id, args.note)
        finally:
            await engine.dispose()

    asyncio.run(run())


if __name__ == "__main__":
    main()
