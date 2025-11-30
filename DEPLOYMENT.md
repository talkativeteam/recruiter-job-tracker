# Recruiter Job Tracker - GitHub Repo Setup

This is a production-ready GitHub repository for the Recruiter ICP Job Tracker system, deployable to Railway.

## Overview

The system accepts HTTP requests with recruiter ICP data and outputs verified companies with outreach emails, sent to a webhook.

**Pipeline:**
1. Validate input
2. Identify recruiter ICP from website
3. Generate Boolean search
4. Scrape LinkedIn jobs (Apify)
5. Validate direct hirers
6. Validate ICP fit
7. Prioritize companies (size diversity)
8. Enrich with company intel (web scraping + AI)
9. Generate outreach email (GPT-4 turbo)
10. Send results to webhook

## Getting Started

### Local Development

```bash
# Clone repo
git clone <repo-url>
cd recruiter-job-tracker

# Create virtual env
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your API keys

# Run locally
python3 api.py
```

### Environment Variables Required

```
OPENAI_API_KEY=sk-...
APIFY_API_KEY=...
EXA_API_KEY=...
SUPABASE_URL=https://...
SUPABASE_KEY=...
WEBHOOK_URL=https://n8n.srv1125040.hstgr.cloud/webhook/2
PORT=5000
```

## API Endpoints

### POST /process

Starts the full recruitment pipeline.

**Request:**
```json
{
  "client_name": "Mat Lis",
  "client_email": "mat@hiringmaven.io",
  "client_website": "https://hiringmaven.io",
  "email_sender_name": "Ollie Heartson",
  "email_sender_address": "ol.heartson@talkativecrew.com",
  "max_jobs_to_scrape": 100,
  "recruiter_timezone": "GMT",
  "callback_webhook_url": "https://your-webhook.com"
}
```

**Response:**
```json
{
  "status": "success",
  "run_id": "uuid",
  "runtime_seconds": 412,
  "webhook_sent": true
}
```

### GET /health

Health check endpoint.

## Webhook Output

Results are automatically sent to the webhook URL with this structure:

```json
{
  "run_metadata": {
    "run_id": "uuid",
    "run_status": "completed",
    "timestamp": "2025-11-30T16:45:23Z",
    "total_runtime_seconds": 412,
    "cost_of_run": "$0.22 OpenAI, ..."
  },
  "input": { ... },
  "recruiter_icp": { ... },
  "stats": { ... },
  "verified_companies": [ ... ],
  "outreach_email": {
    "subject": "...",
    "from": "...",
    "to": "...",
    "body": "..."
  }
}
```

## Deployment to Railway

### 1. Connect GitHub Repository

```bash
# Create public GitHub repo
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/recruiter-job-tracker.git
git push -u origin main
```

### 2. Create Railway Project

1. Go to [railway.app](https://railway.app)
2. Create new project
3. Select "GitHub Repo"
4. Connect your GitHub account
5. Select this repository

### 3. Configure Environment

In Railway project settings:
- Set all required environment variables (see above)
- Set `PORT=5000` (or Railway's assigned port)

### 4. Deploy

Railway automatically deploys on git push:

```bash
# Make changes, commit, push
git add .
git commit -m "Update feature"
git push origin main

# Railway auto-deploys from main branch
```

### 5. Monitor

- View logs: Railway dashboard → Logs
- View metrics: Railway dashboard → Metrics
- Check health: `https://your-railway-url.com/health`

## Architecture

```
api.py                          # Flask HTTP server
├── /process                    # Main API endpoint
└── execution/orchestrator.py   # Pipeline coordinator
    ├── validate_input.py       # Input validation
    ├── identify_icp.py         # Website → ICP extraction
    ├── generate_boolean_search.py  # Boolean query generation
    ├── scrape_linkedin_jobs.py # Apify job scraping
    ├── validate_direct_hirer.py    # Company validation
    ├── validate_icp_fit.py     # ICP matching
    ├── prioritize_companies.py # Size diversity selection
    ├── enrich_company_intel.py # Web scraping + AI
    ├── generate_outreach_email.py  # Email generation
    └── supabase_logger.py      # Logging
```

## Cost & Performance

- **Per run:** ~$0.40 OpenAI (varies by input)
- **Runtime:** 5-10 minutes typical (Apify slower for large jobs)
- **Companies selected:** 4 (configurable in orchestrator)
- **Database:** Supabase (free tier: 500MB)

## Scaling

- Max 100 jobs per run (Apify limit) - configurable
- Handles 1-10 concurrent requests on standard Railway plan
- For higher volume: upgrade Railway plan or use task queue (Celery)

## Testing

```bash
# Local test
python3 api.py
curl -X POST http://localhost:5000/process \
  -H "Content-Type: application/json" \
  -d @sample_input.json

# Or use the orchestrator directly
python3 execution/orchestrator.py
```

## Production Checklist

- [ ] All environment variables set
- [ ] Webhook URL configured and tested
- [ ] Supabase database initialized
- [ ] API keys have correct permissions
- [ ] GitHub repo is public
- [ ] Railway project linked to GitHub
- [ ] Health endpoint responding
- [ ] Test run successful
- [ ] Webhook receiving data

## Support

For issues:
1. Check Railway logs
2. Check Supabase logs
3. Verify all API keys are set
4. Test health endpoint
5. Review error response from `/process`

## License

MIT
