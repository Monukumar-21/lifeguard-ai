from fastapi import APIRouter, Request, BackgroundTasks, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.database import get_db, AsyncSessionLocal
from backend.models import User, Task, ChatHistory, TaskStatus
import httpx
import os
import uuid
from datetime import datetime

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

async def send_whatsapp_message(to_number: str, text: str):
    """
    Sends a text message using Meta's Cloud API for WhatsApp.
    """
    token = os.getenv("WHATSAPP_API_TOKEN")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    
    if not token or not phone_number_id:
        print(f"[WHATSAPP MOCK] To {to_number}: {text}")
        return
        
    url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text}
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            print(f"Message sent to {to_number}")
        except Exception as e:
            print(f"Failed to send WhatsApp message: {e}")

@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    Verify the webhook setup with Meta.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    # Get the verify token from environment variables (no fallback!)
    VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
    
    # Check both mode and token validity
    if mode == "subscribe" and token == VERIFY_TOKEN:
        # Send back the challenge as a plain text response immediately
        return PlainTextResponse(content=challenge)
    
    # If invalid, return a 403 Forbidden (not a 200 JSON)
    raise HTTPException(status_code=403, detail="Invalid verification token")

@router.post("/webhook")
async def handle_whatsapp_message(request: Request, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Receive incoming messages and process them asynchronously.
    """
    body = await request.json()
    
    try:
        if 'entry' not in body:
            return {"status": "ok"}
            
        entry = body['entry'][0]
        changes = entry.get('changes', [])
        if not changes:
            return {"status": "ok"}
            
        value = changes[0].get('value', {})
        
        if 'messages' in value:
            msg = value['messages'][0]
            from_number = msg.get('from')
            
            # For simplicity, we only handle standard text messages
            if msg.get('type') != 'text':
                return {"status": "ok"}
                
            text_body = msg['text']['body']
            
            # Find user by whatsapp number
            result = await db.execute(select(User).where(User.whatsapp_number == from_number))
            user = result.scalar_one_or_none()
            
            if user:
                # Log chat history
                chat = ChatHistory(user_id=user.id, message=text_body, is_from_user=True, platform="WHATSAPP")
                db.add(chat)
                await db.commit()
                
                # Extract commitments asynchronously
                background_tasks.add_task(process_message, text_body, user.id, from_number)
            else:
                # If user doesn't exist in DB, optionally create them here or reply asking to sign up on web
                new_user = User(clerk_id=str(uuid.uuid4()), whatsapp_number=from_number, name="Unknown User")
                db.add(new_user)
                await db.commit()
                await db.refresh(new_user)
                
                chat = ChatHistory(user_id=new_user.id, message=text_body, is_from_user=True, platform="WHATSAPP")
                db.add(chat)
                await db.commit()
                
                background_tasks.add_task(process_message, text_body, new_user.id, from_number)
                
    except Exception as e:
        print(f"Error handling webhook: {e}")

    return {"status": "ok"}

async def process_message(text: str, user_id: uuid.UUID, phone_number: str):
    """
    Background task to analyze the message, create a task if applicable, 
    and reply to the user.
    """
    # FIX: Move heavy imports HERE so they don't block the webhook startup
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
                    # Convert ISO format like 2026-06-25T17:00:00Z safely
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
            
            # Now we can schedule reminders
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
            
            # Send message via WhatsApp API
            await send_whatsapp_message(phone_number, response_text)
        else:
            # Handle general chat fallback
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            user_name = user.name if user and user.name else "there"
            
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
            
            # Send message via WhatsApp API
            await send_whatsapp_message(phone_number, response_text)