#!/bin/bash
set -e

echo "========================================="
echo "  BinBot AI - VPS Deployment Script"
echo "========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err() { echo -e "${RED}[-]${NC} $1"; }

# Check if root
if [ "$EUID" -ne 0 ]; then
    err "Please run as root (sudo su)"
    exit 1
fi

# Update system
log "Updating system packages..."
apt update && apt upgrade -y

# Install dependencies
log "Installing dependencies..."
apt install -y docker.io docker-compose-v2 git curl python3 python3-pip python3-venv nodejs npm

# Start and enable Docker
log "Starting Docker..."
systemctl enable docker
systemctl start docker

# Verify installations
log "Verifying installations..."
docker --version
docker compose version
python3 --version
node --version

# Create app directory
log "Creating application directory..."
mkdir -p /opt/binbot
cd /opt/binbot

# Clone or copy the project
if [ -d "/opt/binbot/.git" ]; then
    log "Pulling latest code..."
    git pull
else
    warn "No git repo found. You need to push your code to GitHub first."
    warn "For now, we'll create the project structure manually."
fi

# Create backend directory structure
log "Setting up backend..."
mkdir -p backend/app/{api,core,models,schemas,services,workers,ml}
mkdir -p backend/tests
mkdir -p backend/alembic/versions

# Create frontend directory structure
log "Setting up frontend..."
mkdir -p frontend/src/{app/{api,components,lib,styles},hooks,services}

# Create infrastructure directory
log "Setting up infrastructure..."
mkdir -p infrastructure/{docker,k8s,nginx}

# Create .env file
log "Creating .env file..."
cat > backend/.env << 'ENVEOF'
# Application
APP_NAME=BinBot AI Trading
APP_VERSION=1.0.0
DEBUG=false

# Database
DATABASE_URL=postgresql+asyncpg://postgres:binbot_secret_pass@postgres:5432/binbot
DATABASE_URL_SYNC=postgresql://postgres:binbot_secret_pass@localhost:5432/binbot

# Redis
REDIS_URL=redis://redis:6379/0

# Security - CHANGE THESE IN PRODUCTION
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ENCRYPTION_KEY=$(openssl rand -base64 32 | head -c 32)

# Binance
BINANCE_API_URL=https://fapi.binance.com
BINANCE_WS_URL=wss://fstream.binance.com/ws
BINANCE_TESTNET_API_URL=https://testnet.binancefuture.com
BINANCE_TESTNET_WS_URL=wss://stream.binancefuture.com/ws

# Stripe (add your keys later)
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_FREE=
STRIPE_PRICE_STARTER=
STRIPE_PRICE_PRO=
STRIPE_PRICE_ENTERPRISE=

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@binbot.ai

# URLs
FRONTEND_URL=http://69.62.83.238
CORS_ORIGINS=["http://69.62.83.238","http://69.62.83.238:3000","http://69.62.83.238:8000"]

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=binbot-data

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
ENVEOF

# Generate secure keys
log "Generating secure keys..."
SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -base64 48 | head -c 32)
sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" backend/.env
sed -i "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=$ENCRYPTION_KEY/" backend/.env

log "Keys generated:"
log "SECRET_KEY: $SECRET_KEY"
log "ENCRYPTION_KEY: $ENCRYPTION_KEY"

# Create docker-compose.yml
log "Creating docker-compose.yml..."
cat > docker-compose.yml << 'DCEOF'
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: binbot_secret_pass
      POSTGRES_DB: binbot
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: ../infrastructure/docker/Dockerfile.backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    volumes:
      - ./backend:/app

  frontend:
    build:
      context: ./frontend
      dockerfile: ../infrastructure/docker/Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://69.62.83.238:8000
    depends_on:
      - backend
    restart: unless-stopped

  celery-worker:
    build:
      context: ./backend
      dockerfile: ../infrastructure/docker/Dockerfile.backend
    command: celery -A app.workers.tasks worker --loglevel=info
    env_file:
      - ./backend/.env
    depends_on:
      - redis
      - postgres
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
DCEOF

# Create backend Dockerfile
log "Creating Dockerfiles..."
cat > infrastructure/docker/Dockerfile.backend << 'DOCEOF'
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
DOCEOF

cat > infrastructure/docker/Dockerfile.frontend << 'DOCEOF'
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

COPY --from=builder /app/package.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/public ./public

EXPOSE 3000

ENV NODE_ENV=production

CMD ["npm", "start"]
DOCEOF

# Open firewall ports
log "Opening firewall ports..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 3000/tcp
ufw allow 8000/tcp
ufw allow 5432/tcp
ufw allow 6379/tcp
echo "y" | ufw enable 2>/dev/null || true

# Start services
log "Starting services with Docker Compose..."
docker compose up -d

# Wait for services to be ready
log "Waiting for services to start..."
sleep 30

# Check service status
log "Checking service status..."
docker compose ps

# Run database migrations
log "Running database migrations..."
docker compose exec -T backend alembic upgrade head 2>/dev/null || {
    warn "Migrations failed - you may need to run manually:"
    warn "docker compose exec backend alembic upgrade head"
}

# Final status
echo ""
echo "========================================="
echo "  Deployment Complete!"
echo "========================================="
echo ""
echo "Services:"
echo "  Frontend:  http://69.62.83.238:3000"
echo "  Backend:   http://69.62.83.238:8000"
echo "  API Docs:  http://69.62.83.238:8000/docs"
echo ""
echo "To view logs:"
echo "  docker compose logs -f"
echo ""
echo "To restart:"
echo "  docker compose restart"
echo ""
echo "To stop:"
echo "  docker compose down"
echo ""
