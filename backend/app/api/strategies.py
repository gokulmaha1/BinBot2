from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.schemas import StrategyResponse
from app.services.strategy_engine import STRATEGIES
from sqlalchemy import select

router = APIRouter()


@router.get("/", response_model=list[StrategyResponse])
async def list_strategies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models import Strategy as StrategyModel
    result = await db.execute(select(StrategyModel).where(StrategyModel.is_active))
    db_strategies = result.scalars().all()

    response = []
    for s in db_strategies:
        if s.is_premium and current_user.plan == "free":
            continue
        response.append(s)

    if not response:
        for name, strategy in STRATEGIES.items():
            response.append(StrategyResponse(
                id="00000000-0000-0000-0000-000000000000",
                name=strategy.name,
                description=strategy.description,
                config_schema={},
                category="default",
                risk_level="medium",
                min_leverage=1,
                max_leverage=5,
                is_active=True,
                is_premium=False,
            ))

    return response


@router.get("/{strategy_name}")
async def get_strategy(strategy_name: str):
    strategy = STRATEGIES.get(strategy_name)
    if not strategy:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"name": strategy.name, "description": strategy.description}
