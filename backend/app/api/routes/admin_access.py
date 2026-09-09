"""Who may use the panel: the permission catalog, roles and admin grants.

Mounted under the same `/api/admin` prefix as the rest of the panel. Reading the matrix
needs `admins.view`, changing anything needs `admins.manage`; an admin can never edit their
own access, and the last account able to manage access can be neither revoked nor demoted.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import AdminActor, SessionDep, require
from app.api.schemas import (
    AdminAccessOut,
    AdminAccountIn,
    AdminAccountOut,
    AdminPermissionOut,
    AdminRoleIn,
    AdminRoleOut,
    AdminRoleUpdateIn,
)
from app.services import admin_access

router = APIRouter(prefix="/admin", tags=["admin"])

AccessViewer = Annotated[AdminActor, Depends(require("admins.view"))]
AccessManager = Annotated[AdminActor, Depends(require("admins.manage"))]


def _role_out(row: admin_access.RoleRow) -> AdminRoleOut:
    permissions = list(row.role.permissions or ())
    return AdminRoleOut(
        id=row.role.id,
        title=row.role.title,
        description=row.role.description or "",
        permissions=permissions,
        isSystem=bool(row.role.is_system),
        isOwner=admin_access.WILDCARD in permissions,
        admins=row.admins,
    )


def _account_out(row: admin_access.AdminRow) -> AdminAccountOut:
    return AdminAccountOut(
        userId=row.user_id,
        name=row.user.name if row.user else "",
        username=(row.user.username or "") if row.user else "",
        roleId=row.role_id,
        roleTitle=row.role_title,
        permissions=row.permissions,
        note=row.note,
        grantedBy=row.granted_by,
    )


@router.get("/access", response_model=AdminAccessOut)
async def admin_access_overview(_: AccessViewer, session: SessionDep) -> AdminAccessOut:
    """Everything the access screen needs: permission catalog, roles, current admins."""
    roles = await admin_access.list_roles(session)
    admins = await admin_access.list_admins(session)
    return AdminAccessOut(
        permissions=[
            AdminPermissionOut(
                key=permission.key, group=permission.group, description=permission.description
            )
            for permission in admin_access.PERMISSIONS
        ],
        roles=[_role_out(row) for row in roles],
        admins=[_account_out(row) for row in admins],
    )


@router.post("/access/roles", response_model=AdminRoleOut)
async def create_role(
    payload: AdminRoleIn, actor: AccessManager, session: SessionDep
) -> AdminRoleOut:
    try:
        await admin_access.create_role(
            session,
            role_id=payload.id,
            title=payload.title,
            description=payload.description,
            permissions=payload.permissions,
            actor_id=actor.id,
        )
    except admin_access.AccessError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return await _one_role(session, payload.id.strip().lower())


@router.put("/access/roles/{role_id}", response_model=AdminRoleOut)
async def update_role(
    role_id: str, payload: AdminRoleUpdateIn, actor: AccessManager, session: SessionDep
) -> AdminRoleOut:
    if payload.permissions is not None and actor.identity.role_id == role_id:
        # Re-cutting your own role could lock you out mid-session; move yourself first.
        raise HTTPException(
            status_code=422, detail="You cannot change the permissions of your own role"
        )
    try:
        await admin_access.update_role(
            session,
            role_id,
            title=payload.title,
            description=payload.description,
            permissions=payload.permissions,
            actor_id=actor.id,
        )
    except admin_access.AccessError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return await _one_role(session, role_id)


@router.delete("/access/roles/{role_id}", status_code=204)
async def delete_role(role_id: str, actor: AccessManager, session: SessionDep) -> None:
    try:
        await admin_access.delete_role(session, role_id, actor_id=actor.id)
    except admin_access.AccessError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/access/admins", response_model=AdminAccountOut)
async def grant_admin(
    payload: AdminAccountIn, actor: AccessManager, session: SessionDep
) -> AdminAccountOut:
    """Grant or move admin access. The subject must already exist as a bot user."""
    try:
        row = await admin_access.grant_admin(
            session,
            payload.userId,
            role_id=payload.roleId,
            note=payload.note,
            actor_id=actor.id,
        )
    except admin_access.AccessError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _account_out(row)


@router.delete("/access/admins/{user_id}", status_code=204)
async def revoke_admin(user_id: int, actor: AccessManager, session: SessionDep) -> None:
    try:
        await admin_access.revoke_admin(session, user_id, actor_id=actor.id)
    except admin_access.AccessError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


async def _one_role(session: SessionDep, role_id: str) -> AdminRoleOut:
    for row in await admin_access.list_roles(session):
        if row.role.id == role_id:
            return _role_out(row)
    raise HTTPException(status_code=404, detail="Unknown role")
