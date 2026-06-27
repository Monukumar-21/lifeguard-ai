from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import whatsapp, tasks, goals, subscriptions
from backend.database import engine, AsyncSessionLocal
from backend.models import Base
from backend.scheduler.reminder_scheduler import start_scheduler, stop_scheduler
from backend.seed_data import seed_demo_data
from backend.mcp_server import mcp_server
from backend.a2a_protocol import router as a2a_router
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist (For dev/hackathon purposes)
    # In production, use Alembic migrations instead
    import os
    async with engine.begin() as conn:
        if os.getenv("RESET_DB") == "true":
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed demo data after fresh reset
    if os.getenv("RESET_DB") == "true":
        async with AsyncSessionLocal() as session:
            await seed_demo_data(session)
    
    # Start APScheduler
    start_scheduler()
    
    yield
    
    # Shutdown APScheduler
    stop_scheduler()

app = FastAPI(title="LifeGuard AI Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers (all under /api prefix)
app.include_router(whatsapp.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(goals.router, prefix="/api")
app.include_router(subscriptions.router, prefix="/api")

# Mount MCP Server (Model Context Protocol)
# Exposes all database tools via the MCP standard at /mcp
try:
    app.mount("/mcp", mcp_server.sse_app())
    print("MCP Server mounted at /mcp")
except Exception as e:
    print(f"Warning: Could not mount MCP SSE app (will use in-process calls): {e}")

# Mount A2A Protocol (Agent-to-Agent)
# Exposes agent cards at /.well-known/agent.json and task endpoints at /a2a/*
app.include_router(a2a_router)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "protocols": {
            "mcp": {"enabled": True, "endpoint": "/mcp"},
            "a2a": {"enabled": True, "agent_card": "/.well-known/agent.json"},
        },
    }

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Grab the port Railway assigns dynamically, or default to 8000 locally
    port = int(os.environ.get("PORT", 8000))
    
    # Run the server with proxy-headers enabled (Crucial for Railway!)
    uvicorn.run(
        "backend.main:app", 
        host="0.0.0.0", 
        port=port, 
        proxy_headers=True, 
        forwarded_allow_ips="*"
    )