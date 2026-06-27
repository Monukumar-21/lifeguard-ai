# LifeGuard AI 🛟

LifeGuard AI is an intelligent accountability agent designed to keep you on track with your goals, deadlines, and priorities, directly from the app you already use every day: **WhatsApp**.

## 🎯 The Problem

As students and busy professionals, we often struggle with procrastination. We download complex scheduling apps with the best of intentions, but the friction of creating tasks, manually checking them off, and navigating clunky UIs often leads to app abandonment. The effort required to maintain the productivity system becomes a burdensome task in itself.

## 💡 The Solution: Zero-Friction Accountability

LifeGuard AI removes this friction entirely. We built this as an intelligent WhatsApp bot capable of handling task scheduling, bill reminders, and goal tracking without requiring you to open a separate app. 

- **No menus to navigate.**
- **No new interface to learn.**
- **Just send a text.** 

Want to add a task? Text it. Need to check off a goal? Reply to the agent. LifeGuard AI acts as your personal accountability partner, ensuring you get things done with zero cognitive overhead.

## 📱 Why WhatsApp?

When a WhatsApp notification pops up, it automatically triggers a psychological response of urgency and importance. By embedding our AI agent into WhatsApp, we leverage this existing habit loop. You get nudged exactly where you are most responsive, making it significantly harder to ignore your responsibilities compared to a standard push notification from a to-do app.

## ✨ Features

### Core AI Agent
- **Proactive WhatsApp Agent**: Get nudged about your upcoming deadlines and priorities directly on WhatsApp.
- **Conversational Task Management**: Add tasks, schedule events, and check off items just by texting in natural language. The agent proactively asks follow-up questions to ensure all details are captured.
- **Smart Priority Management**: AI helps sort and track your most critical tasks.
- **Goal Tracking**: Keep track of long-term goals and progress.
- **Delete Tasks via Chat**: Say "delete my task X" and the AI will find and remove it.

### Automation & Scheduling
- **Smart Recurring Reminders**: Set exact recurring notifications (e.g. "remind me every 1 hour") with a minimum 1-hour interval enforced by the AI.
- **Daily Morning Briefing**: At 8 AM UTC every day, the bot proactively sends you a personalized summary of your pending tasks, overdue items, and a motivational nudge.
- **Overdue Task Nudges**: Every 6 hours, the system detects overdue tasks and sends automated WhatsApp alerts to keep you accountable.
- **10-Second Precision Scheduler**: Reminders trigger within 10 seconds of their scheduled time for near-instant delivery.

### Security & Onboarding
- **WhatsApp-First Onboarding**: Users sign in via the web dashboard, provide their phone number and create a custom 4-digit PIN, and are instantly greeted by the bot on WhatsApp with a full introduction.
- **Secure WhatsApp Dashboard Access**: Users can say "I want to check my dashboard" on WhatsApp, verify their custom PIN with the AI, and receive a secure link to view their data.
- **Timezone Intelligence**: The AI automatically calculates local time for scheduling. Users can set their timezone via chat (e.g., "I'm in India").

### Analytics & Insights
- **Productivity Stats**: Ask "how am I doing?" and the AI returns a formatted stats card with total tasks, completion rate, overdue count, and weekly progress.

### Monetization
- **Tiered Subscription Plans**: 
  - **Free Tier**: Limited to 10 AI messages per day.
  - **Premium Tier (₹50)**: Unlimited AI messages, advanced scheduling, and no rate limits.
- **In-App Upgrade Prompt**: Premium upgrade is prominently displayed in the dashboard sidebar and WhatsApp rate-limit messages.

### Dashboard
- **Modern Dashboard**: A clean, responsive React-based dashboard to visualize your week, priorities, goals, and recent WhatsApp conversations.
- **Plan Indicator**: Clearly shows your current plan (Free/Premium) with usage limits.

## 🛠️ Tech Stack

- **Frontend**: React, TypeScript, Vite, Tailwind CSS, Recharts, Framer Motion
- **Backend**: Python, FastAPI, SQLAlchemy, APScheduler (Asyncpg for PostgreSQL)
- **AI/LLM**: Google Gemini 2.5 Flash API (with function calling / tool use)
- **Protocols**: MCP (Model Context Protocol) for tool access, A2A (Agent-to-Agent) for inter-agent communication
- **Messaging**: Twilio Cloud API for WhatsApp
- **Database**: PostgreSQL (Railway)
- **Deployment**: Railway (Backend) + Vercel (Frontend)

## 📂 Project Structure

```
├── src/                  # React Frontend (Vite)
├── lifeguard-ai/
│   ├── backend/
│   │   ├── agents/       # AI Agents (chat_agent, reminder_agent)
│   │   ├── routers/      # API routes (whatsapp, tasks, goals, subscriptions)
│   │   ├── scheduler/    # APScheduler jobs (reminders, briefing, nudges)
│   │   ├── mcp_server.py # MCP Server — all DB tools via MCP protocol
│   │   ├── a2a_protocol.py # A2A Agent Cards & task endpoints
│   │   ├── models.py     # SQLAlchemy models
│   │   ├── database.py   # DB engine & session
│   │   ├── seed_data.py  # Demo data seeder
│   │   └── main.py       # FastAPI app & lifespan
│   ├── Dockerfile        # Backend Docker configuration
│   ├── railway.json      # Railway deployment config
│   └── DEPLOY.md         # Deployment instructions
├── vercel.json           # Vercel deployment config
└── package.json          # Frontend dependencies
```

## 🧠 Architecture: MCP + A2A

LifeGuard AI uses two modern AI protocols to ensure clean separation of concerns and inter-agent interoperability:

### MCP (Model Context Protocol)
Instead of AI agents directly querying the database, all data operations are exposed as **MCP Tools** through an MCP Server mounted at `/mcp`. The Chat Agent acts as an MCP Client, calling tools through the standardized protocol.

```
User (WhatsApp) → Chat Agent (MCP Client) → MCP Server → PostgreSQL Database
```

- **MCP Server**: `backend/mcp_server.py` — Exposes 12+ tools (CRUD tasks, reminders, stats, etc.)
- **MCP Client**: Built into `backend/agents/chat_agent.py` — Routes all Gemini function calls through MCP
- **SSE Transport**: The MCP server is also accessible via SSE at `/mcp` for external tool clients

### A2A (Agent-to-Agent Protocol)
Following Google’s open A2A standard, each agent publishes an **Agent Card** describing its capabilities. Agents can delegate tasks to each other via structured task endpoints.

- **Agent Discovery**: `GET /.well-known/agent.json` — Returns cards for both Chat Agent and Reminder Agent
- **Chat Agent Task**: `POST /a2a/chat` — Accepts natural language tasks from external agents
- **Reminder Agent Task**: `POST /a2a/reminder` — Generates personalized reminder messages via A2A delegation

## 🚀 Getting Started Locally

### 1. Backend Setup (FastAPI)

1. Navigate to the backend directory:
   ```bash
   cd lifeguard-ai
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r backend/requirements.txt
   ```
3. Set up your environment variables (see `.env.example` format in deployment docs or create a local `.env`).
4. Start the backend server (tables auto-created on first run):
   ```bash
   uvicorn backend.main:app --reload
   ```
5. *(Optional)* To seed with demo data, set `RESET_DB=true` as an env variable before starting:
   ```bash
   RESET_DB=true uvicorn backend.main:app --reload
   ```

### 2. Frontend Setup (React/Vite)

1. Navigate back to the root directory (or open a new terminal in the root).
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

## 🔮 Future Scope (The Master Plan)

- **Dedicated Views for Tasks, Goals, and Subscriptions**: Implement detailed standalone pages for managing individual tasks, deeper goal tracking progress, and comprehensive subscription management interfaces for power users who want deep analytics.
- **Webhooks for Subscriptions**: Integrate Stripe/Razorpay webhooks to automatically activate the premium tier upon successful payment.
- **Voice Note Processing**: Transcribe and parse WhatsApp voice notes into tasks using Whisper API.
- **Team Collaboration**: Allow shared accountability groups where multiple users can track each other's progress.

## ☁️ Deployment

We have included configurations to easily deploy this stack:

### 1. Deploying the Backend (Railway)
- The backend is ready to be deployed on [Railway](https://railway.app/) using the provided `Dockerfile` and `railway.json`.
- When deploying, ensure you set your environment variables (like `GEMINI_API_KEY`, `DATABASE_URL`, Twilio credentials).
- *Note:* Set `RESET_DB=true` for the first deployment to create tables and seed demo data. Remove it afterwards.

### 2. Deploying the Frontend (Vercel)
- The frontend is built with Vite and ready to be deployed on [Vercel](https://vercel.com/) using the provided `vercel.json`.
- **Connecting to the Backend:** When deploying to Vercel, you must set an Environment Variable named `VITE_API_URL`. Set this to the public URL of your deployed Railway backend (e.g., `https://lifeguard-backend-production.up.railway.app`).
- Vercel will automatically build the app and connect all API calls to your live backend.
