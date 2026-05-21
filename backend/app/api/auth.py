from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import UserCreate, UserLogin, Token, UserResponse, PasswordResetRequest, PasswordResetConfirm, EmailVerify, TwoFactorResponse, TwoFactorSetup
from app.services import auth_service
from app.core.security import get_current_user
from app.models import User

router = APIRouter()


@router.post("/register", response_model=dict)
async def register(user_data: UserCreate, request: Request, db: AsyncSession = Depends(get_db)):
    result = await auth_service.register_user(db, user_data)
    return {
        "message": "Registration successful. Please check your email to verify your account.",
        "user_id": str(result["user"].id),
    }


@router.post("/login", response_model=Token)
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await auth_service.login_user(db, login_data)
    if result.get("requires_2fa"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="2FA required", headers={"X-2FA-Required": "true"})
    return Token(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
    )


@router.post("/verify-email")
async def verify_email(data: EmailVerify, db: AsyncSession = Depends(get_db)):
    await auth_service.verify_email(db, data.token)
    return {"message": "Email verified successfully"}


@router.post("/password-reset/request")
async def request_password_reset(data: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    token = await auth_service.request_password_reset(db, data.email)
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/password-reset/confirm")
async def confirm_password_reset(data: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    await auth_service.reset_password(db, data.token, data.new_password)
    return {"message": "Password reset successfully"}


@router.post("/refresh")
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    return await auth_service.refresh_access_token(db, refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/2fa/setup", response_model=TwoFactorResponse)
async def setup_2fa(current_user: User = Depends(get_current_user)):
    import pyotp
    import qrcode
    import base64
    from io import BytesIO

    if current_user.two_factor_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA already enabled")

    secret = pyotp.random_base32()
    current_user.two_factor_secret = secret

    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(current_user.email, issuer_name="BinBot")

    img = qrcode.make(uri)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return {"secret": secret, "qr_code_url": f"data:image/png;base64,{qr_base64}"}


@router.post("/2fa/enable")
async def enable_2fa(data: TwoFactorSetup, current_user: User = Depends(get_current_user)):
    import pyotp
    if not current_user.two_factor_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Setup 2FA first")
    totp = pyotp.TOTP(current_user.two_factor_secret)
    if not totp.verify(data.totp_code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")
    current_user.two_factor_enabled = True
    return {"message": "2FA enabled successfully"}


@router.post("/2fa/disable")
async def disable_2fa(data: TwoFactorSetup, current_user: User = Depends(get_current_user)):
    import pyotp
    if not current_user.two_factor_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA not enabled")
    totp = pyotp.TOTP(current_user.two_factor_secret)
    if not totp.verify(data.totp_code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")
    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    return {"message": "2FA disabled successfully"}
