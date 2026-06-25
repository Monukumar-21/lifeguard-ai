from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.database import get_db
from backend.models import Subscription, User
import uuid

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

@router.get("/status")
async def get_subscription_status(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    sub = result.scalar_one_or_none()
    if not sub:
        return {"status": "inactive", "plan": "none"}
    return {"status": sub.status.value, "plan": sub.plan_id}
