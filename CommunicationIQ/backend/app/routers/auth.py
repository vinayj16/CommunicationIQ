"""Sign-in and session.

Two populations sign in here: platform staff (control plane) and institution
users (students, trainers, tenant admins). The email decides which, and the
issued token carries the answer. A caller never states which institution they
belong to — the directory does, once, at sign-in.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.db import tenant_sessionmaker
from app.deps import PlatformSession, Principal, TenantSession
from app.models.platform import PlatformUser, Tenant, TenantUserDirectory
from app.models.tenant import User
from app.schemas import (ChangePasswordRequest, LoginRequest, LoginResponse,
                         SessionUser)
from app.security import (TokenPrincipal, create_token, hash_password,
                          verify_password)

router = APIRouter(prefix="/auth", tags=["auth"])

# One message for every sign-in failure. Distinguishing "no such account" from
# "wrong password" tells an attacker which emails are registered.
_REJECT = "Incorrect email or password"


def _branding_fields(tenant) -> dict:
    """Branding for the session payload, or empty where a tenant has none.

    Empty rather than defaulted: the shell falls back to the product mark when
    these are absent, and inventing a display name here would stop it ever
    doing that.
    """
    raw = (tenant.branding or {}) if tenant is not None else {}
    return {
        "tenant_display_name": raw.get("display_name") or None,
        "tenant_logo_url": raw.get("logo_url") or None,
        "tenant_primary_color": raw.get("primary_color") or None,
    }


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, session: PlatformSession) -> LoginResponse:
    email = body.email.lower().strip()

    staff = (await session.execute(
        select(PlatformUser).where(PlatformUser.email == email)
    )).scalar_one_or_none()

    if staff is not None:
        if not staff.active or not verify_password(body.password, staff.password_hash):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, _REJECT)
        staff.last_login_at = datetime.now(timezone.utc)
        await session.commit()
        principal = TokenPrincipal(
            user_id=staff.id, email=staff.email, full_name=staff.full_name,
            role=staff.role, scope="platform",
        )
        return LoginResponse(
            token=create_token(principal),
            user=SessionUser(
                id=staff.id, email=staff.email, full_name=staff.full_name,
                role=staff.role, scope="platform",
            ),
        )

    entry = (await session.execute(
        select(TenantUserDirectory).where(TenantUserDirectory.email == email)
    )).scalar_one_or_none()
    if entry is None or not entry.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _REJECT)

    tenant = await session.get(Tenant, entry.tenant_id)
    if tenant is None or tenant.status in {"suspended", "closed"}:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "This institution's access is not currently active")

    async with tenant_sessionmaker(entry.tenant_slug)() as tsession:
        user = (await tsession.execute(
            select(User).where(User.email == email)
        )).scalar_one_or_none()
        if user is None or not user.active or not verify_password(body.password, user.password_hash):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, _REJECT)
        user.last_login_at = datetime.now(timezone.utc)
        await tsession.commit()

        principal = TokenPrincipal(
            user_id=user.id, email=user.email, full_name=user.full_name,
            role=user.role, scope="tenant",
            tenant_id=tenant.id, tenant_slug=tenant.slug,
        )
        return LoginResponse(
            token=create_token(principal),
            user=SessionUser(
                id=user.id, email=user.email, full_name=user.full_name,
                role=user.role, scope="tenant",
                tenant_id=tenant.id, tenant_slug=tenant.slug, tenant_name=tenant.name,
                **_branding_fields(tenant),
                must_change_password=user.must_change_password,
                ui_language=user.ui_language, preferred_theme=user.preferred_theme,
            ),
        )


@router.get("/me", response_model=SessionUser)
async def me(principal: Principal, session: PlatformSession) -> SessionUser:
    if principal.is_platform:
        return SessionUser(
            id=principal.user_id, email=principal.email,
            full_name=principal.full_name, role=principal.role, scope="platform",
        )

    tenant = await session.get(Tenant, principal.tenant_id) if principal.tenant_id else None
    async with tenant_sessionmaker(principal.tenant_slug or "")() as tsession:
        user = await tsession.get(User, principal.user_id)
        if user is None or not user.active:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account is no longer active")
        return SessionUser(
            id=user.id, email=user.email, full_name=user.full_name, role=user.role,
            scope="tenant", tenant_id=principal.tenant_id,
            tenant_slug=principal.tenant_slug,
            tenant_name=tenant.name if tenant else None,
            **_branding_fields(tenant),
            must_change_password=user.must_change_password,
            ui_language=user.ui_language, preferred_theme=user.preferred_theme,
        )


# response_model=None is required, not decoration: with postponed annotations
# the `-> None` return hint resolves to NoneType, which FastAPI reads as a real
# response model and then refuses to pair with 204.
@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT,
             response_class=Response, response_model=None)
async def change_password(body: ChangePasswordRequest, principal: Principal,
                          session: TenantSession) -> None:
    user = await session.get(User, principal.user_id)
    if user is None or not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    await session.commit()


@router.put("/preferences", response_model=SessionUser)
async def update_preferences(principal: Principal, session: TenantSession,
                             ui_language: str | None = None,
                             preferred_theme: str | None = None) -> SessionUser:
    """Personal display preferences. Theme is per account, never per browser."""
    user = await session.get(User, principal.user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if ui_language is not None:
        user.ui_language = ui_language
    if preferred_theme is not None:
        user.preferred_theme = preferred_theme
    await session.commit()
    return SessionUser(
        id=user.id, email=user.email, full_name=user.full_name, role=user.role,
        scope="tenant", tenant_id=principal.tenant_id, tenant_slug=principal.tenant_slug,
        must_change_password=user.must_change_password,
        ui_language=user.ui_language, preferred_theme=user.preferred_theme,
    )
