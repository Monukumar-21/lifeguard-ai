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

- **Proactive WhatsApp Agent**: Get nudged about your upcoming deadlines and priorities directly on WhatsApp.
- **Conversational Task Management**: Add tasks, schedule events, and check off items just by texting in natural language.
- **Smart Priority Management**: AI helps sort and track your most critical tasks.
- **Goal Tracking**: Keep track of long-term goals and progress.
- **WhatsApp-First Onboarding**: Users sign in via the web dashboard, provide their phone number, and are immediately handed off to the WhatsApp agent. After initial setup, users can manage everything seamlessly via WhatsApp without returning to the website.
- **Tiered Subscription Plans**: 
  - **Free Tier**: Limited to 10 messages/day.
  - **Premium Tier (₹50)**: Unlimited AI messages, advanced scheduling, and no rate limits.
- **Smart Recurring Reminders**: Ability to set exact recurring notifications (e.g. "every 1 hour") via WhatsApp.
- **Modern Dashboard**: A clean, responsive React-based dashboard to visualize your week and priorities when you need a macro view.
- **Subscription Management**: Track your recurring subscriptions.

## 🛠️ Tech Stack

- **Frontend**: React, TypeScript, Vite, Tailwind CSS, Recharts, Framer Motion
- **Backend**: Python, FastAPI, SQLAlchemy, Alembic (Asyncpg for PostgreSQL)
- **AI/LLM**: Google Gemini API
- **Messaging**: Twilio Cloud API
- **Caching/Rate Limiting**: Upstash Redis

## 📂 Project Structure

```
├── src/                  # React Frontend (Vite)
├── lifeguard-ai/
│   ├── backend/          # FastAPI Backend Application
│   ├── Dockerfile        # Backend Docker configuration
│   ├── alembic.ini       # Database migrations config
│   ├── railway.json      # Railway deployment config
│   └── DEPLOY.md         # Deployment instructions
├── vercel.json           # Vercel deployment config
└── package.json          # Frontend dependencies
```

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
4. Run the database migrations (requires a running PostgreSQL database):
   ```bash
   alembic upgrade head
   ```
5. Start the backend server:
   ```bash
   uvicorn backend.main:app --reload
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
- **Webhooks for Subscriptions**: Integrate Stripe webhooks to automatically activate the premium tier upon successful payment.

## ☁️ Deployment

We have included configurations to easily deploy this stack:

### 1. Deploying the Backend (Railway)
- The backend is ready to be deployed on [Railway](https://railway.app/) using the provided `Dockerfile` and `railway.json`.
- When deploying, ensure you set your environment variables (like `GEMINI_API_KEY`, `DATABASE_URL`, Twilio credentials).
- *Note:* If you need to reset your schema or apply our new columns in the building phase, set `RESET_DB=true` in Railway variables for one deployment, then remove it.

### 2. Deploying the Frontend (Vercel)
- The frontend is built with Vite and ready to be deployed on [Vercel](https://vercel.com/) using the provided `vercel.json`.
- **Connecting to the Backend:** When deploying to Vercel, you must set an Environment Variable named `VITE_API_URL`. Set this to the public URL of your deployed Railway backend (e.g., `https://lifeguard-backend-production.up.railway.app`).
- Vercel will automatically build the app and connect all API calls to your live backend.

