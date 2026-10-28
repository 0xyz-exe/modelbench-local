FROM node:20-slim AS frontend-builder
WORKDIR /app/apps/web
COPY apps/web/package*.json ./
RUN npm install
COPY apps/web ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY --from=frontend-builder /app/apps/web/dist ./apps/web/dist
RUN mkdir -p /app/data
ENV DATABASE_URL=sqlite:////app/data/modelbench.db
ENV PYTHONPATH=/app/backend
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
