"""
Chat Agent for LifeGuard AI.

This agent uses Gemini function calling for user interaction and delegates
all database operations to the MCP Server via an MCP Client interface.

Architecture:
  User (WhatsApp) --> Chat Agent (this file) --> MCP Client --> MCP Server --> Database
"""

import os
import uuid
from google import genai
from google.genai import types
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import pytz

# ─────────────────────────────────────────────────────────────
# MCP CLIENT — Calls MCP Server tools instead of direct DB access
# ─────────────────────────────────────────────────────────────

class MCPClient:
    """
    In-process MCP Client that calls tools registered on the MCP Server.
    
    In a production multi-service architecture, this would use SSE or stdio
    transport to communicate over the network. For our monolithic deployment
    (Railway), we use direct in-process calls to the FastMCP server instance,
    which still follows the MCP protocol's tool-calling semantics.
    """

    def __init__(self):
        # Lazy import to avoid circular imports at module load time
        self._server = None

    @property
    def server(self):
        if self._server is None:
            from backend.mcp_server import mcp_server
            self._server = mcp_server
        return self._server

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """
        Call an MCP tool by name with the given arguments.
        Returns the tool's string result.
        """
        try:
            result = await self.server.call_tool(tool_name, arguments)
            # Extract text from MCP result
            if hasattr(result, '__iter__'):
                parts = []
                for item in result:
                    if hasattr(item, 'text'):
                        parts.append(item.text)
                    else:
                        parts.append(str(item))
                return "\n".join(parts) if parts else "Done."
            return str(result)
        except Exception as e:
            print(f"MCP tool call error [{tool_name}]: {e}")
            return f"Error calling tool {tool_name}: {e}"

    async def list_tools(self) -> list:
        """List all tools available on the MCP server."""
        try:
            tools = await self.server.list_tools()
            return tools
        except Exception as e:
            print(f"MCP list_tools error: {e}")
            return []


# Singleton MCP client instance
mcp_client = MCPClient()


# ─────────────────────────────────────────────────────────────
# GEMINI TOOL DECLARATIONS (unchanged — Gemini needs these schemas)
# ─────────────────────────────────────────────────────────────

tool_declarations = [
    # ── Read ──────────────────────────────────────────────────
    types.FunctionDeclaration(
        name="get_todays_priorities",
        description="Returns the top 3 highest priority pending tasks for the user.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"user_id": types.Schema(type=types.Type.STRING)},
            required=["user_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_upcoming_deadlines",
        description="Returns tasks due within N days (default 7). Task IDs are included so they can be passed to update_task_status.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "user_id": types.Schema(type=types.Type.STRING),
                "days": types.Schema(type=types.Type.INTEGER, description="Number of days to look ahead. Default 7."),
            },
            required=["user_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_subscriptions",
        description="Returns the user's active subscriptions.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"user_id": types.Schema(type=types.Type.STRING)},
            required=["user_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_goal_progress",
        description="Returns the user's goals and their completion status.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"user_id": types.Schema(type=types.Type.STRING)},
            required=["user_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_risk_tasks",
        description="Returns tasks that are overdue.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"user_id": types.Schema(type=types.Type.STRING)},
            required=["user_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_all_pending_tasks",
        description="Returns all pending tasks for the user. Use this when the user asks for a specific task or wants to see their schedule/list of tasks.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"user_id": types.Schema(type=types.Type.STRING)},
            required=["user_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_categorized_tasks",
        description="Returns tasks categorized into OVERDUE, TODAY, and UPCOMING. Use this when the user asks to see tasks by dues or category.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"user_id": types.Schema(type=types.Type.STRING)},
            required=["user_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_task_by_id",
        description="Retrieves the full details (description, due date, status, priority) of a specific task using its exact UUID. Call this when you already have the task_id and need more info.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "user_id": types.Schema(type=types.Type.STRING),
                "task_id": types.Schema(type=types.Type.STRING, description="The UUID of the task to retrieve."),
            },
            required=["user_id", "task_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_productivity_stats",
        description="Returns the user's productivity statistics including total tasks, completed count, pending count, overdue count, completion rate, and tasks completed this week. Call when user asks 'how am I doing', 'my stats', 'my progress', 'productivity report', or similar.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"user_id": types.Schema(type=types.Type.STRING)},
            required=["user_id"],
        ),
    ),
    # ── Write ─────────────────────────────────────────────────
    types.FunctionDeclaration(
        name="create_task_with_reminder",
        description=(
            "Creates a new task AND schedules a WhatsApp reminder for it. "
            "ALWAYS call this when the user says 'remind me', 'set a reminder', "
            "'alert me at X', 'remind me at X for Y', or any phrasing that asks "
            "for a notification at a specific time. Never refuse this request."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "user_id": types.Schema(type=types.Type.STRING, description="The user's UUID."),
                "title": types.Schema(type=types.Type.STRING, description="Short title of the task/event."),
                "reminder_time_iso": types.Schema(
                    type=types.Type.STRING,
                    description=(
                        "Exact UTC datetime to fire the reminder, in ISO-8601 format "
                        "e.g. '2025-06-26T08:20:00Z'. You must convert any relative or "
                        "local time the user mentions into UTC using the CURRENT UTC TIME "
                        "provided in your system prompt."
                    ),
                ),
                "priority": types.Schema(type=types.Type.INTEGER, description="1 (low) to 5 (critical). Default 3."),
                "description": types.Schema(type=types.Type.STRING, description="Optional extra context about the task."),
                "due_date_iso": types.Schema(type=types.Type.STRING, description="Optional separate due date ISO-8601 UTC. Omit to use reminder_time as due date."),
                "recurring_interval_minutes": types.Schema(type=types.Type.INTEGER, description="Optional recurrence interval in minutes. MUST be at least 60 (1 hour)."),
            },
            required=["user_id", "title", "reminder_time_iso"],
        ),
    ),
    types.FunctionDeclaration(
        name="create_task_only",
        description=(
            "Adds a task to the user's list WITHOUT scheduling a reminder. "
            "Use when the user says 'add a task', 'log this', 'I need to do X' "
            "but does NOT ask to be notified at a specific time."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "user_id": types.Schema(type=types.Type.STRING),
                "title": types.Schema(type=types.Type.STRING),
                "priority": types.Schema(type=types.Type.INTEGER, description="1-5, default 3."),
                "description": types.Schema(type=types.Type.STRING),
                "due_date_iso": types.Schema(type=types.Type.STRING, description="Optional due date ISO-8601 UTC."),
            },
            required=["user_id", "title"],
        ),
    ),
    types.FunctionDeclaration(
        name="update_task_status",
        description=(
            "Updates the status of an existing task. Call when user says "
            "'done', 'finished', 'mark complete', 'cancel', etc."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "user_id": types.Schema(type=types.Type.STRING),
                "task_id": types.Schema(type=types.Type.STRING, description="UUID of the task to update."),
                "new_status": types.Schema(
                    type=types.Type.STRING,
                    description="One of: completed, in_progress, cancelled, pending.",
                ),
            },
            required=["user_id", "task_id", "new_status"],
        ),
    ),
    types.FunctionDeclaration(
        name="delete_task",
        description="Permanently deletes a task and all its reminders. Call when user says 'delete task', 'remove task', 'cancel and delete'. To find the task_id first, call get_all_pending_tasks.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "user_id": types.Schema(type=types.Type.STRING),
                "task_id": types.Schema(type=types.Type.STRING, description="UUID of the task to delete."),
            },
            required=["user_id", "task_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="update_user_timezone",
        description="Updates the user's timezone. Call this when the user says they are in a specific country/city or want to change their timezone. Pass a valid IANA timezone string like 'Asia/Kolkata'.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "user_id": types.Schema(type=types.Type.STRING),
                "timezone_str": types.Schema(type=types.Type.STRING, description="Valid IANA timezone string (e.g., 'America/New_York', 'Asia/Kolkata')."),
            },
            required=["user_id", "timezone_str"],
        ),
    ),
    types.FunctionDeclaration(
        name="verify_dashboard_access",
        description="Call this ONLY after the user provides their password when they ask to check their dashboard.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "user_id": types.Schema(type=types.Type.STRING),
                "password": types.Schema(type=types.Type.STRING, description="The password provided by the user."),
            },
            required=["user_id", "password"],
        ),
    ),
]

TOOLS = [types.Tool(function_declarations=tool_declarations)]


# ─────────────────────────────────────────────────────────────
# TOOL DISPATCHER — Routes Gemini function calls through MCP Client
# ─────────────────────────────────────────────────────────────

async def _dispatch_tool(name: str, args: dict, user_id: str) -> str:
    """
    Dispatches a Gemini function call to the corresponding MCP Server tool.
    All database operations go through the MCP protocol layer.
    """
    # Ensure user_id is always present in args
    args["user_id"] = args.get("user_id", str(user_id))

    # Route through MCP Client
    return await mcp_client.call_tool(name, args)


# ─────────────────────────────────────────────────────────────
# MAIN AGENT ENTRY POINT
# ─────────────────────────────────────────────────────────────

async def chat_with_agent(
    message: str,
    user_id: str,
    history: List[Dict[str, Any]] = None,
    user_timezone: str = "UTC"
) -> str:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    now_utc = datetime.now(timezone.utc)
    current_time_str = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    try:
        tz = pytz.timezone(user_timezone)
        local_time = now_utc.astimezone(tz)
        local_time_str = local_time.strftime("%Y-%m-%d %H:%M:%S %Z (UTC%z)")
    except Exception:
        local_time_str = current_time_str

    system_prompt = (
        "You are LifeGuard AI, a strict but supportive accountability partner on WhatsApp.\n\n"
        f"CURRENT UTC TIME: {current_time_str}\n"
        f"USER LOCAL TIME: {local_time_str} (Timezone: {user_timezone})\n"
        f"USER ID: {user_id}\n\n"
        "RULES (follow exactly):\n"
        "1. Always pass the exact USER ID above to every tool call — never make one up.\n"
        "2. When calculating reminder times (e.g. 'in 10 minutes' or 'at 9:02 AM'), ALWAYS use the CURRENT UTC TIME or USER LOCAL TIME to compute the exact absolute UTC datetime in ISO-8601 format to pass to tools. DO NOT ask for their timezone unless it's necessary and they haven't provided enough info to deduce it.\n"
        "3. 'remind me', 'set a reminder', 'alert me', 'notify me at X' → ALWAYS call "
        "create_task_with_reminder. You have full ability to do this. Never say you cannot.\n"
        "4. 'add task', 'log this', 'I need to do X' (no time) → call create_task_only.\n"
        "5. 'done', 'finished', 'mark complete', 'cancel' → call update_task_status. "
        "If you need the task_id first, call get_upcoming_deadlines or get_all_pending_tasks to find it.\n"
        "6. Format all replies for WhatsApp: *bold*, _italics_, emojis. No markdown headers.\n"
        "7. Be concise — max 4 sentences. Confirm what you did, don't just say 'I will'.\n"
        "8. If the user asks for their schedule, list of tasks, or a specific task (e.g. 'what is my task 1'), ALWAYS call get_all_pending_tasks to check all tasks.\n"
        "9. If the user asks for a recurring reminder (e.g. 'every 1 hr'), set `recurring_interval_minutes`. The MINIMUM limit is 60 minutes (1 hour). If they ask for a recurrence less than 1 hour (e.g. 30 mins), refuse and state clearly that the minimum allowed recurring interval is 1 hour.\n"
        "10. **Follow-up Questions**: When a user creates a new task or reminder with very sparse details (e.g. 'Remind me at 10am'), ALWAYS successfully schedule the reminder FIRST using the tool, but then in your response politely ask a follow-up question like 'Got it, reminder set for 10 AM! Do you want to add more details or context to this task, or is this good as is?'\n"
        "11. **Dashboard Access**: If the user asks for their dashboard, dashboard link, or dashboard details, DO NOT provide task lists or stats. First, reply ONLY asking them to provide their 4-digit dashboard password for security. Once they reply with the password, call `verify_dashboard_access` to check it and give them the link.\n"
        "12. **Productivity Stats**: When the user asks 'how am I doing', 'my stats', 'my progress', 'productivity', call `get_productivity_stats` and present the results as a beautifully formatted WhatsApp stats card with emojis.\n"
        "13. **Delete Task**: When the user asks to delete/remove a task, first call `get_all_pending_tasks` to find the matching task_id, then call `delete_task` with it. Confirm the deletion.\n"
        "14. **Timezone Updates**: If the user asks to update their timezone, or mentions they are in a specific country/city (e.g., 'Update my timezone to India'), you MUST call `update_user_timezone` with the correct IANA timezone string (e.g., 'Asia/Kolkata'). Do not say you can't do it."
    )

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=TOOLS,
    )

    contents: List[types.Content] = []
    if history:
        for msg in history[-10:]:
            role = "user" if msg["is_from_user"] else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part(text=msg["message"])])
            )
    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

    try:
        while True:
            response = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=config,
            )

            candidate = response.candidates[0]
            fc_part = next(
                (p for p in candidate.content.parts if p.function_call),
                None,
            )

            if fc_part is None:
                return response.text  # Final answer

            fc = fc_part.function_call
            args = dict(fc.args) if fc.args else {}
            result_str = await _dispatch_tool(fc.name, args, user_id)

            contents.append(
                types.Content(role="model", parts=[types.Part(function_call=fc)])
            )
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=fc.name,
                                response={"result": result_str},
                            )
                        )
                    ],
                )
            )

    except Exception as e:
        print(f"Chat agent error: {e}")
        return "Sorry, something went wrong. Try again in a moment! \U0001f504"