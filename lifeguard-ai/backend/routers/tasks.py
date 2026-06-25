from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from backend.database import get_db
from backend.models import Task
from backend.schemas import TaskCreate, TaskResponse
import uuid

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", response_model=TaskResponse)
async def create_task(task_in: TaskCreate, user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    new_task = Task(**task_in.model_dump(), user_id=user_id)
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task

@router.get("/", response_model=List[TaskResponse])
async def list_tasks(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.user_id == user_id))
    tasks = result.scalars().all()
    return tasks
