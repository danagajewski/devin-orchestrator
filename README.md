# Devin Orchestrator

Automated issue resolution for [danagajewski/superset](https://github.com/danagajewski/superset) powered by the [Devin API](https://docs.devin.ai).

When a GitHub issue is created on the target repository, this service automatically spins up a Devin session to analyze and fix it — then tracks progress, cost, and outcomes through a lightweight dashboard. When the fix is ready, the orchestrator can auto-merge the PR or request human review based on configurable rules.

## Architecture

```
GitHub (superset repo)
    │ issue.opened / pull_request.closed webhooks
    ▼
┌──────────────────────────────────────────────┐
│              Docker Compose                  │
│                                              │
│  ┌──────────────┐     ┌──────────────┐       │
│  │   Backend     │     │   Frontend   │       │
│  │  (FastAPI)    │     │   (React)    │       │
│  │               │     │              │       │
│  │  - Webhook    │◄────│  Dashboard   │       │
│  │  - Devin API  │     │  (Vite)      │       │
│  │  - Poller     │     │              │       │
│  │  - GitHub API │     └──────────────┘       │
│  │  - Auto-merge │                            │
│  └──────┬────────┘                            │
│         │                                     │
│    data.json (file storage)                   │
│                                               │
│  ┌──────────────┐  (optional)                 │
│  │    ngrok      │  webhook tunnel             │
│  └──────────────┘                             │
└──────────────────────────────────────────────┘
          │
          ▼
    Devin API (api.devin.ai/v3)
```

## Features

### Core
- **Webhook-driven**: Automatically creates Devin sessions when GitHub issues are opened
- **Session tracking**: Polls Devin API every 30s to track session status, PR creation, and completion
- **Close-the-loop**: Detects PR merges (via webhook or polling) and auto-closes the originating GitHub issue
- **File-based storage**: Simple JSON file with thread-safe locking — no database required
- **Docker-ready**: Single `docker compose up` to run the full stack
- **ngrok integration**: Optional Docker service for webhook tunneling to your local machine

### Auto-Merge / Human Review
- **Confidence-based merge decisions**: Automatically merges PRs from small, successful sessions
- **Size threshold**: Configurable max session size for auto-merge (`xs`, `s`, `m`, `l`, `xl`)
- **CI awareness**: Checks GitHub CI status before merging — failed CI triggers human review
- **Merge conflict detection**: PRs with conflicts are flagged for human review
- **Label-based override**: Issues tagged `needs-review` always request human review regardless of size
- **Safety defaults**: Unknown session size defaults to human review

### Dashboard
- **Metrics cards**: Total sessions, success rate, estimated ACUs, average resolution time
- **Cost chart**: Estimated ACU consumption per session (bar chart, color-coded by status)
- **Activity feed**: Chronological feed of events (session created, PR opened, PR merged, issue closed)
- **Session table**: Filterable list with status badges, issue links, Devin session links, PR links
- **Merge-aware status badges**: Shows "auto-merged" (green) or "review requested" (amber) instead of raw API status
- **Auto-refresh**: Dashboard polls every 10 seconds

### Estimated ACU Tracking
Since the Devin API does not expose per-session billing, the orchestrator estimates ACU consumption:
```
estimated_acus = num_devin_messages × 0.22 × size_multiplier
```
Size multipliers: `xs=1.0`, `s=1.3`, `m=1.6`, `l=2.0`, `xl=2.5`

## Quick Start

### Prerequisites

- Docker and Docker Compose
- A [Devin API key](https://docs.devin.ai/api-reference/getting-started/teams-quickstart) (service user with `ManageOrgSessions` permission)
- Your Devin organization ID
- A [GitHub fine-grained token](https://github.com/settings/tokens?type=beta) with **Contents**, **Issues**, and **Pull requests** set to Read & Write, scoped to your target repo

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
GITHUB_TOKEN=ghp_your_token_here
TARGET_REPO=danagajewski/superset
```

### 2. Run with Docker

```bash
docker compose up --build
```

- **Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API docs**: http://localhost:8000/docs

### 3. Expose your machine with ngrok

GitHub webhooks need a public URL to reach your machine. The orchestrator includes an ngrok tunnel as an optional Docker service.

1. Sign up at [ngrok.com](https://ngrok.com) and copy your auth token from the [dashboard](https://dashboard.ngrok.com/get-started/your-authtoken)
2. Add it to your `.env`:
   ```env
   NGROK_AUTHTOKEN=your_token_here
   ```
3. Start the orchestrator with the tunnel:
   ```bash
   docker compose --profile tunnel up --build
   ```
4. Open http://localhost:4040 to see your ngrok dashboard — copy the public URL (e.g. `https://abc123.ngrok-free.app`)

### 4. Set up GitHub Webhook

1. Go to your target repo → **Settings** → **Webhooks** → **Add webhook**
2. **Payload URL**: `https://abc123.ngrok-free.app/webhook/github` (use your ngrok URL from step 3)
3. **Content type**: `application/json`
4. **Secret**: Same value as `GITHUB_WEBHOOK_SECRET` in your `.env`
5. **Events**: Select "Let me select individual events" → check **Issues** and **Pull requests**
6. Click **Add webhook**

> **Note:** The free ngrok plan gives you a new URL each time you restart. Update the webhook URL in GitHub if you restart the containers. For a stable URL, use an [ngrok reserved domain](https://dashboard.ngrok.com/domains) (free plan includes one).

## How It Works

### Issue → Fix → Merge → Close

1. **Issue created**: GitHub sends a webhook to the orchestrator
2. **Session started**: The orchestrator calls the Devin API to create a session with a prompt built from the issue title, body, and labels
3. **Devin works**: Devin analyzes the issue, implements a fix, and creates a PR
4. **Auto-merge evaluation**: When the session reaches a terminal state or `waiting_for_user`:
   - Checks if the issue has a `needs-review` label → human review
   - Checks if the session failed or was suspended → human review
   - Checks session size against `AUTO_MERGE_MAX_SIZE` threshold → human review if exceeded
   - Checks CI status → human review if CI failed
   - Checks for merge conflicts → human review if conflicts exist
   - If all checks pass → **auto-merge**
5. **Issue closed**: After PR merge, the orchestrator closes the GitHub issue with a comment linking the merged PR

### Human Review Path

When auto-merge is not appropriate, the orchestrator:
- Leaves a comment on the PR explaining why review is needed
- Shows "review requested" status on the dashboard
- Waits for a human to review and merge manually
- Detects the manual merge (via webhook or polling) and closes the issue

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
| `POST` | `/webhook/github` | GitHub webhook receiver (issues + pull requests) |
| `GET` | `/api/sessions` | List all tracked sessions |
| `GET` | `/api/sessions/{id}` | Get session details |
| `GET` | `/api/metrics` | Aggregated metrics |
| `GET` | `/api/health` | Health check |

## Project Structure

```
devin-orchestrator/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app with CORS and routes
│   │   ├── webhook.py          # GitHub webhook handler (issues + PRs)
│   │   ├── devin_client.py     # Devin API v3 client
│   │   ├── github_client.py    # GitHub API client (merge, close, comments)
│   │   ├── poller.py           # Background poller + auto-merge logic
│   │   ├── storage.py          # JSON file-based storage with locking
│   │   ├── models.py           # Pydantic models
│   │   └── config.py           # Settings via env vars
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main dashboard layout
│   │   ├── components/
│   │   │   ├── MetricsPanel.tsx  # Metrics cards
│   │   │   ├── SessionList.tsx   # Session table with merge-aware status
│   │   │   ├── CostChart.tsx     # ACU cost bar chart
│   │   │   └── ActivityFeed.tsx  # Event timeline
│   │   └── lib/api.ts           # API client
│   ├── nginx.conf               # Reverse proxy config
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
| `GITHUB_TOKEN` | Yes | — | GitHub fine-grained token (Contents + Issues + Pull requests: Read & Write) |
| `TARGET_REPO` | No | `danagajewski/superset` | Repository for Devin sessions |
| `POLL_INTERVAL_SECONDS` | No | `30` | Session status polling interval |
| `AUTO_MERGE_ENABLED` | No | `true` | Enable/disable auto-merge for PRs |
| `AUTO_MERGE_MAX_SIZE` | No | `s` | Max session size for auto-merge (`xs`, `s`, `m`, `l`, `xl`) |
| `NGROK_AUTHTOKEN` | For tunnel | — | ngrok auth token ([get one here](https://dashboard.ngrok.com/get-started/your-authtoken)) |

## Auto-Merge Configuration

The `AUTO_MERGE_MAX_SIZE` setting controls which sessions are eligible for auto-merge:

| Setting | Auto-merges | Requests review |
|---------|------------|-----------------|
| `xs` | Extra-small sessions only | Small and above |
| `s` (default) | Extra-small and small | Medium and above |
| `m` | Up to medium | Large and above |
| `l` | Up to large | Extra-large only |
| `xl` | All sizes | Nothing (size-based) |

Sessions will still be flagged for review regardless of size if:
- CI checks fail
- The PR has merge conflicts
- The issue has a `needs-review`, `needs review`, or `manual-review` label
- The session failed or was suspended
- Session size is unknown (insights API hasn't responded)

Set `AUTO_MERGE_ENABLED=false` to disable auto-merge entirely and always request human review.
