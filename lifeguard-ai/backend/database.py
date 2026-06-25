import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# The database URL for Neon PostgreSQL using asyncpg
# Expected format: postgresql+asyncpg://user:password@endpoint/dbname
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:5432/lifeguard"
)

# Create the async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800, # Recycle connections after 30 minutes
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
