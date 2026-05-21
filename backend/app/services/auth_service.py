import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from app.models import User
from app.schemas import UserCreate, UserLogin


async def register_user(db: AsyncSession, user_data: UserCreate) -> dict:
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        id=uuid.uuid4(),
        name=user_data.name,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        verification_token=str(uuid.uuid4()),
    )
    db.add(user)
    await db.flush()

    return {
        "user": user,
        "verification_token": user.verification_token,
    }


async def login_user(db: AsyncSession, login_data: UserLogin) -> dict:
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")

    if user.two_factor_enabled:
        if not login_data.totp_code:
            return {"requires_2fa": True, "user_id": str(user.id)}
        import pyotp
        totp = pyotp.TOTP(user.two_factor_secret)
        if not totp.verify(login_data.totp_code):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid 2FA code")

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user,
    }


async def verify_email(db: AsyncSession, token: str) -> User:
    result = await db.execute(select(User).where(User.verification_token == token))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")
    user.is_verified = True
    user.verification_token = None
    return user


async def request_password_reset(db: AsyncSession, email: str) -> str | None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return None
    reset_token = str(uuid.uuid4())
    user.reset_token = reset_token
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    return reset_token


async def reset_password(db: AsyncSession, token: str, new_password: str) -> User:
    result = await db.execute(select(User).where(User.reset_token == token))
    user = result.scalar_one_or_none()
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    user.password_hash = get_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    return user


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> dict:
    from app.core.security import decode_token
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or disabled")
    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
