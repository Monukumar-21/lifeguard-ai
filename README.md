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
- **Modern Dashboard**: A clean, responsive React-based dashboard to visualize your week and priorities when you need a macro view.
- **Subscription Management**: Track your recurring subscriptions.

## 🛠️ Tech Stack

- **Frontend**: React, TypeScript, Vite, Tailwind CSS, Recharts, Framer Motion
- **Backend**: Python, FastAPI, SQLAlchemy, Alembic (Asyncpg for PostgreSQL)
- **AI/LLM**: Google Gemini API
- **Messaging**: Meta WhatsApp Cloud API
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

- **WhatsApp-First Onboarding**: Implement a frictionless registration process where the user signs in via the web dashboard, verifies their phone number, and is immediately handed off to the WhatsApp agent. After this initial setup, the user *never* has to visit the website for daily task updates—everything is handled seamlessly via WhatsApp.
- **Dedicated Views for Tasks, Goals, and Subscriptions**: Implement detailed standalone pages for managing individual tasks, deeper goal tracking progress, and comprehensive subscription management interfaces for power users who want deep analytics.
- **Tiered Subscription Plans**: 
  - **Free Tier**: Limited number of task schedules and basic accountability nudges.
  - **Premium Tier**: Unlimited task scheduling, advanced goal tracking, deeper Gemini AI insights, and custom nudge frequencies.

## ☁️ Deployment

We have included configurations to easily deploy this stack:
- **Backend**: Ready to be deployed on [Railway](https://railway.app/) using the provided `Dockerfile` and `railway.json`.
- **Frontend**: Ready to be deployed on [Vercel](https://vercel.com/) using the provided `vercel.json` (Vite framework).

