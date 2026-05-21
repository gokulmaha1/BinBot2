from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: datetime
    type: str


class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(None, min_length=8)


class UserResponse(UserBase):
    id: UUID
    role: str
    plan: str
    subscription_status: str
    is_verified: bool
    two_factor_enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class EmailVerify(BaseModel):
    token: str


class TwoFactorSetup(BaseModel):
    totp_code: str


class TwoFactorResponse(BaseModel):
    secret: str
    qr_code_url: str


class ExchangeAccountCreate(BaseModel):
    exchange: str = "binance"
    api_key: str
    api_secret: str
    testnet: bool = True


class ExchangeAccountResponse(BaseModel):
    id: UUID
    exchange: str
    testnet: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class BotCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    strategy: str
    symbol: str
    leverage: int = Field(ge=1, le=5, default=1)
    live_mode: bool = False
    config: dict = {}
    risk_config: Optional[dict] = None


class BotUpdate(BaseModel):
    name: Optional[str] = None
    strategy: Optional[str] = None
    leverage: Optional[int] = Field(None, ge=1, le=5)
    status: Optional[str] = None
    config: Optional[dict] = None
    risk_config: Optional[dict] = None


class BotResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    strategy: str
    symbol: str
    leverage: int
    status: str
    live_mode: bool
    total_pnl: float
    win_rate: float
    total_trades: int
    created_at: datetime

    class Config:
        from_attributes = True


class TradeResponse(BaseModel):
    id: UUID
    bot_id: UUID
    symbol: str
    side: str
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    leverage: int
    stop_loss: Optional[float]
    take_profit: Optional[float]
    pnl: float
    pnl_percentage: float
    status: str
    exit_reason: Optional[str]
    strategy_used: Optional[str]
    ml_confidence: Optional[float]
    entry_timestamp: datetime
    exit_timestamp: Optional[datetime]

    class Config:
        from_attributes = True


class BacktestRequest(BaseModel):
    strategy: str
    symbol: str
    timeframe: str = "1h"
    start_date: datetime
    end_date: datetime
    initial_capital: float = 10000.0
    config: dict = {}


class BacktestResponse(BaseModel):
    id: UUID
    strategy: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    result: dict
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class StrategyResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    config_schema: dict
    category: str
    risk_level: str
    min_leverage: int
    max_leverage: int
    is_active: bool
    is_premium: bool

    class Config:
        from_attributes = True


class AnalyticsResponse(BaseModel):
    total_pnl: float
    daily_pnl: list[dict]
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    max_drawdown: float
    sharpe_ratio: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    active_positions: list[TradeResponse]
    trade_history: list[TradeResponse]


class SubscriptionResponse(BaseModel):
    plan: str
    status: str
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool
    max_bots: int
    features: list[str]


class AdminUserResponse(UserResponse):
    total_bots: int
    total_trades: float
    subscription_revenue: float


class AuditLogResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    action: str
    resource: Optional[str]
    details: Optional[dict]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
