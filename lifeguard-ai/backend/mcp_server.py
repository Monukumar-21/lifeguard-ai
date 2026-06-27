"""
MCP (Model Context Protocol) Server for LifeGuard AI.

This module exposes all database operations as MCP tools, providing a
standardised protocol layer between AI agents and the data layer.

Instead of agents directly importing SQLAlchemy models and running queries,
they call MCP tools through the protocol — enabling interoperability,
auditability, and clean separation of concerns.

Architecture:
  Agent (MCP Client)  -->  MCP Server (this file)  -->  Database
"""

from mcp.server.fastmcp import FastMCP
from datetime import datetime, timezone, timedelta
from sqlalchemy.future import select
from sqlalchemy import func as sa_func
from backend.database import AsyncSessionLocal
from backend.models import (
    Task, Goal, Subscription, Reminder, User, ChatHistory,
    TaskStatus, GoalStatus, SubscriptionStatus, ReminderType,
)
import uuid

# ─────────────────────────────────────────────────────────────
# Initialize MCP Server
# ─────────────────────────────────────────────────────────────

mcp_server = FastMCP(
    "LifeGuard AI MCP Server",
    description="MCP server providing task management, reminders, goals, and user analytics tools for the LifeGuard AI platform.",
)


# ─────────────────────────────────────────────────────────────
# READ TOOLS
# ─────────────────────────────────────────────────────────────

@mcp_server.tool()
async def get_todays_priorities(user_id: str) -> str:
    """Returns the top 3 highest priority pending tasks for a user."""
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


@mcp_server.tool()
async def get_upcoming_deadlines(user_id: str, days: int = 7) -> str:
    """Returns tasks due within N days (default 7). Includes task IDs."""
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


@mcp_server.tool()
async def get_subscriptions(user_id: str) -> str:
    """Returns the user's active subscriptions."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Subscription).where(Subscription.user_id == uuid.UUID(user_id))
        )
        subs = result.scalars().all()
        if not subs:
            return "No active subscriptions."
        return "\n".join([f"- Plan: {s.plan_id} (Status: {s.status.value})" for s in subs])


@mcp_server.tool()
async def get_goal_progress(user_id: str) -> str:
    """Returns the user's goals and their completion status."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Goal).where(Goal.user_id == uuid.UUID(user_id))
        )
        goals = result.scalars().all()
        if not goals:
            return "No active goals."
        return "\n".join([f"- Goal: {g.title} (Status: {g.status.value})" for g in goals])


@mcp_server.tool()
async def get_risk_tasks(user_id: str) -> str:
    """Returns tasks that are overdue."""
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


@mcp_server.tool()
async def get_all_pending_tasks(user_id: str) -> str:
    """Returns all pending tasks for the user with their IDs."""
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


@mcp_server.tool()
async def get_categorized_tasks(user_id: str) -> str:
    """Returns tasks categorized into Overdue, Today, and Upcoming."""
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        today_end = now.replace(hour=23, minute=59, second=59)

        result = await session.execute(
            select(Task)
            .where(Task.user_id == uuid.UUID(user_id))
            .where(Task.status == TaskStatus.PENDING)
            .order_by(Task.due_date.asc().nulls_last())
        )
        tasks = result.scalars().all()

        if not tasks:
            return "No pending tasks."

        overdue, today, upcoming, no_date = [], [], [], []
        for t in tasks:
            if not t.due_date:
                no_date.append(t)
            elif t.due_date < now:
                overdue.append(t)
            elif t.due_date <= today_end:
                today.append(t)
            else:
                upcoming.append(t)

        out = []
        if overdue:
            out.append("🔴 OVERDUE:")
            out.extend([f"  - [{t.id}] {t.title} (Was due: {t.due_date.strftime('%Y-%m-%d')})" for t in overdue])
        if today:
            out.append("🟡 TODAY:")
            out.extend([f"  - [{t.id}] {t.title} (Due: {t.due_date.strftime('%H:%M UTC')})" for t in today])
        if upcoming:
            out.append("🟢 UPCOMING:")
            out.extend([f"  - [{t.id}] {t.title} (Due: {t.due_date.strftime('%Y-%m-%d')})" for t in upcoming])
        if no_date:
            out.append("⚪ NO DUE DATE:")
            out.extend([f"  - [{t.id}] {t.title}" for t in no_date])
            
        return "\n".join(out)


@mcp_server.tool()
async def get_task_by_id(user_id: str, task_id: str) -> str:
    """Retrieves full details of a specific task by its UUID."""
    async with AsyncSessionLocal() as session:
        try:
            tid = uuid.UUID(task_id)
        except ValueError:
            return "Invalid task ID format."
            
        result = await session.execute(
            select(Task)
            .where(Task.id == tid)
            .where(Task.user_id == uuid.UUID(user_id))
        )
        task = result.scalar_one_or_none()
        if not task:
            return f"Task {task_id} not found."
            
        due = task.due_date.strftime('%Y-%m-%d %H:%M UTC') if task.due_date else 'None'
        desc = task.description if task.description else 'None'
        
        return (
            f"Title: {task.title}\n"
            f"ID: {task.id}\n"
            f"Status: {task.status.value}\n"
            f"Priority: {task.priority}\n"
            f"Due Date: {due}\n"
            f"Description: {desc}"
        )


@mcp_server.tool()
async def get_productivity_stats(user_id: str) -> str:
    """Returns productivity statistics: total tasks, completed, pending, overdue, completion rate, weekly progress."""
    async with AsyncSessionLocal() as session:
        uid = uuid.UUID(user_id)
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)

        total_res = await session.execute(
            select(sa_func.count(Task.id)).where(Task.user_id == uid)
        )
        total = total_res.scalar() or 0

        completed_res = await session.execute(
            select(sa_func.count(Task.id)).where(
                Task.user_id == uid, Task.status == TaskStatus.COMPLETED
            )
        )
        completed = completed_res.scalar() or 0

        pending_res = await session.execute(
            select(sa_func.count(Task.id)).where(
                Task.user_id == uid, Task.status == TaskStatus.PENDING
            )
        )
        pending = pending_res.scalar() or 0

        overdue_res = await session.execute(
            select(sa_func.count(Task.id)).where(
                Task.user_id == uid,
                Task.status == TaskStatus.PENDING,
                Task.due_date.isnot(None),
                Task.due_date < now,
            )
        )
        overdue = overdue_res.scalar() or 0

        week_res = await session.execute(
            select(sa_func.count(Task.id)).where(
                Task.user_id == uid,
                Task.status == TaskStatus.COMPLETED,
                Task.updated_at >= week_ago,
            )
        )
        completed_this_week = week_res.scalar() or 0

        rate = round((completed / total) * 100, 1) if total > 0 else 0

        return (
            f"Total tasks: {total}\n"
            f"Completed: {completed}\n"
            f"Pending: {pending}\n"
            f"Overdue: {overdue}\n"
            f"Completion rate: {rate}%\n"
            f"Completed this week: {completed_this_week}"
        )


# ─────────────────────────────────────────────────────────────
# WRITE TOOLS
# ─────────────────────────────────────────────────────────────

@mcp_server.tool()
async def create_task_with_reminder(
    user_id: str,
    title: str,
    reminder_time_iso: str,
    priority: int = 3,
    description: str = "",
    due_date_iso: str = "",
    recurring_interval_minutes: int = 0,
) -> str:
    """Creates a Task and an attached WhatsApp Reminder. reminder_time_iso and due_date_iso must be UTC ISO-8601 strings."""
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
            due_dt = reminder_dt

    except ValueError as e:
        return f"Invalid datetime format: {e}. Use ISO-8601 UTC e.g. 2025-01-15T08:20:00Z"

    recur = recurring_interval_minutes if recurring_interval_minutes and recurring_interval_minutes > 0 else None

    async with AsyncSessionLocal() as session:
        async with session.begin():
            task = Task(
                user_id=uuid.UUID(user_id),
                title=title,
                description=description or None,
                due_date=due_dt,
                status=TaskStatus.PENDING,
                priority=max(1, min(5, priority)),
            )
            session.add(task)
            await session.flush()

            reminder = Reminder(
                task_id=task.id,
                reminder_time=reminder_dt,
                reminder_type=ReminderType.WHATSAPP,
                is_sent=False,
                recurring_interval_minutes=recur,
            )
            session.add(reminder)

    return (
        f"Task '{title}' created and WhatsApp reminder set for "
        f"{reminder_dt.strftime('%Y-%m-%d %H:%M UTC')}. Task ID: {task.id}"
    )


@mcp_server.tool()
async def create_task_only(
    user_id: str,
    title: str,
    priority: int = 3,
    description: str = "",
    due_date_iso: str = "",
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
                description=description or None,
                due_date=due_dt,
                status=TaskStatus.PENDING,
                priority=max(1, min(5, priority)),
            )
            session.add(task)

    due_str = due_dt.strftime("%Y-%m-%d %H:%M UTC") if due_dt else "no due date"
    return f"Task '{title}' added (Priority: {priority}, Due: {due_str}). Task ID: {task.id}"


@mcp_server.tool()
async def update_task_status(user_id: str, task_id: str, new_status: str) -> str:
    """Updates the status of an existing task (completed, in_progress, cancelled, pending)."""
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


@mcp_server.tool()
async def delete_task(user_id: str, task_id: str) -> str:
    """Permanently deletes a task and all its reminders."""
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
            title = task.title
            await session.delete(task)

    return f"Task '{title}' and all its reminders have been permanently deleted."


@mcp_server.tool()
async def update_user_timezone(user_id: str, timezone_str: str) -> str:
    """Updates the user's IANA timezone (e.g. 'Asia/Kolkata')."""
    import pytz
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


@mcp_server.tool()
async def verify_dashboard_access(user_id: str, password: str) -> str:
    """Verifies the user's dashboard PIN and returns a link if correct."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            return "User not found."

        if getattr(user, 'dashboard_password', None) == password:
            return "SUCCESS. Dashboard Access Verified. Tell the user they can access their dashboard at: https://lifeguard-ai-frontend.vercel.app/ (Hackathon Demo Link). Inform them that their phone number acts as their primary identity."
        else:
            return "INCORRECT PASSWORD. Access denied."
