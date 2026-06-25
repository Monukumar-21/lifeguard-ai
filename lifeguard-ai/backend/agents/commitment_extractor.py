import os
import json
from datetime import datetime, timezone
import google.generativeai as genai
from pydantic import BaseModel, Field
from typing import Optional, Any

# Ensure you have google-generativeai and pydantic installed in requirements.txt
# pip install google-generativeai pydantic

class CommitmentSchema(BaseModel):
    task_title: str = Field(description="A clear, concise title of the task or commitment.")
    category: str = Field(description="Category of the task (e.g., Work, Health, Personal, Finance).")
    due_date: Optional[str] = Field(description="Absolute UTC ISO-8601 formatted date and time if mentioned, otherwise null.")
    priority: int = Field(description="Integer from 1 (low) to 5 (high) indicating priority based on urgency.")
    is_financial: bool = Field(description="True if the task involves money, payments, or financial transactions.")
    amount: Optional[float] = Field(description="Financial amount if mentioned, otherwise null.")

def extract_commitment(message: str) -> dict[str, Any]:
    """
    Analyzes a raw WhatsApp message to extract structured task/commitment data.
    """
    # Configure the SDK. Ensure GEMINI_API_KEY is in your environment variables.
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    # Get current UTC time to resolve relative dates
    current_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    prompt = f"""
    You are the core intelligence of "LifeGuard AI", an AI accountability system.
    Your job is to extract structured commitment data from a raw WhatsApp message.
    
    CURRENT SYSTEM TIME (UTC): {current_utc}
    Use this time to convert relative dates (e.g., "Friday", "tomorrow", "next week", "in 2 hours") into an absolute UTC ISO-8601 format string.
    
    RULES:
    1. Identify the core task or commitment the user is making.
    2. Determine a category (e.g., Work, Health, Personal, Finance, Fitness).
    3. If a due date or time is implied, convert it to an absolute ISO-8601 UTC string. If NO date/time is mentioned or implied, return null for due_date.
    4. Estimate a priority from 1 (low) to 5 (critical) based on the language used.
    5. If the message involves money, purchasing, payments, or costs, set is_financial to true.
    6. If a specific financial amount is mentioned (e.g., "$50", "20 bucks"), extract it as a float. Otherwise, return null.
    7. If the message is completely vague (e.g., "hey", "I'm tired"), try to extract any latent goal or return a default placeholder task like "Check in" with low priority.

    USER MESSAGE:
    "{message}"
    """
    
    try:
        # Using structured outputs feature of Gemini 2.5 Flash
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=CommitmentSchema,
                temperature=0.1,
            )
        )
        
        # Parse the JSON response
        return json.loads(response.text)
        
    except Exception as e:
        print(f"Error extracting commitment: {e}")
        # Fallback dictionary matching the schema
        return {
            "task_title": "Unidentified Task",
            "category": "Unknown",
            "due_date": None,
            "priority": 1,
            "is_financial": False,
            "amount": None
        }

# Example usage (for testing manually):
if __name__ == "__main__":
    test_msg = "I need to pay my rent of $1200 by this Friday at 5 PM."
    print("Testing extraction...")
    result = extract_commitment(test_msg)
    print(json.dumps(result, indent=2))
