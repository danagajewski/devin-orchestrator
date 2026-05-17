# Devin Orchestrator

Automated issue resolution for [danagajewski/superset](https://github.com/danagajewski/superset) powered by the [Devin API](https://docs.devin.ai).

When a GitHub issue is created on the target repository, this service automatically spins up a Devin session to analyze and fix it — then tracks progress, cost, and outcomes through a lightweight dashboard.

## Architecture

```
GitHub (superset repo)
    │ issue.opened webhook
    ▼
┌────────────────────────────────────┐
│         Docker Compose             │
│                                    │
│  ┌─────────────┐  ┌────────────┐  │
│  │   Backend    │  │  Frontend  │  │
│  │  (FastAPI)   │  │  (React)   │  │
│  │             │  │            │  │
│  │  - Webhook  │◄─│  Dashboard │  │
│  │  - Devin API│  │  (Vite)    │  │
│  │  - Poller   │  │            │  │
│  │  - Metrics  │  └────────────┘  │
│  └──────┬──────┘                   │
│         │                          │
│    data.json (file storage)        │
└────────────────────────────────────┘
          │
          ▼
    Devin API (api.devin.ai/v3)
```

## Features

- **Webhook-driven**: Automatically creates Devin sessions when GitHub issues are opened
- **Session tracking**: Polls Devin API to track session status, ACU consumption, and PR creation
- **Metrics dashboard**: Real-time view of total sessions, success rate, cost, and resolution time
- **Cost visualization**: Bar chart showing ACU cost per session with status-based coloring
- **Activity feed**: Chronological feed of session events (created, completed, PR opened, failed)
- **File-based storage**: Simple JSON file — no database required
- **Docker-ready**: Single `docker compose up` to run the full stack

## Quick Start

### Prerequisites

- Docker and Docker Compose
- A [Devin API key](https://docs.devin.ai/api-reference/getting-started/teams-quickstart) (service user with `ManageOrgSessions` permission)
- Your Devin organization ID

### 1. Clone and configure

```bash
git clone https://github.com/danagajewski/devin-orchestrator.git
cd devin-orchestrator
cp .env.example .env
```

Edit `.env` with your credentials:

```env
DEVIN_API_KEY=cog_your_api_key_here
DEVIN_ORG_ID=org-your_org_id_here
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
TARGET_REPO=danagajewski/superset
```

### 2. Run with Docker

```bash
docker compose up --build
```

- **Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API docs**: http://localhost:8000/docs

### 3. Set up GitHub Webhook

1. Go to your target repo → **Settings** → **Webhooks** → **Add webhook**
2. **Payload URL**: `https://your-server:3000/webhook/github` (the nginx proxy forwards to the backend)
3. **Content type**: `application/json`
4. **Secret**: Same value as `GITHUB_WEBHOOK_SECRET` in your `.env`
5. **Events**: Select **Issues** only
6. Click **Add webhook**

## Local Development

### Backend

```bash
cd backend
cp .env.example .env  # Edit with your credentials
poetry install
poetry run uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

The frontend dev server runs on http://localhost:5173 and proxies API requests to the backend at http://localhost:8000.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/webhook/github` | GitHub webhook receiver |
| `GET` | `/api/sessions` | List all tracked sessions |
| `GET` | `/api/sessions/{id}` | Get session details |
| `GET` | `/api/metrics` | Aggregated metrics |
| `GET` | `/api/health` | Health check |

## Dashboard

The dashboard provides:

- **Metrics cards**: Total sessions, success rate, total ACUs consumed, average resolution time
- **Cost chart**: ACU consumption per session (bar chart, color-coded by status)
- **Activity feed**: Recent events across all sessions
- **Session table**: Filterable list with issue links, Devin session links, status badges, PR links

Data auto-refreshes every 10 seconds.

## Project Structure

```
devin-orchestrator/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app with CORS and routes
│   │   ├── webhook.py        # GitHub webhook handler
│   │   ├── devin_client.py   # Devin API v3 client
│   │   ├── poller.py         # Background session status poller
│   │   ├── storage.py        # JSON file-based storage
│   │   ├── models.py         # Pydantic models
│   │   └── config.py         # Settings via env vars
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # Main dashboard layout
│   │   ├── components/
│   │   │   ├── MetricsPanel.tsx
│   │   │   ├── SessionList.tsx
│   │   │   ├── CostChart.tsx
│   │   │   └── ActivityFeed.tsx
│   │   └── lib/api.ts         # API client
│   ├── nginx.conf             # Reverse proxy config
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEVIN_API_KEY` | Yes | — | Devin service user API key |
| `DEVIN_ORG_ID` | Yes | — | Devin organization ID |
| `GITHUB_WEBHOOK_SECRET` | Yes | — | Secret for webhook signature validation |
| `TARGET_REPO` | No | `danagajewski/superset` | Repository for Devin sessions |
| `POLL_INTERVAL_SECONDS` | No | `30` | Session status polling interval |
