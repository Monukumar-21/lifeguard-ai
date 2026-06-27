"""
A2A (Agent-to-Agent) Protocol Implementation for LifeGuard AI.

Implements Google's A2A open standard for inter-agent communication.
This module provides:
  1. AgentCard endpoints (/.well-known/agent.json) for agent discovery
  2. Task-based A2A endpoints for structured agent-to-agent messaging
  3. Agent registry for multi-agent collaboration

Architecture:
  External Agent  -->  A2A Task Endpoint  -->  LifeGuard Chat Agent
  Reminder Agent  <--  A2A Delegation     <--  Chat Agent (internal)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid

router = APIRouter(tags=["a2a"])


# ─────────────────────────────────────────────────────────────
# A2A Protocol Models (per Google A2A spec)
# ─────────────────────────────────────────────────────────────

class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class AgentSkill(BaseModel):
    id: str
    name: str
    description: str
    tags: List[str] = []
    examples: List[str] = []


class AgentCapabilities(BaseModel):
    streaming: bool = False
    pushNotifications: bool = True
    stateTransitionHistory: bool = False


class AgentCard(BaseModel):
    """A2A Agent Card — the 'business card' of an AI agent."""
    name: str
    description: str
    url: str
    version: str = "1.0.0"
    documentationUrl: Optional[str] = None
    capabilities: AgentCapabilities = AgentCapabilities()
    defaultInputModes: List[str] = ["text/plain"]
    defaultOutputModes: List[str] = ["text/plain"]
    skills: List[AgentSkill] = []


class Message(BaseModel):
    role: str  # "user" or "agent"
    parts: List[Dict[str, Any]]


class TaskStatus(BaseModel):
    state: TaskState
    message: Optional[Message] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus
    history: List[Message] = []
    metadata: Dict[str, Any] = {}


class TaskRequest(BaseModel):
    """Incoming A2A task request."""
    id: Optional[str] = None
    message: Message
    metadata: Dict[str, Any] = {}


class TaskResponse(BaseModel):
    """A2A task response."""
    id: str
    status: TaskStatus
    artifacts: List[Dict[str, Any]] = []


# ─────────────────────────────────────────────────────────────
# In-memory task store (for demo purposes)
# ─────────────────────────────────────────────────────────────

_task_store: Dict[str, Task] = {}


# ─────────────────────────────────────────────────────────────
# Agent Cards — Discovery endpoints
# ─────────────────────────────────────────────────────────────

CHAT_AGENT_CARD = AgentCard(
    name="LifeGuard Chat Agent",
    description="An AI accountability partner that manages tasks, reminders, goals, and productivity tracking via natural language on WhatsApp.",
    url="/a2a/chat",
    version="1.0.0",
    documentationUrl="https://github.com/Monukumar-21/lifeguard-ai",
    capabilities=AgentCapabilities(
        streaming=False,
        pushNotifications=True,
        stateTransitionHistory=True,
    ),
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/plain"],
    skills=[
        AgentSkill(
            id="task-management",
            name="Task Management",
            description="Create, update, delete, and list tasks with priorities and due dates.",
            tags=["tasks", "reminders", "scheduling"],
            examples=[
                "Remind me to call John at 5 PM",
                "What are my pending tasks?",
                "Mark task X as done",
                "Delete my grocery shopping task",
            ],
        ),
        AgentSkill(
            id="recurring-reminders",
            name="Recurring Reminders",
            description="Set up recurring reminders with a minimum 1-hour interval.",
            tags=["reminders", "recurring", "scheduling"],
            examples=[
                "Remind me to drink water every 1 hour",
                "Set a recurring reminder for standup every day",
            ],
        ),
        AgentSkill(
            id="productivity-analytics",
            name="Productivity Analytics",
            description="Get productivity stats including completion rate, overdue tasks, and weekly progress.",
            tags=["analytics", "stats", "productivity"],
            examples=[
                "How am I doing?",
                "Show my productivity stats",
                "What's my completion rate?",
            ],
        ),
        AgentSkill(
            id="goal-tracking",
            name="Goal Tracking",
            description="Track long-term goals and their progress.",
            tags=["goals", "progress"],
            examples=["What are my goals?", "Show goal progress"],
        ),
    ],
)

REMINDER_AGENT_CARD = AgentCard(
    name="LifeGuard Reminder Agent",
    description="Generates context-aware, personalized WhatsApp reminder messages using AI. Designed to be called by the Chat Agent via A2A delegation.",
    url="/a2a/reminder",
    version="1.0.0",
    capabilities=AgentCapabilities(streaming=False, pushNotifications=False),
    defaultInputModes=["application/json"],
    defaultOutputModes=["text/plain"],
    skills=[
        AgentSkill(
            id="smart-reminder-generation",
            name="Smart Reminder Generation",
            description="Generates a personalized, motivational reminder message given task context.",
            tags=["reminders", "ai", "generation"],
            examples=["Generate a reminder for 'Pitch Deck' due in 2 hours"],
        ),
    ],
)


# ─────────────────────────────────────────────────────────────
# A2A Endpoints
# ─────────────────────────────────────────────────────────────

@router.get("/.well-known/agent.json")
async def get_agent_card():
    """
    A2A Agent Card discovery endpoint.
    Returns all registered agent cards for this platform.
    """
    return {
        "agents": [
            CHAT_AGENT_CARD.model_dump(),
            REMINDER_AGENT_CARD.model_dump(),
        ]
    }


@router.post("/a2a/chat")
async def a2a_chat_task(request: TaskRequest):
    """
    A2A Task endpoint for the Chat Agent.
    Accepts structured task requests from other agents or external systems.
    """
    from backend.agents.chat_agent import chat_with_agent

    task_id = request.id or str(uuid.uuid4())

    # Extract text from the message parts
    text_parts = [p.get("text", "") for p in request.message.parts if "text" in p]
    user_message = " ".join(text_parts)

    # Extract user_id from metadata (required for our tools)
    user_id = request.metadata.get("user_id", "00000000-0000-0000-0000-000000000000")
    user_timezone = request.metadata.get("timezone", "UTC")

    # Create task in WORKING state
    task = Task(
        id=task_id,
        status=TaskStatus(state=TaskState.WORKING),
        history=[request.message],
        metadata=request.metadata,
    )
    _task_store[task_id] = task

    try:
        # Delegate to the chat agent
        response_text = await chat_with_agent(
            message=user_message,
            user_id=user_id,
            user_timezone=user_timezone,
        )

        # Update task to COMPLETED
        response_message = Message(
            role="agent",
            parts=[{"text": response_text}],
        )
        task.status = TaskStatus(
            state=TaskState.COMPLETED,
            message=response_message,
        )
        task.history.append(response_message)

        return TaskResponse(
            id=task_id,
            status=task.status,
            artifacts=[{"parts": [{"text": response_text}]}],
        )

    except Exception as e:
        task.status = TaskStatus(
            state=TaskState.FAILED,
            message=Message(role="agent", parts=[{"text": f"Error: {str(e)}"}]),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/a2a/reminder")
async def a2a_reminder_task(request: TaskRequest):
    """
    A2A Task endpoint for the Reminder Agent.
    Generates a smart reminder message via A2A delegation from the Chat Agent.
    """
    from backend.agents.reminder_agent import generate_smart_reminder
    from backend.models import Task as TaskModel, User
    from backend.database import AsyncSessionLocal
    from sqlalchemy.future import select

    task_id = request.id or str(uuid.uuid4())

    # Extract task_id and user_id from metadata
    db_task_id = request.metadata.get("task_id")
    db_user_id = request.metadata.get("user_id")

    if not db_task_id or not db_user_id:
        raise HTTPException(status_code=400, detail="task_id and user_id required in metadata")

    async with AsyncSessionLocal() as session:
        task_result = await session.execute(
            select(TaskModel).where(TaskModel.id == uuid.UUID(db_task_id))
        )
        task_obj = task_result.scalar_one_or_none()

        user_result = await session.execute(
            select(User).where(User.id == uuid.UUID(db_user_id))
        )
        user_obj = user_result.scalar_one_or_none()

    if not task_obj or not user_obj:
        raise HTTPException(status_code=404, detail="Task or User not found")

    reminder_text = generate_smart_reminder(task_obj, user_obj)

    response_message = Message(
        role="agent",
        parts=[{"text": reminder_text}],
    )

    return TaskResponse(
        id=task_id,
        status=TaskStatus(
            state=TaskState.COMPLETED,
            message=response_message,
        ),
        artifacts=[{"parts": [{"text": reminder_text}]}],
    )


@router.get("/a2a/tasks/{task_id}")
async def get_a2a_task(task_id: str):
    """Get the status of an A2A task by ID."""
    task = _task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(
        id=task.id,
        status=task.status,
        artifacts=[],
    )
