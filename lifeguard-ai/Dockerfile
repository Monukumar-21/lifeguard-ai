# /lifeguard-ai/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code and migration files
COPY backend/ ./backend/
COPY alembic.ini .

# Expose port
EXPOSE 8000

# We only run the server here. 
# Do NOT run alembic migrations in the CMD.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]