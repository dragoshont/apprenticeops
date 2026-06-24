# ApprenticeOps mission-control — single image: build the Vite UI, serve via FastAPI.
# The container reaches the home node over SSH, so it needs openssh-client and a
# mounted key + ssh config (see compose.yaml).

# ---- stage 1: build the React/Vite frontend -------------------------------------
FROM node:22-slim AS ui
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- stage 2: python backend ----------------------------------------------------
FROM python:3.12-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends openssh-client \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=ui /ui/dist ./frontend/dist

ENV HOST=0.0.0.0 PORT=8770 HOME_SSH=home
EXPOSE 8770
CMD ["python", "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8770"]
