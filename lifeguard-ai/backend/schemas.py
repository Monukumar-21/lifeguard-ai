from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid
from .models import TaskStatus, GoalStatus, SubscriptionStatus, ReminderType

# --- User Schemas ---
class UserBase(BaseModel):
    clerk_id: str
    whatsapp_number: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    timezone: str = "UTC"

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

# --- Goal Schemas ---
class GoalBase(BaseModel):
    title: str
    description: Optional[str] = None
    target_date: Optional[datetime] = None
    status: GoalStatus = GoalStatus.ACTIVE

class GoalCreate(GoalBase):
    pass

class GoalResponse(GoalBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Task Schemas ---
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 1

class TaskCreate(TaskBase):
    goal_id: Optional[uuid.UUID] = None

class TaskResponse(TaskBase):
    id: uuid.UUID
    user_id: uuid.UUID
    goal_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Reminder Schemas ---
class ReminderBase(BaseModel):
    reminder_time: datetime
    reminder_type: ReminderType = ReminderType.WHATSAPP
    is_sent: bool = False

class ReminderCreate(ReminderBase):
    task_id: uuid.UUID

class ReminderResponse(ReminderBase):
    id: uuid.UUID
    task_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

# --- WhatsApp Webhook Schema ---
class WhatsAppMessage(BaseModel):
    from_number: str
    text: str
    timestamp: Optional[str] = None
