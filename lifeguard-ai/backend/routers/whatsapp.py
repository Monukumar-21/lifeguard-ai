from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.database import get_db, AsyncSessionLocal
from backend.models import User, ChatHistory
from twilio.rest import Client
import os
import uuid

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


async def send_whatsapp_message(to_number: str, text: str):
    """
    Sends a WhatsApp message via Twilio.
    Accepts any number format — raw digits, with +, or already prefixed.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token  = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_WHATSAPP_FROM")  # e.g. 'whatsapp:+14155238886'

    if not account_sid or not auth_token or not from_number:
        print(f"[TWILIO MOCK] To {to_number}: {text}")
        return

    try:
        # Normalise to whatsapp:+<digits>
        # Strip any existing prefix/plus so we start clean
        digits = (
            to_number
            .replace("whatsapp:", "")
            .replace("+", "")
            .strip()
        )
        to_formatted = f"whatsapp:+{digits}"   # BUG FIX: was missing the '+'

        client = Client(account_sid, auth_token)
        message = client.messages.create(
            from_=from_number,
            body=text,
            to=to_formatted,
        )
        print(f"Message successfully sent via Twilio to {to_formatted}, SID: {message.sid}")
    except Exception as e:
        print(f"Failed to send Twilio WhatsApp message: {e}")


@router.post("/webhook")
async def handle_whatsapp_message(
    background_tasks: BackgroundTasks,
    From: str = Form(...),   # e.g. 'whatsapp:+916205138154'
    Body: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Receives incoming WhatsApp messages from Twilio and queues processing.
    """
    try:
        # Store digits-only so format is consistent with what we stored at signup
        cleaned_number = From.replace("whatsapp:", "").replace("+", "")
        text_body = Body

        result = await db.execute(
            select(User).where(User.whatsapp_number == cleaned_number)
        )
        user = result.scalar_one_or_none()

        if not user:
            # Auto-create a minimal profile on first contact
            user = User(
                clerk_id=str(uuid.uuid4()),
                whatsapp_number=cleaned_number,
                name="Unknown User",
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        # Log the incoming message
        db.add(ChatHistory(
            user_id=user.id,
            message=text_body,
            is_from_user=True,
            platform="WHATSAPP",
        ))
        await db.commit()

        # Process in background so Twilio gets its 200 immediately
        background_tasks.add_task(process_message, text_body, user.id, From, user.timezone)

    except Exception as e:
        print(f"Error in WhatsApp webhook: {e}")

    return {"status": "ok"}


async def process_message(text: str, user_id: uuid.UUID, phone_number: str, user_timezone: str = "UTC"):
    """
    Background task: runs the chat agent and replies to the user.

    FIX: previously this called commitment_extractor first and only fell
    through to chat_with_agent for 'non-task' messages.  That meant any
    message detected as a task (including 'set a reminder at 8:30 AM')
    bypassed the agent entirely — so the agent's write tools (create_task_with_reminder,
    etc.) were never called and the user's requested reminder time was ignored.

    Now every message goes straight to chat_with_agent, which uses its tools
    to decide whether to create a task, set a reminder, answer a question, etc.
    """
    from backend.agents.chat_agent import chat_with_agent

    async with AsyncSessionLocal() as session:
        # Fetch recent history so the agent has conversational context
        history_result = await session.execute(
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.created_at.desc())
            .limit(10)
        )
        chat_logs = history_result.scalars().all()
        history = [
            {"is_from_user": c.is_from_user, "message": c.message}
            for c in reversed(chat_logs)
        ]

        # Let the agent decide what to do (chat, create task, set reminder, etc.)
        response_text = await chat_with_agent(text, str(user_id), history, user_timezone)

        # Persist the bot reply
        session.add(ChatHistory(
            user_id=user_id,
            message=response_text,
            is_from_user=False,
            platform="WHATSAPP",
        ))
        await session.commit()

    # Send reply via Twilio
    await send_whatsapp_message(phone_number, response_text)