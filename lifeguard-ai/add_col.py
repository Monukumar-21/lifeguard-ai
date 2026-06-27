import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from backend.database import DATABASE_URL

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE reminders ADD COLUMN recurring_interval_minutes INTEGER;"))
            print("Column added successfully.")
        except Exception as e:
            print("Error adding column:", e)

asyncio.run(main())
