import os
import ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

raw_url = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:5432/lifeguard"
)

if raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif raw_url.startswith("postgresql://"):
    raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

if "?sslmode=require" in raw_url:
    DATABASE_URL = raw_url.replace("?sslmode=require", "")
elif "&sslmode=require" in raw_url:
    DATABASE_URL = raw_url.replace("&sslmode=require", "")
else:
    DATABASE_URL = raw_url

connect_args = {}
if "neon.tech" in DATABASE_URL:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    connect_args["ssl"] = ctx

# Create the async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    connect_args=connect_args
)

# Create an async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Dependency for FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
