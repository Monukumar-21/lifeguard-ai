import os
import uuid
from google import genai
from google.genai import types
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.future import select
from backend.database import AsyncSessionLocal
from backend.models import Task, Goal, Subscription, Reminder, TaskStatus, ReminderType, User
import pytz

# ─────────────────────────────────────────────────────────────
# READ TOOLS
# ─────────────────────────────────────────────────────────────

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
        return "\n".join([f"- [{t.id}] {t.title} (Due: {t.due_date.strftime('%Y-%m-%d %H:%M UTC')})" for t in tasks])


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

async def fetch_all_pending_tasks(user_id: str) -> str:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Task)
            .where(Task.user_id == uuid.UUID(user_id))
            .where(Task.status == TaskStatus.PENDING)
            .order_by(Task.created_at.desc())
            .limit(50)
        )
        tasks = result.scalars().all()
        if not tasks:
            return "No pending tasks."
        return "\n".join([f"- [{t.id}] {t.title} (Priority: {t.priority})" for t in tasks])


# ─────────────────────────────────────────────────────────────
# WRITE TOOLS
# ─────────────────────────────────────────────────────────────

async def create_task_with_reminder(
    user_id: str,
    title: str,
    reminder_time_iso: str,
    priority: int = 3,
    description: Optional[str] = None,
    due_date_iso: Optional[str] = None,
    recurring_interval_minutes: Optional[int] = None,
) -> str:
    """
    Creates a Task row and an attached Reminder row in a single transaction.
    reminder_time_iso and due_date_iso must be UTC ISO-8601 strings.
    """
    try:
        reminder_dt = datetime.fromisoformat(reminder_time_iso.replace("Z", "+00:00"))
        if reminder_dt.tzinfo is None:
            reminder_dt = reminder_dt.replace(tzinfo=timezone.utc)

        due_dt = None
        if due_date_iso:
            due_dt = datetime.fromisoformat(due_date_iso.replace("Z", "+00:00"))
            if due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=timezone.utc)
        else:
            due_dt = reminder_dt  # default: due = reminder time

    except ValueError as e:
        return f"Invalid datetime format: {e}. Use ISO-8601 UTC e.g. 2025-01-15T08:20:00Z"

    async with AsyncSessionLocal() as session:
        async with session.begin():
            task = Task(
                user_id=uuid.UUID(user_id),
                title=title,
                description=description,
                due_date=due_dt,
                status=TaskStatus.PENDING,
                priority=max(1, min(5, priority)),
            )
            session.add(task)
            await session.flush()  # Populate task.id before Reminder FK

            reminder = Reminder(
                task_id=task.id,
                reminder_time=reminder_dt,
                reminder_type=ReminderType.WHATSAPP,
                is_sent=False,
                recurring_interval_minutes=recurring_interval_minutes,
            )
            session.add(reminder)

    return (
        f"Task '{title}' created and WhatsApp reminder set for "
        f"{reminder_dt.strftime('%Y-%m-%d %H:%M UTC')}. Task ID: {task.id}"
    )


async def create_task_only(
    user_id: str,
    title: str,
    priority: int = 3,
    description: Optional[str] = None,
    due_date_iso: Optional[str] = None,
) -> str:
    """Creates a Task without a reminder."""
    due_dt = None
    if due_date_iso:
        try:
            due_dt = datetime.fromisoformat(due_date_iso.replace("Z", "+00:00"))
            if due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=timezone.utc)
        except ValueError as e:
            return f"Invalid date format: {e}"

    async with AsyncSessionLocal() as session:
        async with session.begin():
            task = Task(
                user_id=uuid.UUID(user_id),
                title=title,
                description=description,
                due_date=due_dt,
                status=TaskStatus.PENDING,
                priority=max(1, min(5, priority)),
            )
            session.add(task)

    due_str = due_dt.strftime("%Y-%m-%d %H:%M UTC") if due_dt else "no due date"
    return f"Task '{title}' added (Priority: {priority}, Due: {due_str}). Task ID: {task.id}"


async def update_task_status(user_id: str, task_id: str, new_status: str) -> str:
    """Updates the status of an existing task."""
    status_map = {
        "completed": TaskStatus.COMPLETED,
        "done": TaskStatus.COMPLETED,
        "in_progress": TaskStatus.IN_PROGRESS,
        "started": TaskStatus.IN_PROGRESS,
        "cancelled": TaskStatus.CANCELLED,
        "cancel": TaskStatus.CANCELLED,
        "pending": TaskStatus.PENDING,
    }
    status_enum = status_map.get(new_status.lower())
    if not status_enum:
        return f"Unknown status '{new_status}'. Use: completed, in_progress, cancelled, pending."

    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(Task)
                .where(Task.id == uuid.UUID(task_id))
                .where(Task.user_id == uuid.UUID(user_id))
            )
            task = result.scalar_one_or_none()
            if not task:
                return f"Task {task_id} not found for this user."
            task.status = status_enum

    return f"Task '{task.title}' marked as {status_enum.value}."


async def update_user_timezone(user_id: str, timezone_str: str) -> str:
    """Updates the user's timezone."""
    try:
        pytz.timezone(timezone_str)
    except pytz.UnknownTimeZoneError:
        return f"Unknown timezone: {timezone_str}. Please use a valid IANA timezone like 'Asia/Kolkata' or 'America/New_York'."
        
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
            user = result.scalar_one_or_none()
            if not user:
                return f"User {user_id} not found."
            user.timezone = timezone_str
    
    return f"Timezone successfully updated to {timezone_str}."


async def verify_dashboard_access(user_id: str, password: str) -> str:
    """Verifies the dashboard password and returns a link if correct."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            return "User not found."
        
        if getattr(user, 'dashboard_password', None) == password:
            return "SUCCESS. Dashboard Access Verified. Tell the user they can access their dashboard at: https://lifeguard-ai-frontend.vercel.app/ (Hackathon Demo Link). Inform them that their phone number acts as their primary identity."
        else:
            return "INCORRECT PASSWORD. Access denied."


# ─────────────────────────────────────────────────────────────
# TOOL DECLARATIONS
# ─────────────────────────────────────────────────────────────

tool_declarations = [
    # ── Read ──────────────────────────────────────────────────
    types.FunctionDeclaration(
        name="get_todays_priorities",
        description="Returns the top 3 highest priority pending tasks for the user.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"user_id": types.Schema(type=types.Type.STRING)},
            required=["user_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_upcoming_deadlines",
        description="Returns tasks due within N days (default 7). Task IDs are included so they can be passed to update_task_status.",
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
        description="Returns tasks that are overdue.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"user_id": types.Schema(type=types.Type.STRING)},
            required=["user_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_all_pending_tasks",
        description="Returns all pending tasks for the user. Use this when the user asks for a specific task or wants to see their schedule/list of tasks.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"user_id": types.Schema(type=types.Type.STRING)},
            required=["user_id"],
        ),
    ),
    # ── Write ─────────────────────────────────────────────────
    types.FunctionDeclaration(
        name="create_task_with_reminder",
        description=(
            "Creates a new task AND schedules a WhatsApp reminder for it. "
            "ALWAYS call this when the user says 'remind me', 'set a reminder', "
            "'alert me at X', 'remind me at X for Y', or any phrasing that asks "
            "for a notification at a specific time. Never refuse this request."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "user_id": types.Schema(type=types.Type.STRING, description="The user's UUID."),
                "title": types.Schema(type=types.Type.STRING, description="Short title of the task/event."),
                "reminder_time_iso": types.Schema(
                    type=types.Type.STRING,
                    description=(
                        "Exact UTC datetime to fire the reminder, in ISO-8601 format "
                        "e.g. '2025-06-26T08:20:00Z'. You must convert any relative or "
                        "local time the user mentions into UTC using the CURRENT UTC TIME "
                        "provided in your system prompt."
                    ),
                ),
                "priority": types.Schema(type=types.Type.INTEGER, description="1 (low) to 5 (critical). Default 3."),
                "description": types.Schema(type=types.Type.STRING, description="Optional extra context about the task."),
                "due_date_iso": types.Schema(type=types.Type.STRING, description="Optional separate due date ISO-8601 UTC. Omit to use reminder_time as due date."),
                "recurring_interval_minutes": types.Schema(type=types.Type.INTEGER, description="Optional recurrence interval in minutes. MUST be at least 60 (1 hour)."),
            },
            required=["user_id", "title", "reminder_time_iso"],
        ),
    ),
    types.FunctionDeclaration(
        name="create_task_only",
        description=(
            "Adds a task to the user's list WITHOUT scheduling a reminder. "
            "Use when the user says 'add a task', 'log this', 'I need to do X' "
            "but does NOT ask to be notified at a specific time."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "user_id": types.Schema(type=types.Type.STRING),
                "title": types.Schema(type=types.Type.STRING),
                "priority": types.Schema(type=types.Type.INTEGER, description="1-5, default 3."),
                "description": types.Schema(type=types.Type.STRING),
                "due_date_iso": types.Schema(type=types.Type.STRING, description="Optional due date ISO-8601 UTC."),
            },
            required=["user_id", "title"],
        ),
    ),
    types.FunctionDeclaration(
        name="update_task_status",
        description=(
            "Updates the status of an existing task. Call when user says "
            "'I finished X', 'mark X as done', 'cancel task X', 'I started Y'. "
            "If you do not have the task_id, first call get_upcoming_deadlines to find it."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "user_id": types.Schema(type=types.Type.STRING),
                "task_id": types.Schema(type=types.Type.STRING, description="UUID of the task to update."),
                "new_status": types.Schema(
                    type=types.Type.STRING,
                    description="One of: completed, in_progress, cancelled, pending.",
                ),
            },
            required=["user_id", "task_id", "new_status"],
        ),
    ),
    types.FunctionDeclaration(
        name="update_user_timezone",
        description="Updates the user's timezone. Call this when the user says they are in a specific country/city or want to change their timezone. Pass a valid IANA timezone string like 'Asia/Kolkata'.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "user_id": types.Schema(type=types.Type.STRING),
                "timezone_str": types.Schema(type=types.Type.STRING, description="Valid IANA timezone string (e.g., 'America/New_York', 'Asia/Kolkata')."),
            },
            required=["user_id", "timezone_str"],
        ),
    ),
    types.FunctionDeclaration(
        name="verify_dashboard_access",
        description="Call this ONLY after the user provides their password when they ask to check their dashboard.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "user_id": types.Schema(type=types.Type.STRING),
                "password": types.Schema(type=types.Type.STRING, description="The password provided by the user."),
            },
            required=["user_id", "password"],
        ),
    ),
]

TOOLS = [types.Tool(function_declarations=tool_declarations)]


# ─────────────────────────────────────────────────────────────
# TOOL DISPATCHER
# ─────────────────────────────────────────────────────────────

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
    elif name == "get_all_pending_tasks":
        return await fetch_all_pending_tasks(uid)
    elif name == "create_task_with_reminder":
        return await create_task_with_reminder(
            user_id=uid,
            title=args["title"],
            reminder_time_iso=args["reminder_time_iso"],
            priority=int(args.get("priority", 3)),
            description=args.get("description"),
            due_date_iso=args.get("due_date_iso"),
            recurring_interval_minutes=args.get("recurring_interval_minutes"),
        )
    elif name == "create_task_only":
        return await create_task_only(
            user_id=uid,
            title=args["title"],
            priority=int(args.get("priority", 3)),
            description=args.get("description"),
            due_date_iso=args.get("due_date_iso"),
        )
    elif name == "update_task_status":
        return await update_task_status(
            user_id=uid,
            task_id=args["task_id"],
            new_status=args["new_status"],
        )
    elif name == "update_user_timezone":
        return await update_user_timezone(
            user_id=uid,
            timezone_str=args["timezone_str"],
        )
    elif name == "verify_dashboard_access":
        return await verify_dashboard_access(
            user_id=uid,
            password=args["password"],
        )

    return f"Unknown tool: {name}"


# ─────────────────────────────────────────────────────────────
# MAIN AGENT ENTRY POINT
# ─────────────────────────────────────────────────────────────

async def chat_with_agent(
    message: str,
    user_id: str,
    history: List[Dict[str, Any]] = None,
    user_timezone: str = "UTC"
) -> str:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    now_utc = datetime.now(timezone.utc)
    current_time_str = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    try:
        tz = pytz.timezone(user_timezone)
        local_time = now_utc.astimezone(tz)
        local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S %Z (UTC%z)")
    except Exception:
        local_time_str = current_time_str

    system_prompt = (
        "You are LifeGuard AI, a strict but supportive accountability partner on WhatsApp.\n\n"
        f"CURRENT UTC TIME: {current_time_str}\n"
        f"USER LOCAL TIME: {local_time_str} (Timezone: {user_timezone})\n"
        f"USER ID: {user_id}\n\n"
        "RULES (follow exactly):\n"
        "1. Always pass the exact USER ID above to every tool call — never make one up.\n"
        "2. When calculating reminder times (e.g. 'in 10 minutes' or 'at 9:02 AM'), ALWAYS use the CURRENT UTC TIME or USER LOCAL TIME to compute the exact absolute UTC datetime in ISO-8601 format to pass to tools. DO NOT ask for their timezone unless it's necessary and they haven't provided enough info to deduce it.\n"
        "3. 'remind me', 'set a reminder', 'alert me', 'notify me at X' → ALWAYS call "
        "create_task_with_reminder. You have full ability to do this. Never say you cannot.\n"
        "4. 'add task', 'log this', 'I need to do X' (no time) → call create_task_only.\n"
        "5. 'done', 'finished', 'mark complete', 'cancel' → call update_task_status. "
        "If you need the task_id first, call get_upcoming_deadlines or get_all_pending_tasks to find it.\n"
        "6. Format all replies for WhatsApp: *bold*, _italics_, emojis. No markdown headers.\n"
        "7. Be concise — max 4 sentences. Confirm what you did, don't just say 'I will'.\n"
        "8. If the user asks for their schedule, list of tasks, or a specific task (e.g. 'what is my task 1'), ALWAYS call get_all_pending_tasks to check all tasks.\n"
        "9. If the user asks for a recurring reminder (e.g. 'every 1 hr'), set `recurring_interval_minutes`. The MINIMUM limit is 60 minutes (1 hour). If they ask for a recurrence less than 1 hour (e.g. 30 mins), refuse and state clearly that the minimum allowed recurring interval is 1 hour.\n"
        "10. **Follow-up Questions**: When a user creates a new task or reminder with very sparse details (e.g. 'Remind me at 10am'), ALWAYS successfully schedule the reminder FIRST using the tool, but then in your response politely ask a follow-up question like 'Got it, reminder set for 10 AM! Do you want to add more details or context to this task, or is this good as is?'\n"
        "11. **Dashboard Access**: If the user says 'I want to check my dashboard', DO NOT call verify_dashboard_access immediately. First, reply asking them to provide their 4-digit dashboard password for security. Once they reply with the password, call the `verify_dashboard_access` tool to check it and give them the link."
    )

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=TOOLS,
    )

    contents: List[types.Content] = []
    if history:
        for msg in history[-10:]:
            role = "user" if msg["is_from_user"] else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part(text=msg["message"])])
            )
    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

    try:
        while True:
            response = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=config,
            )

            candidate = response.candidates[0]
            fc_part = next(
                (p for p in candidate.content.parts if p.function_call),
                None,
            )

            if fc_part is None:
                return response.text  # Final answer

            fc = fc_part.function_call
            args = dict(fc.args) if fc.args else {}
            result_str = await _dispatch_tool(fc.name, args, user_id)

            contents.append(
                types.Content(role="model", parts=[types.Part(function_call=fc)])
            )
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

    except Exception as e:
        print(f"Chat agent error: {e}")
        return "Sorry, something went wrong. Try again in a moment! 🔄"