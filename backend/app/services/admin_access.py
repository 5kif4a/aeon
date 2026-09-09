"""Admin access control: the permission catalog, roles and who holds them.

Permissions are declared here (code owns the catalog, the matrix lives in the database):
`admin_roles` stores which permission keys each role grants, `admin_accounts` binds a
Telegram user to one role. The database is the only source of access - there is no env
allowlist. What keeps the panel reachable instead is the invariant enforced below: the last
account that can manage access cannot be revoked or demoted. To recover from an empty table
(a fresh environment, or rows deleted by hand) use `scripts/grant_admin.py`.
"""

from dataclasses import dataclass, field

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import AdminAccount, AdminRole, User
from app.services import events, users

WILDCARD = "*"
OWNER_ROLE_ID = "owner"


@dataclass(frozen=True)
class Permission:
    key: str
    group: str
    description: str


# Order matters: the panel renders the matrix in this order, grouped by `group`.
PERMISSIONS: tuple[Permission, ...] = (
    Permission("stats.view", "dashboard", "See the dashboard and product metrics"),
    Permission("users.view", "users", "Browse users and open a user card"),
    Permission("users.grant_pro", "users", "Grant Pro without a payment"),
    Permission("conversations.view", "users", "Read user dialogues"),
    Permission("payments.view", "billing", "See payments"),
    Permission("payments.refund", "billing", "Refund a Stars charge"),
    Permission("settings.view", "bot", "See runtime bot settings"),
    Permission("settings.edit", "bot", "Change prompts and generation knobs"),
    Permission("segments.view", "audience", "See segments and their size"),
    Permission("segments.edit", "audience", "Create, change and delete segments"),
    Permission("broadcasts.view", "audience", "See broadcasts and their delivery stats"),
    Permission("broadcasts.edit", "audience", "Compose and edit broadcast drafts"),
    Permission("broadcasts.send", "audience", "Send, schedule and cancel broadcasts"),
    Permission("admins.view", "access", "See admins and roles"),
    Permission("admins.manage", "access", "Grant, change and revoke admin access"),
)

PERMISSION_KEYS = frozenset(permission.key for permission in PERMISSIONS)

# Built-in roles. `owner` is locked (all permissions, not editable, not deletable); the other
# two are seeded once and may be re-cut in the panel.
SYSTEM_ROLES: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    (OWNER_ROLE_ID, "Owner", "Full access, including who else is an admin", (WILDCARD,)),
    (
        "support",
        "Support",
        "Answers users: reads dialogues, grants Pro, refunds payments",
        (
            "stats.view",
            "users.view",
            "users.grant_pro",
            "conversations.view",
            "payments.view",
            "payments.refund",
        ),
    ),
    (
        "marketing",
        "Marketing",
        "Builds segments and sends broadcasts; no dialogues, no refunds",
        (
            "stats.view",
            "users.view",
            "segments.view",
            "segments.edit",
            "broadcasts.view",
            "broadcasts.edit",
            "broadcasts.send",
        ),
    ),
)


class AccessError(ValueError):
    """Rejected access change (unknown role, locked role, self-demotion, last owner)."""


@dataclass
class AdminIdentity:
    """Who the caller is inside the panel and what they may do."""

    user_id: int
    role_id: str
    role_title: str
    permissions: frozenset[str] = field(default_factory=frozenset)

    @property
    def is_owner(self) -> bool:
        return WILDCARD in self.permissions

    def can(self, permission: str) -> bool:
        return WILDCARD in self.permissions or permission in self.permissions


async def ensure_system_roles(session: AsyncSession) -> None:
    """Create the built-in roles if they are missing (fresh database, tests, dev)."""
    existing = set(await session.scalars(select(AdminRole.id)))
    added = False
    for role_id, title, description, permissions in SYSTEM_ROLES:
        if role_id in existing:
            continue
        session.add(
            AdminRole(
                id=role_id,
                title=title,
                description=description,
                permissions=list(permissions),
                is_system=True,
            )
        )
        added = True
    if added:
        await session.commit()


async def resolve_identity(session: AsyncSession, user_id: int) -> AdminIdentity | None:
    """Return the caller's panel identity, or None when they are not an admin at all."""
    account = (
        await session.scalars(
            select(AdminAccount)
            .where(AdminAccount.user_id == user_id)
            .options(selectinload(AdminAccount.role))
        )
    ).one_or_none()
    if account is None or account.role is None:
        return None
    return AdminIdentity(
        user_id=user_id,
        role_id=account.role_id,
        role_title=account.role.title,
        permissions=frozenset(account.role.permissions or ()),
    )


# --- roles -------------------------------------------------------------------------------


@dataclass
class RoleRow:
    role: AdminRole
    admins: int


async def list_roles(session: AsyncSession) -> list[RoleRow]:
    await ensure_system_roles(session)
    counts = dict(
        (
            await session.execute(
                select(AdminAccount.role_id, func.count()).group_by(AdminAccount.role_id)
            )
        ).all()
    )
    roles = list(await session.scalars(select(AdminRole).order_by(AdminRole.id)))
    return [RoleRow(role=role, admins=int(counts.get(role.id, 0))) for role in roles]


def _clean_permissions(permissions: list[str]) -> list[str]:
    unknown = sorted(set(permissions) - PERMISSION_KEYS)
    if unknown:
        raise AccessError(f"Unknown permissions: {', '.join(unknown)}")
    return [permission.key for permission in PERMISSIONS if permission.key in set(permissions)]


def _clean_role_id(role_id: str) -> str:
    slug = role_id.strip().lower()
    if not slug or not all(char.isalnum() or char in "_-" for char in slug):
        raise AccessError("Role id must be a slug: letters, digits, '-' or '_'")
    return slug


async def create_role(
    session: AsyncSession,
    *,
    role_id: str,
    title: str,
    description: str,
    permissions: list[str],
    actor_id: int,
) -> AdminRole:
    slug = _clean_role_id(role_id)
    if await session.get(AdminRole, slug) is not None:
        raise AccessError("A role with this id already exists")
    role = AdminRole(
        id=slug,
        title=title.strip() or slug,
        description=description.strip(),
        permissions=_clean_permissions(permissions),
        is_system=False,
    )
    session.add(role)
    events.record(session, events.ADMIN_ROLE_CHANGED, actor_id, role_id=slug, action="created")
    await session.commit()
    await session.refresh(role)
    return role


async def update_role(
    session: AsyncSession,
    role_id: str,
    *,
    title: str | None,
    description: str | None,
    permissions: list[str] | None,
    actor_id: int,
) -> AdminRole:
    role = await session.get(AdminRole, role_id)
    if role is None:
        raise AccessError("Unknown role")
    if role.id == OWNER_ROLE_ID and permissions is not None:
        raise AccessError("The owner role always has every permission")
    if title is not None:
        role.title = title.strip() or role.id
    if description is not None:
        role.description = description.strip()
    if permissions is not None:
        cleaned = _clean_permissions(permissions)
        if not (WILDCARD in cleaned or "admins.manage" in cleaned):
            await _assert_manager_remains_after_role_change(session, role.id)
        role.permissions = cleaned
    events.record(
        session,
        events.ADMIN_ROLE_CHANGED,
        actor_id,
        role_id=role.id,
        action="updated",
        permissions=list(role.permissions or ()),
    )
    await session.commit()
    await session.refresh(role)
    return role


async def delete_role(session: AsyncSession, role_id: str, *, actor_id: int) -> None:
    role = await session.get(AdminRole, role_id)
    if role is None:
        raise AccessError("Unknown role")
    if role.is_system:
        raise AccessError("Built-in roles cannot be deleted")
    holders = await session.scalar(
        select(func.count()).select_from(AdminAccount).where(AdminAccount.role_id == role_id)
    )
    if holders:
        raise AccessError("Move the admins to another role first")
    await session.execute(delete(AdminRole).where(AdminRole.id == role_id))
    events.record(session, events.ADMIN_ROLE_CHANGED, actor_id, role_id=role_id, action="deleted")
    await session.commit()


# --- admins ------------------------------------------------------------------------------


@dataclass
class AdminRow:
    user: User | None
    user_id: int
    role_id: str
    role_title: str
    permissions: list[str]
    note: str
    granted_by: int | None


def _row_of(account: AdminAccount) -> AdminRow:
    return AdminRow(
        user=account.user,
        user_id=account.user_id,
        role_id=account.role_id,
        role_title=account.role.title if account.role else account.role_id,
        permissions=list(account.role.permissions or ()) if account.role else [],
        note=account.note or "",
        granted_by=account.granted_by,
    )


async def _accounts(session: AsyncSession) -> list[AdminAccount]:
    return list(
        await session.scalars(
            select(AdminAccount)
            .options(selectinload(AdminAccount.role), selectinload(AdminAccount.user))
            .order_by(AdminAccount.created_at)
        )
    )


async def list_admins(session: AsyncSession) -> list[AdminRow]:
    await ensure_system_roles(session)
    return [_row_of(account) for account in await _accounts(session)]


def _can_manage(account: AdminAccount) -> bool:
    granted = set(account.role.permissions or ()) if account.role else set()
    return WILDCARD in granted or "admins.manage" in granted


async def _assert_manager_remains(
    session: AsyncSession, *, losing: int, gaining_role: str | None = None
) -> None:
    """Refuse a change that would leave nobody able to manage access.

    This is what replaces the old env allowlist: the panel is kept reachable by an invariant
    rather than by an id in the environment. `losing` is the account being revoked or moved,
    `gaining_role` the role it moves to (None when it is revoked).
    """
    remaining = 0
    for account in await _accounts(session):
        if account.user_id == losing:
            continue
        if _can_manage(account):
            remaining += 1
    if remaining == 0 and gaining_role is not None:
        role = await session.get(AdminRole, gaining_role)
        if role is not None and (
            WILDCARD in (role.permissions or ()) or "admins.manage" in (role.permissions or ())
        ):
            return
    if remaining == 0:
        raise AccessError("Someone has to keep the right to manage access")


async def _assert_manager_remains_after_role_change(session: AsyncSession, role_id: str) -> None:
    """Refuse to strip `admins.manage` from the only role that still has it."""
    for account in await _accounts(session):
        if account.role_id != role_id and _can_manage(account):
            return
    raise AccessError("Someone has to keep the right to manage access")


async def grant_admin(
    session: AsyncSession,
    user_id: int,
    *,
    role_id: str,
    note: str = "",
    actor_id: int,
) -> AdminRow:
    """Give (or move) admin access to a Telegram user. Idempotent per user id."""
    await ensure_system_roles(session)
    role = await session.get(AdminRole, role_id)
    if role is None:
        raise AccessError("Unknown role")
    if user_id == actor_id:
        raise AccessError("You cannot change your own access")
    # Moving the last manager into a narrower role would close the panel for everyone.
    existing = await session.get(AdminAccount, user_id)
    if existing is not None:
        await _assert_manager_remains(session, losing=user_id, gaining_role=role_id)
    # Deliberately no `get_or_create_user`: inserting a user here would fake a signup in the
    # product metrics. The person has to open the bot once before they can be made an admin.
    if await users.get_user(session, user_id) is None:
        raise AccessError("Unknown user: they have to open the bot at least once")
    account = await session.get(AdminAccount, user_id)
    if account is None:
        account = AdminAccount(user_id=user_id, role_id=role_id, note=note.strip())
        account.granted_by = actor_id
        session.add(account)
        action = "granted"
    else:
        account.role_id = role_id
        account.note = note.strip()
        account.granted_by = actor_id
        action = "role_changed"
    events.record(
        session,
        events.ADMIN_ACCESS_GRANTED if action == "granted" else events.ADMIN_ACCESS_CHANGED,
        actor_id,
        subject_user_id=user_id,
        role_id=role_id,
    )
    await session.commit()
    account = (
        await session.scalars(
            select(AdminAccount)
            .where(AdminAccount.user_id == user_id)
            .options(selectinload(AdminAccount.role), selectinload(AdminAccount.user))
        )
    ).one()
    return _row_of(account)


async def revoke_admin(session: AsyncSession, user_id: int, *, actor_id: int) -> None:
    if user_id == actor_id:
        raise AccessError("You cannot revoke your own access")
    account = await session.get(AdminAccount, user_id)
    if account is None:
        raise AccessError("This user is not an admin")
    await _assert_manager_remains(session, losing=user_id)
    role_id = account.role_id
    await session.execute(delete(AdminAccount).where(AdminAccount.user_id == user_id))
    events.record(
        session,
        events.ADMIN_ACCESS_REVOKED,
        actor_id,
        subject_user_id=user_id,
        role_id=role_id,
    )
    await session.commit()
