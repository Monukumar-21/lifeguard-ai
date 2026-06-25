from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.future import select
from datetime import datetime, timezone, timedelta
from backend.database import AsyncSessionLocal
from backend.models import Reminder, Task, User, ReminderType
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
                
                # Mark as sent
                reminder.is_sent = True
                
        if reminders:
            await session.commit()

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
    scheduler.add_job(process_reminders, CronTrigger(minute="*")) # Runs every minute
    scheduler.start()
    print("Scheduler started!")

def stop_scheduler():
    scheduler.shutdown()
    print("Scheduler stopped!")
