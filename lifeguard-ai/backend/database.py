import os
import ssl
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

raw_url = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:5432/lifeguard"
)

# Normalize the scheme to postgresql+asyncpg
if raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif raw_url.startswith("postgresql://"):
    raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Strip sslmode from the URL query parameters (asyncpg doesn't support it as a URL param)
parsed = urlparse(raw_url)
query_params = parse_qs(parsed.query)
query_params.pop("sslmode", None)
clean_query = urlencode(query_params, doseq=True)
DATABASE_URL = urlunparse(parsed._replace(query=clean_query))

# Enable SSL for any non-localhost database connection
connect_args = {}
is_remote = "localhost" not in DATABASE_URL and "127.0.0.1" not in DATABASE_URL
if is_remote:
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
