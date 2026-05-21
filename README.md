# BinBot AI - AI-Powered Binance Futures Trading Platform

A production-grade multi-tenant SaaS platform for AI-powered Binance Futures trading with real-time market analysis, automated strategy execution, risk management, and subscription billing.

## Features

- **Multi-tenant SaaS architecture** with role-based access control
- **6 trading strategies**: Trend Following, Mean Reversion, Momentum Breakout, Scalping, Volatility Expansion, Multi-Timeframe
- **ML predictions** using XGBoost for trade confirmation
- **Comprehensive risk engine** with mandatory stop losses, dynamic position sizing, drawdown protection
- **Backtesting engine** with historical data
- **Paper trading** for strategy validation
- **Live trading** with Binance Futures API
- **Real-time analytics** dashboard with PnL, win rate, Sharpe ratio, and more
- **Stripe subscription billing** with 4 plans
- **2FA authentication** with TOTP
- **WebSocket** real-time updates

## Tech Stack

### Backend
- FastAPI (Python 3.12)
- PostgreSQL + SQLAlchemy (async)
- Redis (caching, Celery broker)
- Celery (background tasks)
- XGBoost + Scikit-Learn (ML)
- Pandas + NumPy (data processing)

### Frontend
- Next.js 15 (App Router)
- React 19 + TypeScript
- Tailwind CSS + ShadCN UI
- Recharts (analytics)
- Zustand (state management)
- Axios (API client)

### Infrastructure
- Docker + Docker Compose
- Kubernetes
- Nginx (reverse proxy)
- MinIO (object storage)
- GitHub Actions (CI/CD)

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- PostgreSQL 16+
- Redis 7+

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

### Docker Compose

```bash
docker-compose -f infrastructure/docker/docker-compose.yml up -d
```

## Project Structure

```
binbot/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes
│   │   ├── core/         # Config, security, database
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   ├── workers/      # Celery tasks
│   │   └── ml/           # ML prediction system
│   ├── tests/
│   └── alembic/
├── frontend/
│   └── src/
│       ├── app/          # Next.js pages
│       ├── components/   # React components
│       ├── lib/          # Utilities, API client, store
│       └── hooks/        # Custom hooks
├── infrastructure/
│   ├── docker/           # Dockerfiles, docker-compose
│   ├── k8s/              # Kubernetes manifests
│   └── nginx/            # Nginx configuration
└── .github/workflows/    # CI/CD
```

## Trading Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| Trend Following | EMA crossovers with Supertrend | Trending markets |
| Mean Reversion | Bollinger Bands + RSI bounce | Ranging markets |
| Momentum Breakout | Volume-confirmed breakouts | Volatile breakouts |
| Scalping | Stochastic RSI + short EMAs | Quick trades |
| Volatility Expansion | BB squeeze breakouts | Post-consolidation |
| Multi-Timeframe | Cross-timeframe confirmation | High confidence |

## Risk Management

- **Max risk per trade**: 1% of account
- **Max daily loss**: 3% of account
- **Max drawdown**: 8% of account
- **Max consecutive losses**: 3 (trading pauses)
- **Max leverage**: 5x
- **Stop loss**: Mandatory on all trades
- **Trailing stop**: Supported
- **Breakeven logic**: Automatic
- **Multiple take profit levels**: Configurable

**Never**: Martingale, averaging down, unlimited leverage

## Subscription Plans

| Plan | Price | Bots | Features |
|------|-------|------|----------|
| Free | $0 | 1 | Paper trading, basic indicators |
| Starter | $29/mo | 3 | Backtesting, live trading, basic strategies |
| Pro | $99/mo | Unlimited | AI strategies, ML predictions, analytics |
| Enterprise | $299/mo | Unlimited | White-label, API access, team management |

## Real-Time WebSocket Streaming

The platform uses Binance Futures WebSocket for real-time market data:

### Subscribed Streams
- **Klines**: 1m, 5m, 15m, 1h, 4h intervals
- **Ticker**: 24hr price, volume, change
- **Order Book**: Top 20 levels @ 100ms
- **Trades**: Real-time trade stream
- **Mark Price**: Funding rate + open interest
- **Liquidations**: Forced order stream

### Real-Time Metrics
- VWAP (Volume Weighted Average Price)
- Volume Profile (POC, VAH, VAL)
- Buy/Sell Ratio
- Volatility Index
- Order Book Imbalance
- Recent Liquidations

### API Endpoints
- `GET /api/ws/price/{symbol}` - Real-time price
- `GET /api/ws/klines/{symbol}/{interval}` - Live kline cache
- `GET /api/ws/orderbook/{symbol}` - Live order book
- `GET /api/ws/metrics/{symbol}` - All real-time metrics
- `WS /api/ws/{user_id}` - User-specific WebSocket for live updates

### Strategy Improvements with WebSocket
- **Volume confirmation**: Real buy/sell ratio filters false breakouts
- **Volatility filter**: Avoids low-volatility chop
- **Liquidation awareness**: Detects cascade liquidation zones
- **Order book imbalance**: Confirms directional bias
- **VWAP alignment**: Trades only in direction of VWAP

## API Documentation

Once the backend is running, visit `http://localhost:8000/docs` for the interactive Swagger UI.

### Key Endpoints

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user
- `GET /api/bots/` - List bots
- `POST /api/bots/` - Create bot
- `POST /api/bots/{id}/start` - Start bot
- `POST /api/bots/{id}/stop` - Stop bot
- `POST /api/backtests/` - Run backtest
- `GET /api/analytics/` - Get analytics
- `POST /api/billing/checkout` - Create Stripe checkout

## Security

- API keys encrypted with AES-256
- JWT authentication with refresh tokens
- 2FA with TOTP
- Rate limiting on all endpoints
- CORS protection
- Tenant isolation (users can only access their data)
- Audit logging for all actions

## Deployment

### Kubernetes

```bash
kubectl apply -f infrastructure/k8s/manifests.yaml
```

### Environment Variables

Copy `.env.example` to `.env` and configure:
- Database credentials
- Redis URL
- Secret keys
- Stripe API keys
- SMTP settings
- Binance API (optional, users add their own)

## License

Proprietary. All rights reserved.

## Support

For support, contact support@binbot.ai or open an issue on GitHub.
