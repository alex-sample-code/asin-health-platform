# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + static files
FROM python:3.12-slim
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy Python project files
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev

# Copy source code
COPY src/ ./src/
COPY data/ ./data/
COPY main.py ./

# Copy frontend build to static directory
COPY --from=frontend-builder /app/frontend/dist ./static/

# Install uvicorn with standard extras for production
RUN uv pip install uvicorn[standard]

EXPOSE 8000

# Run with uvicorn, serving both API and static files
CMD ["uv", "run", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
