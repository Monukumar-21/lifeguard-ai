import os
import uuid
import google.generativeai as genai
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.future import select
from backend.database import AsyncSessionLocal
from backend.models import Task, User, Goal, Subscription, TaskStatus

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
        if not tasks: return "No pending tasks."
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
        if not tasks: return f"No deadlines in next {days} days."
        return "\n".join([f"- {t.title} (Due: {t.due_date.strftime('%Y-%m-%d')})" for t in tasks])

async def fetch_subscriptions(user_id: str) -> str:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Subscription).where(Subscription.user_id == uuid.UUID(user_id)))
        subs = result.scalars().all()
        if not subs: return "No active subscriptions."
        return "\n".join([f"- Plan: {s.plan_id} (Status: {s.status.value})" for s in subs])

async def fetch_goal_progress(user_id: str) -> str:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Goal).where(Goal.user_id == uuid.UUID(user_id)))
        goals = result.scalars().all()
        if not goals: return "No active goals."
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
        if not tasks: return "No tasks currently at risk or overdue."
        return "\n".join([f"- OVERDUE: {t.title} (Was due: {t.due_date.strftime('%Y-%m-%d')})" for t in tasks])

tool_declarations = [
    {
        "name": "get_todays_priorities",
        "description": "Returns the top 3 highest priority tasks for the user today.",
        "parameters": {"type": "object", "properties": {"user_id": {"type": "string"}}, "required": ["user_id"]}
    },
    {
        "name": "get_upcoming_deadlines",
        "description": "Returns tasks that are due within the specified number of days.",
        "parameters": {"type": "object", "properties": {"user_id": {"type": "string"}, "days": {"type": "integer"}}, "required": ["user_id"]}
    },
    {
        "name": "get_subscriptions",
        "description": "Returns the user's active subscriptions.",
        "parameters": {"type": "object", "properties": {"user_id": {"type": "string"}}, "required": ["user_id"]}
    },
    {
        "name": "get_goal_progress",
        "description": "Returns the user's goals and their completion status.",
        "parameters": {"type": "object", "properties": {"user_id": {"type": "string"}}, "required": ["user_id"]}
    },
    {
        "name": "get_risk_tasks",
        "description": "Returns tasks that are overdue or highly likely to be missed.",
        "parameters": {"type": "object", "properties": {"user_id": {"type": "string"}}, "required": ["user_id"]}
    }
]

async def chat_with_agent(message: str, user_id: str, history: List[Dict[str, Any]] = None) -> str:
    """
    Main function to handle conversational AI with tool calling capabilities.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        
    system_prompt = (
        "You are LifeGuard AI, a strict but supportive accountability partner. "
        "Use your tools to pull the user's data when they ask about their tasks, goals, or schedule. "
        f"The user_id is {user_id}. Always pass this exact user_id to your tools. "
        "Format responses for WhatsApp (use *bold* for emphasis, be concise, use emojis appropriately). "
        "Do not output markdown headers."
    )
    
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        tools=[{"function_declarations": tool_declarations}],
        system_instruction=system_prompt
    )
    
    formatted_history = []
    if history:
        for msg in history[-10:]:
            role = "user" if msg["is_from_user"] else "model"
            formatted_history.append({"role": role, "parts": [msg["message"]]})
            
    chat = model.start_chat(history=formatted_history)

    try:
        response = await chat.send_message_async(message)
        
        while response.function_call:
            fc = response.function_call
            name = fc.name
            
            # Convert protobuf args to dict safely
            args = {}
            for k in fc.args:
                args[k] = fc.args[k]
                
            uid = args.get("user_id", str(user_id))
            
            if name == "get_todays_priorities":
                result_str = await fetch_todays_priorities(uid)
            elif name == "get_upcoming_deadlines":
                result_str = await fetch_upcoming_deadlines(uid, int(args.get("days", 7)))
            elif name == "get_subscriptions":
                result_str = await fetch_subscriptions(uid)
            elif name == "get_goal_progress":
                result_str = await fetch_goal_progress(uid)
            elif name == "get_risk_tasks":
                result_str = await fetch_risk_tasks(uid)
            else:
                result_str = "Unknown function."
                
            response = await chat.send_message_async(
                genai.types.Part.from_function_response(
                    name=name,
                    response={"result": result_str}
                )
            )
            
        return response.text
    except Exception as e:
        print(f"Chat agent error: {e}")
        return "I'm here to help you stay on track. Tell me your next goal! 💪"
