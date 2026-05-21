from typing import Optional

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import User

settings = get_settings()
stripe.api_key = settings.STRIPE_SECRET_KEY

PLANS = {
    "free": {
        "name": "Free",
        "price": 0,
        "max_bots": 1,
        "features": ["Paper trading only", "1 bot", "Basic indicators", "Email support"],
    },
    "starter": {
        "name": "Starter",
        "price": 29,
        "max_bots": 3,
        "features": ["3 bots", "Backtesting", "Basic strategies", "Live trading", "Priority support"],
    },
    "pro": {
        "name": "Pro",
        "price": 99,
        "max_bots": -1,
        "features": ["Unlimited bots", "Advanced AI strategies", "ML predictions", "Analytics dashboard", "All strategies", "Priority support"],
    },
    "enterprise": {
        "name": "Enterprise",
        "price": 299,
        "max_bots": -1,
        "features": ["White-label support", "API access", "Team management", "Custom strategies", "Dedicated support", "SLA"],
    },
}


class BillingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_checkout_session(self, user_id: str, plan: str) -> dict:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        if plan not in PLANS:
            raise ValueError(f"Invalid plan: {plan}")

        price_id = getattr(settings, f"STRIPE_PRICE_{plan.upper()}")
        if not price_id:
            raise ValueError(f"Stripe price not configured for plan: {plan}")

        if not user.stripe_customer_id:
            customer = stripe.Customer.create(email=user.email, name=user.name)
            user.stripe_customer_id = customer.id
            await self.db.flush()

        session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{settings.FRONTEND_URL}/dashboard/billing?success=true",
            cancel_url=f"{settings.FRONTEND_URL}/dashboard/billing?canceled=true",
            metadata={"user_id": str(user_id), "plan": plan},
        )

        return {"url": session.url, "session_id": session.id}

    async def handle_webhook(self, payload: bytes, sig: str) -> dict:
        try:
            event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
        except ValueError:
            raise ValueError("Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise ValueError("Invalid signature")

        if event.type == "checkout.session.completed":
            await self._handle_checkout_completed(event.data.object)
        elif event.type == "customer.subscription.created":
            await self._handle_subscription_created(event.data.object)
        elif event.type == "customer.subscription.updated":
            await self._handle_subscription_updated(event.data.object)
        elif event.type == "customer.subscription.deleted":
            await self._handle_subscription_deleted(event.data.object)
        elif event.type == "invoice.payment_failed":
            await self._handle_payment_failed(event.data.object)

        return {"status": "success"}

    async def _handle_checkout_completed(self, session):
        user_id = session.metadata.get("user_id")
        if user_id:
            result = await self.db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                user.plan = session.metadata.get("plan", "starter")
                user.subscription_status = "active"
                await self.db.flush()

    async def _handle_subscription_created(self, subscription):
        customer_id = subscription.customer
        result = await self.db.execute(select(User).where(User.stripe_customer_id == customer_id))
        user = result.scalar_one_or_none()
        if user:
            from datetime import datetime, timezone
            from app.models import Subscription as SubModel
            import uuid
            sub = SubModel(
                id=uuid.uuid4(),
                user_id=user.id,
                stripe_subscription_id=subscription.id,
                stripe_price_id=subscription.items.data[0].price.id if subscription.items.data else None,
                plan=user.plan,
                status=subscription.status,
                current_period_start=datetime.fromtimestamp(subscription.current_period_start, tz=timezone.utc),
                current_period_end=datetime.fromtimestamp(subscription.current_period_end, tz=timezone.utc),
            )
            self.db.add(sub)
            await self.db.flush()

    async def _handle_subscription_updated(self, subscription):
        result = await self.db.execute(select(User).where(User.stripe_customer_id == subscription.customer))
        user = result.scalar_one_or_none()
        if user:
            user.subscription_status = subscription.status
            if subscription.cancel_at_period_end:
                from app.models import Subscription as SubModel
                from sqlalchemy import select as sa_select
                sub_result = await self.db.execute(sa_select(SubModel).where(SubModel.stripe_subscription_id == subscription.id))
                sub = sub_result.scalar_one_or_none()
                if sub:
                    sub.cancel_at_period_end = True
            await self.db.flush()

    async def _handle_subscription_deleted(self, subscription):
        result = await self.db.execute(select(User).where(User.stripe_customer_id == subscription.customer))
        user = result.scalar_one_or_none()
        if user:
            user.plan = "free"
            user.subscription_status = "canceled"
            await self.db.flush()

    async def _handle_payment_failed(self, invoice):
        customer_id = invoice.customer
        result = await self.db.execute(select(User).where(User.stripe_customer_id == customer_id))
        user = result.scalar_one_or_none()
        if user:
            user.subscription_status = "past_due"
            await self.db.flush()

    async def cancel_subscription(self, user_id: str) -> dict:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.stripe_customer_id:
            raise ValueError("No active subscription")

        subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id, status="active")
        if subscriptions.data:
            sub = subscriptions.data[0]
            stripe.Subscription.modify(sub.id, cancel_at_period_end=True)

        user.subscription_status = "canceling"
        await self.db.flush()

        return {"status": "canceled", "message": "Subscription will end at period end"}

    def get_plan_info(self, plan: str) -> dict:
        return PLANS.get(plan, PLANS["free"])

    def can_create_bot(self, plan: str, current_bot_count: int) -> bool:
        plan_info = self.get_plan_info(plan)
        max_bots = plan_info["max_bots"]
        return max_bots == -1 or current_bot_count < max_bots
