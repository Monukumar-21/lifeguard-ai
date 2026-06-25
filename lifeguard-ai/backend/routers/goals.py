from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from backend.database import get_db
from backend.models import Goal
from backend.schemas import GoalCreate, GoalResponse
import uuid

router = APIRouter(prefix="/goals", tags=["goals"])

@router.post("/", response_model=GoalResponse)
async def create_goal(goal_in: GoalCreate, user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    new_goal = Goal(**goal_in.model_dump(), user_id=user_id)
    db.add(new_goal)
    await db.commit()
    await db.refresh(new_goal)
    return new_goal

@router.get("/", response_model=List[GoalResponse])
async def list_goals(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal).where(Goal.user_id == user_id))
    goals = result.scalars().all()
    return goals
