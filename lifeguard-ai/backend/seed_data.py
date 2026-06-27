"""
Seed script that populates the database with realistic demo data.
Called from main.py lifespan when RESET_DB=true.
"""
import uuid
from datetime import datetime, timezone, timedelta
from backend.models import (
    User, Task, Goal, Subscription, Reminder, ChatHistory,
    TaskStatus, GoalStatus, SubscriptionStatus, ReminderType,
)


# A fixed demo user UUID so the frontend MOCK_USER_ID can match
DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


async def seed_demo_data(session):
    """Insert realistic demo data for the hackathon judges."""

    # ── Demo User ────────────────────────────────────────────
    user = User(
        id=DEMO_USER_ID,
        clerk_id="demo-clerk-id",
        whatsapp_number="916205138154",  # replace w/ your own for live demo
        email="demo@lifeguard.ai",
        name="Alex",
        timezone="Asia/Kolkata",
        dashboard_password="1234",
    )
    session.add(user)
    await session.flush()

    now = datetime.now(timezone.utc)

    # ── Tasks ────────────────────────────────────────────────
    tasks_data = [
        # Pending — high priority
        {"title": "Finalize Hackathon Pitch Deck", "desc": "Polish slides, add demo video link, rehearse 3-min pitch", "priority": 5, "status": TaskStatus.PENDING,
         "due": now + timedelta(hours=6)},
        {"title": "Review Q3 Marketing Budget", "desc": "Check ad spend allocation across channels", "priority": 4, "status": TaskStatus.PENDING,
         "due": now + timedelta(days=1)},
        {"title": "Prepare DSA Mock Interview", "desc": "Practice 3 medium LC problems: graphs, DP, sliding window", "priority": 4, "status": TaskStatus.PENDING,
         "due": now + timedelta(days=2)},
        # Pending — medium
        {"title": "Read Chapter 5 — System Design", "desc": "Designing Data-Intensive Applications", "priority": 3, "status": TaskStatus.PENDING,
         "due": now + timedelta(days=3)},
        {"title": "Grocery Shopping", "desc": "Milk, eggs, bread, fruits", "priority": 2, "status": TaskStatus.PENDING,
         "due": now + timedelta(days=1, hours=4)},
        # Completed
        {"title": "Submit College Assignment", "desc": "ML lab report — due Monday", "priority": 3, "status": TaskStatus.COMPLETED,
         "due": now - timedelta(days=1)},
        {"title": "Morning Jog — 5 km", "desc": None, "priority": 2, "status": TaskStatus.COMPLETED,
         "due": now - timedelta(hours=10)},
        {"title": "Call Mom", "desc": "Weekly check-in call", "priority": 3, "status": TaskStatus.COMPLETED,
         "due": now - timedelta(days=2)},
        # Overdue (for nudge demo)
        {"title": "Renew Library Books", "desc": "3 books checked out last month", "priority": 2, "status": TaskStatus.PENDING,
         "due": now - timedelta(days=1, hours=5)},
    ]

    task_objects = []
    for td in tasks_data:
        t = Task(
            user_id=DEMO_USER_ID,
            title=td["title"],
            description=td["desc"],
            priority=td["priority"],
            status=td["status"],
            due_date=td["due"],
        )
        session.add(t)
        task_objects.append(t)

    await session.flush()

    # ── Reminders for pending tasks ──────────────────────────
    for t in task_objects:
        if t.status == TaskStatus.PENDING and t.due_date and t.due_date > now:
            r = Reminder(
                task_id=t.id,
                reminder_time=t.due_date - timedelta(minutes=30),
                reminder_type=ReminderType.WHATSAPP,
                is_sent=False,
            )
            session.add(r)

    # Add one recurring reminder for demo
    recurring_reminder = Reminder(
        task_id=task_objects[0].id,  # Pitch deck
        reminder_time=now + timedelta(hours=1),
        reminder_type=ReminderType.WHATSAPP,
        is_sent=False,
        recurring_interval_minutes=60,
    )
    session.add(recurring_reminder)

    # ── Goals ────────────────────────────────────────────────
    goals_data = [
        {"title": "Run 50 km this month", "desc": "Track daily runs, avg 1.6 km/day", "status": GoalStatus.ACTIVE},
        {"title": "Read 3 Books", "desc": "Currently reading: System Design Interview", "status": GoalStatus.ACTIVE},
        {"title": "Complete ML Course", "desc": "Andrew Ng's ML Specialization on Coursera", "status": GoalStatus.ACTIVE},
    ]
    for gd in goals_data:
        g = Goal(
            user_id=DEMO_USER_ID,
            title=gd["title"],
            description=gd["desc"],
            status=gd["status"],
        )
        session.add(g)

    # ── Subscription ─────────────────────────────────────────
    sub = Subscription(
        user_id=DEMO_USER_ID,
        plan_id="free",
        status=SubscriptionStatus.ACTIVE,
        current_period_end=now + timedelta(days=30),
    )
    session.add(sub)

    # ── Chat History (recent WhatsApp conversation) ──────────
    chat_data = [
        {"msg": "Hey, remind me to finalize my pitch deck by 5 PM today", "from_user": True, "ago": timedelta(hours=3)},
        {"msg": "\u2705 Done! I've set a reminder for *Finalize Hackathon Pitch Deck* at 5:00 PM IST. Want to add more details?", "from_user": False, "ago": timedelta(hours=3, minutes=-1)},
        {"msg": "What are my tasks for today?", "from_user": True, "ago": timedelta(hours=2)},
        {"msg": "\U0001f4cb *Your Pending Tasks:*\n\n\U0001f534 1. Finalize Hackathon Pitch Deck (Due: Today 5 PM)\n\U0001f7e1 2. Review Q3 Marketing Budget (Due: Tomorrow)\n\U0001f7e2 3. Grocery Shopping (Due: Tomorrow)\n\nStay focused! \U0001f4aa", "from_user": False, "ago": timedelta(hours=2, minutes=-1)},
        {"msg": "Mark submit college assignment as done", "from_user": True, "ago": timedelta(hours=1)},
        {"msg": "\U0001f389 *Submit College Assignment* marked as completed! One less thing to worry about. Keep the momentum going!", "from_user": False, "ago": timedelta(hours=1, minutes=-1)},
    ]
    for cd in chat_data:
        ch = ChatHistory(
            user_id=DEMO_USER_ID,
            message=cd["msg"],
            is_from_user=cd["from_user"],
            platform="WHATSAPP",
        )
        # Override created_at via raw SQL would be complex, just add them in order
        session.add(ch)

    await session.commit()
    print("Demo data seeded successfully!")
