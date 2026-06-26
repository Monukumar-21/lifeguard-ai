import os
import uuid
from google import genai
from google.genai import types
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.future import select
from backend.database import AsyncSessionLocal
from backend.models import Task, User, Goal, Subscription, TaskStatus

# ─────────────────────────────────────────────
# DB helper functions (unchanged from your original)
# ─────────────────────────────────────────────

async def fetch_todays_priorities(user_id: str) -> str:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Task)
            .where(Task.user_id == uuid.UUID(user_id))
            .where(Task.status == TaskStatus.PENDING)
            .order_by(Task.priority.desc())
            .limit(3)
        )
        tasks = result.scalars().all()
        if not tasks:
            return "No pending tasks."
        return "\n".join([f"- {t.title} (Priority: {t.priority})" for t in tasks])


async def fetch_upcoming_deadlines(user_id: str, days: int = 7) -> str:
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=days)
        result = await session.execute(
            select(Task)
            .where(Task.user_id == uuid.UUID(user_id))
            .where(Task.status == TaskStatus.PENDING)
            .where(Task.due_date.isnot(None))
            .where(Task.due_date >= now)
            .where(Task.due_date <= future)
            .order_by(Task.due_date.asc())
        )
        tasks = result.scalars().all()
        if not tasks:
            return f"No deadlines in next {days} days."
        return "\n".join([f"- {t.title} (Due: {t.due_date.strftime('%Y-%m-%d')})" for t in tasks])


async def fetch_subscriptions(user_id: str) -> str:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Subscription).where(Subscription.user_id == uuid.UUID(user_id))
        )
        subs = result.scalars().all()
        if not subs:
            return "No active subscriptions."
        return "\n".join([f"- Plan: {s.plan_id} (Status: {s.status.value})" for s in subs])


async def fetch_goal_progress(user_id: str) -> str:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Goal).where(Goal.user_id == uuid.UUID(user_id))
        )
        goals = result.scalars().all()
        if not goals:
            return "No active goals."
        return "\n".join([f"- Goal: {g.title} (Status: {g.status.value})" for g in goals])


async def fetch_risk_tasks(user_id: str) -> str:
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        result = await session.execute(
            select(Task)
            .where(Task.user_id == uuid.UUID(user_id))
            .where(Task.status == TaskStatus.PENDING)
            .where(Task.due_date.isnot(None))
            .where(Task.due_date < now)
        )
        tasks = result.scalars().all()
        if not tasks:
            return "No tasks currently at risk or overdue."
        return "\n".join([
            f"- OVERDUE: {t.title} (Was due: {t.due_date.strftime('%Y-%m-%d')})"
            for t in tasks
        ])


# ─────────────────────────────────────────────
# Tool declarations — now using new SDK types
# ─────────────────────────────────────────────

tool_declarations = [
    types.FunctionDeclaration(
        name="get_todays_priorities",
        description="Returns the top 3 highest priority tasks for the user today.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"user_id": types.Schema(type=types.Type.STRING)},
            required=["user_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_upcoming_deadlines",
        description="Returns tasks that are due within the specified number of days.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "user_id": types.Schema(type=types.Type.STRING),
                "days": types.Schema(type=types.Type.INTEGER),
            },
            required=["user_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_subscriptions",
        description="Returns the user's active subscriptions.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"user_id": types.Schema(type=types.Type.STRING)},
            required=["user_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_goal_progress",
        description="Returns the user's goals and their completion status.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"user_id": types.Schema(type=types.Type.STRING)},
            required=["user_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_risk_tasks",
        description="Returns tasks that are overdue or highly likely to be missed.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"user_id": types.Schema(type=types.Type.STRING)},
            required=["user_id"],
        ),
    ),
]

TOOLS = [types.Tool(function_declarations=tool_declarations)]


# ─────────────────────────────────────────────
# Tool dispatcher
# ─────────────────────────────────────────────

async def _dispatch_tool(name: str, args: dict, user_id: str) -> str:
    uid = args.get("user_id", str(user_id))
    if name == "get_todays_priorities":
        return await fetch_todays_priorities(uid)
    elif name == "get_upcoming_deadlines":
        return await fetch_upcoming_deadlines(uid, int(args.get("days", 7)))
    elif name == "get_subscriptions":
        return await fetch_subscriptions(uid)
    elif name == "get_goal_progress":
        return await fetch_goal_progress(uid)
    elif name == "get_risk_tasks":
        return await fetch_risk_tasks(uid)
    return "Unknown function."


# ─────────────────────────────────────────────
# Main agent entry point
# ─────────────────────────────────────────────

async def chat_with_agent(
    message: str,
    user_id: str,
    history: List[Dict[str, Any]] = None,
) -> str:
    """
    Handles conversational AI with tool-calling via the new google-genai SDK.
    FIX: replaced deprecated google-generativeai SDK and fixed function_call access.
    """
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    system_prompt = (
        "You are LifeGuard AI, a strict but supportive accountability partner. "
        "Use your tools to pull the user's data when they ask about their tasks, goals, or schedule. "
        f"The user_id is {user_id}. Always pass this exact user_id to your tools. "
        "Format responses for WhatsApp (use *bold* for emphasis, be concise, use emojis appropriately). "
        "Do not output markdown headers."
    )

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=TOOLS,
    )

    # Build contents list from history + new message
    contents: List[types.Content] = []
    if history:
        for msg in history[-10:]:
            role = "user" if msg["is_from_user"] else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part(text=msg["message"])])
            )
    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

    try:
        # Agentic loop — keep calling until no more function calls
        while True:
            response = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=config,
            )

            # FIX: function calls live in parts, not on the response directly
            candidate = response.candidates[0]
            fc_part = next(
                (p for p in candidate.content.parts if p.function_call),
                None,
            )

            if fc_part is None:
                # No more tool calls — return the final text answer
                return response.text

            # Execute the tool
            fc = fc_part.function_call
            args = dict(fc.args) if fc.args else {}
            result_str = await _dispatch_tool(fc.name, args, user_id)

            # Append model turn (with the function call) to contents
            contents.append(
                types.Content(role="model", parts=[types.Part(function_call=fc)])
            )
            # Append the tool result as a user turn
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=fc.name,
                                response={"result": result_str},
                            )
                        )
                    ],
                )
            )
            # Loop continues → model will now produce the final reply

    except Exception as e:
        print(f"Chat agent error: {e}")
        return "I'm here to help you stay on track. Tell me your next goal! 💪"