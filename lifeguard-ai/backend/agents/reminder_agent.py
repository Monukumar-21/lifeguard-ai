import os
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from backend.models import Task, User

class ReminderMessage(BaseModel):
    message_text: str = Field(description="The exact text to send to the user via WhatsApp.")

def generate_smart_reminder(task: Task, user: User) -> str:
    """
    Generates a personalized, context-aware WhatsApp reminder message using AI.
    It mentions the task name, time remaining, and a suggested next action.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    
    # Initialize the new Google GenAI client
    client = genai.Client(api_key=api_key)
    
    now = datetime.now(timezone.utc)
    time_remaining_str = "No due date specified"
    if task.due_date:
        delta = task.due_date - now
        days, seconds = delta.days, delta.seconds
        hours = seconds // 3600
        if days > 0:
            time_remaining_str = f"{days} days and {hours} hours left"
        elif hours > 0:
            time_remaining_str = f"{hours} hours left"
        else:
            time_remaining_str = "Due very soon (less than an hour)"
            
    user_name = user.name if user.name else 'there'
    
    prompt = f"""
    You are an AI accountability partner named LifeGuard AI. 
    Write a short, highly personalized, impactful WhatsApp reminder for the user.
    
    USER: {user_name}
    TASK: {task.title}
    DESCRIPTION/CONTEXT: {task.description or 'No extra details provided'}
    TIME REMAINING: {time_remaining_str}
    PRIORITY LEVEL: {task.priority} (1-5, where 5 is highest)
    
    REQUIREMENTS:
    1. Must mention the task name.
    2. Must mention the exact time remaining.
    3. Must suggest ONE very specific, immediate next action they can take right now to get started.
    4. Never be generic or robotic; speak like a strict but supportive human coach. Use WhatsApp formatting (*bold*, _italics_) and appropriate emojis.
    5. Keep it under 3-4 short sentences.
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReminderMessage,
                temperature=0.7,
            )
        )
        return json.loads(response.text).get("message_text", f"Reminder: *{task.title}* is due soon.")
    except Exception as e:
        print(f"Error generating reminder: {e}")
        return f"Hey {user_name}, you have '{task.title}' coming up. Time remaining: {time_remaining_str}. What's your first step?"