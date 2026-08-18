# ------------------------------------------------------------
# Stage 1: Build the React frontend
# ------------------------------------------------------------

FROM node:24-bookworm-slim AS frontend-builder

WORKDIR /app/frontend-vite

COPY frontend-vite/package.json frontend-vite/package-lock.json ./

RUN npm ci

COPY frontend-vite/ ./

RUN npm run build


# ------------------------------------------------------------
# Stage 2: Build the production Python application
# ------------------------------------------------------------

FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt

RUN python -m pip install \
    --no-cache-dir \
    -r /app/backend/requirements.txt

COPY backend/ /app/backend/

COPY --from=frontend-builder \
    /app/frontend-vite/dist \
    /app/frontend-vite/dist

WORKDIR /app/backend

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--app-dir", "app", "--host", "0.0.0.0", "--port", "8000"]