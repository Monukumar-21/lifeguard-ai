import os
import google.generativeai as genai
from pydantic import BaseModel, Field

class PrioritySchema(BaseModel):
    priority_score: int = Field(description="Score from 1-100 indicating absolute priority")
    reasoning: str = Field(description="Short explanation of why this priority was chosen")

def assess_priority(task_title: str, task_context: str, due_date: str = None) -> dict:
    """
    Uses AI to evaluate the true priority of a task relative to a user's context.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""
    You are the Priority Engine for LifeGuard AI. Evaluate the priority of the following task from 1 to 100.
    100 = Critical, immediate action required (e.g., life, health, major financial loss).
    1 = Trivial, can wait indefinitely.
    
    TASK: {task_title}
    CONTEXT: {task_context}
    DUE DATE: {due_date if due_date else 'None specified'}
    
    Return a priority_score and brief reasoning.
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=PrioritySchema,
                temperature=0.1,
            )
        )
        import json
        return json.loads(response.text)
    except Exception as e:
        print(f"Error in priority engine: {e}")
        return {"priority_score": 50, "reasoning": "Fallback due to AI error"}
