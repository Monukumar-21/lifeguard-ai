from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.future import select
from sqlalchemy import func as sa_func
from datetime import datetime, timezone, timedelta
from backend.database import AsyncSessionLocal
from backend.models import Reminder, Task, User, ReminderType, TaskStatus
from backend.agents.reminder_agent import generate_smart_reminder
from backend.routers.whatsapp import send_whatsapp_message
import uuid

async def process_reminders():
    """
    Checks for due reminders and sends them out.
    """
    now = datetime.now(timezone.utc)
    
    async with AsyncSessionLocal() as session:
        # Find reminders that are due and not sent
        result = await session.execute(
            select(Reminder, Task, User)
            .join(Task, Reminder.task_id == Task.id)
            .join(User, Task.user_id == User.id)
            .where(Reminder.is_sent == False)
            .where(Reminder.reminder_time <= now)
        )
        reminders = result.all()
        
        for reminder, task, user in reminders:
            if user.whatsapp_number:
                # Generate a smart reminder message
                msg = generate_smart_reminder(task, user)
                
                await send_whatsapp_message(user.whatsapp_number, msg)
                
                # Mark as sent or schedule next recurrence
                if getattr(reminder, 'recurring_interval_minutes', None):
                    # Advance until it is in the future
                    while reminder.reminder_time <= now:
                        reminder.reminder_time += timedelta(minutes=reminder.recurring_interval_minutes)
                else:
                    reminder.is_sent = True
                
        if reminders:
            await session.commit()


async def daily_morning_briefing():
    """
    Sends a proactive morning summary to every user at 8 AM UTC.
    Includes today's pending tasks, overdue count, and a motivational nudge.
    """
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        users_result = await session.execute(
            select(User).where(User.whatsapp_number.isnot(None))
        )
        users = users_result.scalars().all()

        for user in users:
            try:
                # Pending tasks
                pending_res = await session.execute(
                    select(Task)
                    .where(Task.user_id == user.id)
                    .where(Task.status == TaskStatus.PENDING)
                    .order_by(Task.priority.desc())
                    .limit(5)
                )
                pending_tasks = pending_res.scalars().all()

                # Overdue count
                overdue_res = await session.execute(
                    select(sa_func.count(Task.id)).where(
                        Task.user_id == user.id,
                        Task.status == TaskStatus.PENDING,
                        Task.due_date.isnot(None),
                        Task.due_date < now,
                    )
                )
                overdue_count = overdue_res.scalar() or 0

                user_name = user.name if user.name and user.name != "Unknown User" else "there"

                if not pending_tasks and overdue_count == 0:
                    continue  # Nothing to report

                lines = [f"\U0001f305 *Good Morning, {user_name}!*\n"]

                if overdue_count > 0:
                    lines.append(f"\u26a0\ufe0f You have *{overdue_count} overdue* task(s). Let's tackle those first!\n")

                if pending_tasks:
                    lines.append("\U0001f4cb *Today's Focus:*")
                    for i, t in enumerate(pending_tasks, 1):
                        priority_emoji = "\U0001f534" if t.priority >= 4 else "\U0001f7e1" if t.priority >= 3 else "\U0001f7e2"
                        lines.append(f"  {priority_emoji} {i}. {t.title}")

                lines.append("\n\U0001f4aa _Reply to me anytime to manage your tasks. You got this!_")

                msg = "\n".join(lines)
                await send_whatsapp_message(user.whatsapp_number, msg)
            except Exception as e:
                print(f"Error sending morning briefing to {user.id}: {e}")


async def nudge_overdue_tasks():
    """
    Sends a nudge for tasks that are overdue. Runs every 6 hours.
    Only nudges for tasks overdue by more than 1 hour to avoid spam right at deadline.
    """
    now = datetime.now(timezone.utc)
    overdue_threshold = now - timedelta(hours=1)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Task, User)
            .join(User, Task.user_id == User.id)
            .where(Task.status == TaskStatus.PENDING)
            .where(Task.due_date.isnot(None))
            .where(Task.due_date < overdue_threshold)
            .limit(50)
        )
        overdue_items = result.all()

        # Group by user
        user_tasks: dict = {}
        for task, user in overdue_items:
            if user.whatsapp_number:
                user_tasks.setdefault(user.whatsapp_number, {"name": user.name or "there", "tasks": []})
                user_tasks[user.whatsapp_number]["tasks"].append(task.title)

        for phone, data in user_tasks.items():
            count = len(data["tasks"])
            task_list = "\n".join([f"  \u2022 {t}" for t in data["tasks"][:5]])
            msg = (
                f"\u23f0 *Overdue Alert, {data['name']}!*\n\n"
                f"You have *{count}* overdue task(s):\n{task_list}\n\n"
                f"_Reply 'done [task name]' to mark complete, or 'delete [task name]' to remove._"
            )
            await send_whatsapp_message(phone, msg)


async def schedule_reminders_for_task(task_id: uuid.UUID):
    """
    Schedules reminders for a task at 7 days, 3 days, 1 day, and morning of.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task or not task.due_date:
            return
            
        due_date = task.due_date
        now = datetime.now(timezone.utc)
        
        # Determine schedule times
        schedule_times = []
        
        # 7 days before
        t_7d = due_date - timedelta(days=7)
        if t_7d > now: schedule_times.append(t_7d)
        
        # 3 days before
        t_3d = due_date - timedelta(days=3)
        if t_3d > now: schedule_times.append(t_3d)
        
        # 1 day before
        t_1d = due_date - timedelta(days=1)
        if t_1d > now: schedule_times.append(t_1d)
        
        # Morning of (8:00 AM on due date)
        t_morning = due_date.replace(hour=8, minute=0, second=0, microsecond=0)
        if t_morning > now and t_morning < due_date: 
            schedule_times.append(t_morning)
            
        # Add to database
        for st in schedule_times:
            reminder = Reminder(
                task_id=task.id,
                reminder_time=st,
                reminder_type=ReminderType.WHATSAPP
            )
            session.add(reminder)
            
        if schedule_times:
            await session.commit()
            print(f"Scheduled {len(schedule_times)} reminders for task {task_id}")

# Setup Scheduler
scheduler = AsyncIOScheduler()

def start_scheduler():
    # Core reminder checker — every 10 seconds
    scheduler.add_job(process_reminders, IntervalTrigger(seconds=10))
    # Daily morning briefing — 8 AM UTC (1:30 PM IST)
    scheduler.add_job(daily_morning_briefing, CronTrigger(hour=8, minute=0))
    # Overdue nudger — every 6 hours
    scheduler.add_job(nudge_overdue_tasks, IntervalTrigger(hours=6))
    scheduler.start()
    print("Scheduler started! (reminders: 10s, briefing: 8AM UTC, nudges: 6h)")

def stop_scheduler():
    scheduler.shutdown()
    print("Scheduler stopped!")
