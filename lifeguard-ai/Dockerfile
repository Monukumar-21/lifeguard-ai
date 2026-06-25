FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for asyncpg/PostgreSQL and compilation
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ ./backend/
COPY alembic.ini .

# Start command is handled by railway.json, but provide a robust fallback
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]