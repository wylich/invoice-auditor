# Stage 1: Build React frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN VITE_API_URL="" npm run build

# Stage 2: Python backend
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app

# Install Python dependencies (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application
COPY config.toml ./
COPY src/ src/
COPY data/ data/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist/ frontend/dist/

EXPOSE 8080
CMD uv run uvicorn invoice_auditor.api.app:app --host 0.0.0.0 --port ${PORT:-8080}
