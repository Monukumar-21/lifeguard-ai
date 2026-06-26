from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.database import get_db, AsyncSessionLocal
from backend.models import User, Task, ChatHistory, TaskStatus
from twilio.rest import Client
import os
import uuid
from datetime import datetime

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

async def send_whatsapp_message(to_number: str, text: str):
    """
    Sends a WhatsApp text message using Twilio's REST API Client.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_WHATSAPP_FROM")  # Example: 'whatsapp:+14155238886'
    
    if not account_sid or not auth_token or not from_number:
        print(f"[TWILIO MOCK] To {to_number}: {text}")
        return
        
    try:
        # Twilio expects recipient numbers to include the 'whatsapp:' identifier
        to_formatted = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"
        
        # Initialize Twilio Client
        client = Client(account_sid, auth_token)
        
        # Send message out-of-band (runs perfectly inside BackgroundTasks)
        message = client.messages.create(
            from_=from_number,
            body=text,
            to=to_formatted
        )
        print(f"Message successfully sent via Twilio to {to_formatted}, SID: {message.sid}")
    except Exception as e:
        print(f"Failed to send Twilio WhatsApp message: {e}")

@router.post("/webhook")
async def handle_whatsapp_message(
    background_tasks: BackgroundTasks, 
    From: str = Form(...),   # Twilio passes user's number here (e.g., 'whatsapp:+919876543210')
    Body: str = Form(...),   # Twilio passes message contents here
    db: AsyncSession = Depends(get_db)
):
    """
    Receive incoming WhatsApp messages from Twilio via Form data and process asynchronously.
    """
    try:
        # 1. Clean the incoming number to match your database's format (e.g., '919876543210')
        cleaned_number = From.replace("whatsapp:", "").replace("+", "")
        text_body = Body
        
        # 2. Look up user by their cleaned phone number digits
        result = await db.execute(select(User).where(User.whatsapp_number == cleaned_number))
        user = result.scalar_one_or_none()
        
        if user:
            # Log raw incoming text to history
            chat = ChatHistory(user_id=user.id, message=text_body, is_from_user=True, platform="WHATSAPP")
            db.add(chat)
            await db.commit()
            
            # Pass the complete Twilio format 'From' variable forward to ensure replies hit properly
            background_tasks.add_task(process_message, text_body, user.id, From)
        else:
            # Create a fallback profile if user doesn't exist yet
            new_user = User(clerk_id=str(uuid.uuid4()), whatsapp_number=cleaned_number, name="Unknown User")
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            
            chat = ChatHistory(user_id=new_user.id, message=text_body, is_from_user=True, platform="WHATSAPP")
            db.add(chat)
            await db.commit()
            
            background_tasks.add_task(process_message, text_body, new_user.id, From)
                
    except Exception as e:
        print(f"Error handling Twilio webhook incoming payload: {e}")

    # Twilio requires a fast 200 HTTP response to acknowledge receipt
    return {"status": "ok"}

async def process_message(text: str, user_id: uuid.UUID, phone_number: str):
    """
    Background task to analyze the message, create a task if applicable, 
    and reply to the user.
    """
    from backend.agents.commitment_extractor import extract_commitment
    from backend.agents.chat_agent import chat_with_agent
    
    # Process text using the commitment extractor AI
    commitment_data = extract_commitment(text)
    
    async with AsyncSessionLocal() as session:
        title = commitment_data.get("task_title", "")
        
        # Determine if it's a valid task rather than general chat
        is_valid_task = title and title not in ["Unidentified Task", "Unparseable Task", "Check in"]
        
        if is_valid_task:
            due_date_str = commitment_data.get("due_date")
            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                except ValueError:
                    pass
            
            new_task = Task(
                user_id=user_id,
                title=title,
                priority=commitment_data.get("priority", 1),
                due_date=due_date,
                status=TaskStatus.PENDING
            )
            session.add(new_task)
            await session.commit()
            await session.refresh(new_task)
            
            if due_date:
                from backend.scheduler.reminder_scheduler import schedule_reminders_for_task
                await schedule_reminders_for_task(new_task.id)
            
            date_info = f"\n📅 *Due:* {due_date.strftime('%b %d, %Y at %H:%M %Z')}" if due_date else ""
            category_info = f"\n🏷️ *Category:* {commitment_data.get('category', 'General')}"
            priority_info = f"\n⚡ *Priority:* {new_task.priority}/5"
            
            response_text = (
                f"✅ *Commitment Locked In*\n"
                f"I've added: *{new_task.title}*{category_info}{date_info}{priority_info}\n\n"
                f"I'll hold you to this! 💪 What's the very first step you need to take?"
            )
            
            bot_chat = ChatHistory(user_id=user_id, message=response_text, is_from_user=False, platform="WHATSAPP")
            session.add(bot_chat)
            await session.commit()
            
            # Send message via Twilio API
            await send_whatsapp_message(phone_number, response_text)
        else:
            # Handle general chat fallback
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            # Fetch recent chat history
            history_result = await session.execute(
                select(ChatHistory)
                .where(ChatHistory.user_id == user_id)
                .order_by(ChatHistory.created_at.desc())
                .limit(10)
            )
            chat_logs = history_result.scalars().all()
            history = [{"is_from_user": c.is_from_user, "message": c.message} for c in reversed(chat_logs)]
            
            response_text = await chat_with_agent(text, str(user_id), history)
            bot_chat = ChatHistory(user_id=user_id, message=response_text, is_from_user=False, platform="WHATSAPP")
            session.add(bot_chat)
            await session.commit()
            
            # Send message via Twilio API
            await send_whatsapp_message(phone_number, response_text)