from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import whatsapp, tasks, goals, subscriptions
from backend.database import engine
from backend.models import Base
from backend.scheduler.reminder_scheduler import start_scheduler, stop_scheduler
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist (For dev/hackathon purposes)
    # In production, use Alembic migrations instead
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
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

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

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