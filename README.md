# Recruiter ICP Job Tracker & Outreach Generator

Enterprise-grade AI agent system for **Talkative** - helping recruiters land more clients by tracking open job roles and generating personalized outreach.

## Overview

This system takes a recruiter's information (name, email, website) and:
1. ✅ Analyzes their Ideal Client Profile (ICP)
2. ✅ Identifies roles they fill
3. ✅ Generates precise LinkedIn Boolean searches
4. ✅ Scrapes job postings from LinkedIn
5. ✅ Validates companies are direct hirers (NOT recruiters)
6. ✅ Prioritizes multi-role companies
7. ✅ Finds decision-makers for each company
8. ✅ Generates peer-to-peer outreach emails

## Architecture

**3-Layer System**:
- **Layer 1 (Directives)**: SOPs in `directives/` - natural language instructions
- **Layer 2 (Orchestration)**: AI agent routes between directives and execution tools
- **Layer 3 (Execution)**: Deterministic Python scripts in `execution/`

## Quick Start

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers (for web scraping)
playwright install
```

### 2. Set Up Environment Variables

Copy `.env.template` to `.env` and fill in your API keys:

```bash
cp .env.template .env
# Edit .env with your API keys
```

Required API keys:
- **OpenAI API Key** (for AI analysis)
- **Apify API Key** (for LinkedIn scraping)
- **Exa API Key** (for decision-maker search)
- **Supabase URL & Key** (for logging)

Optional:
- **Bright Data API Key** (last resort scraping)

### 3. Set Up Supabase

Create a Supabase table called `agent_logs` with this schema:

```sql
CREATE TABLE agent_logs (
  id BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMP DEFAULT NOW(),
  agent_name TEXT,
  run_id TEXT UNIQUE,
  run_status TEXT,
  cost_of_run TEXT,
  client_name TEXT,
  client_email TEXT,
  phase TEXT,
  companies_found INT,
  companies_validated INT,
  final_companies_selected INT,
  error_message TEXT
);
```

### 4. Run the System

**Validate Input**:
```bash
python execution/validate_input.py \
  --input input.json \
  --output .tmp/validated_input.json
```

**Example `input.json`**:
```json
{
  "client_name": "John Doe",
  "client_email": "john@recruitingfirm.com",
  "client_website": "https://recruitingfirm.com",
  "max_jobs_to_scrape": 50,
  "callback_webhook_url": "https://optional-webhook.com/results"
}
```

**Run Full Workflow** (AI agent orchestrates all phases):
```bash
# The AI agent will read directives and execute each phase automatically
# See directives/master_workflow.md for complete phase flow
```

## Phase-by-Phase Execution

### Phase 1: Scrape Recruiter Website
```bash
python execution/scrape_website.py \
  --url "https://recruitingfirm.com" \
  --output .tmp/recruiter_website.md \
  --run-id <run-id>
```

### Phase 2: Identify ICP
```bash
python execution/call_openai.py \
  --prompt-type identify_icp \
  --input .tmp/recruiter_website.md \
  --output .tmp/recruiter_icp.json \
  --run-id <run-id>
```

### Phase 3: Generate Boolean Search
```bash
python execution/generate_linkedin_url.py \
  --icp .tmp/recruiter_icp.json \
  --output .tmp/linkedin_boolean_search.json \
  --run-id <run-id>
```

### Phase 4: Scrape LinkedIn Jobs
```bash
python execution/call_apify_linkedin_scraper.py \
  --url-file .tmp/linkedin_boolean_search.json \
  --output .tmp/scraped_jobs/linkedin_jobs_raw.json \
  --max-jobs 50 \
  --run-id <run-id>
```

### Phase 5: Filter Direct Hirers
```bash
python execution/filter_companies.py \
  --input .tmp/scraped_jobs/linkedin_jobs_raw.json \
  --output .tmp/filtered_companies/direct_hirers.json \
  --run-id <run-id>
```

### Phase 6 & 7: Prioritize and Select Top 4
```bash
python execution/prioritize_companies.py \
  --input .tmp/filtered_companies/direct_hirers.json \
  --icp .tmp/recruiter_icp.json \
  --output .tmp/final_output/selected_companies.json \
  --count 4 \
  --validate-icp \
  --run-id <run-id>
```

### Phase 8: Find Decision-Makers
```bash
python execution/find_contact_person.py \
  --companies .tmp/final_output/selected_companies.json \
  --output .tmp/decision_makers/contacts.json \
  --run-id <run-id>
```

### Phase 9: Generate Email
```bash
python execution/call_openai.py \
  --prompt-type generate_email \
  --companies .tmp/final_output/selected_companies.json \
  --decision-makers .tmp/decision_makers/contacts.json \
  --recruiter-name "John Doe" \
  --output .tmp/final_output/outreach_email.txt \
  --model gpt-4-turbo-preview \
  --run-id <run-id>
```

## Directory Structure

```
recruiter-icp-job-tracker/
├── directives/               # SOPs (natural language instructions)
│   ├── master_workflow.md
│   ├── scrape_recruiter_website.md
│   ├── identify_recruiter_icp.md
│   ├── generate_boolean_search.md
│   ├── scrape_linkedin_jobs.md
│   ├── filter_direct_hirers.md
│   ├── prioritize_multi_role.md
│   ├── select_top_companies.md
│   ├── find_decision_maker.md
│   └── generate_outreach_email.md
├── execution/                # Python scripts (deterministic tools)
│   ├── validate_input.py
│   ├── scrape_website.py
│   ├── call_openai.py
│   ├── generate_linkedin_url.py
│   ├── call_apify_linkedin_scraper.py
│   ├── filter_companies.py
│   ├── prioritize_companies.py
│   ├── find_contact_person.py
│   ├── send_webhook_response.py
│   └── supabase_logger.py
├── config/                   # Configuration and AI prompts
│   ├── config.py
│   ├── ai_prompts.py
│   └── cost_optimization.md
├── .tmp/                     # Temporary files (not committed)
│   ├── validated_input.json
│   ├── recruiter_website.md
│   ├── recruiter_icp.json
│   ├── linkedin_boolean_search.json
│   ├── scraped_jobs/
│   ├── filtered_companies/
│   ├── decision_makers/
│   └── final_output/
├── logs/                     # Audit logs
├── .env                      # API keys (DO NOT COMMIT)
├── .env.template             # Template for .env
├── requirements.txt          # Python dependencies
└── README.md
```

## Cost Optimization

The system prioritizes cost-effective methods:

1. **HTTP Request** (FREE) - Always try first
2. **Playwright** (FREE) - For JavaScript-heavy sites
3. **Bright Data** (PAID) - Last resort only

**AI Models**:
- **gpt-4o-mini** - For most tasks (~$0.0002 per 1K tokens)
- **gpt-4-turbo-preview** - ONLY for client-facing email (~$0.01 per 1K tokens)

**Typical Cost Per Run**: $0.25-0.35
- OpenAI: $0.15 (30-40 calls)
- Apify: $0.05 (1 run, 50 jobs)
- Exa: $0.004 (4 searches)
- Playwright: $0.00 (free)

## Key Features

### ✅ ZERO Tolerance for Misinformation
- Validates all company data
- Removes recruiters/staffing agencies
- Verifies ICP fit
- Logs all operations to Supabase

### ✅ Self-Annealing System
When errors occur:
1. AI agent reads error message
2. Fixes execution script
3. Tests fix
4. Updates directive with learnings
5. System becomes stronger

### ✅ Cost-Optimized
- HTTP before Playwright before Bright Data
- gpt-4o-mini for analysis, gpt-4-turbo-preview for emails only
- Apify's `scrapeCompany: true` eliminates extra scraping

### ✅ Enterprise-Ready
- Real-time Supabase logging
- Webhook delivery
- Comprehensive error handling
- Audit trail

## Output Format

Final output (`.tmp/final_output/results.json`):

```json
{
  "run_id": "uuid",
  "run_status": "completed",
  "cost_of_run": "$0.25 OpenAI...",
  "recruiter": {
    "name": "John Doe",
    "email": "john@recruitingfirm.com",
    "website": "https://recruitingfirm.com"
  },
  "icp": {...},
  "linkedin_search_url": "...",
  "companies_found": 50,
  "companies_validated": 23,
  "final_companies": [
    {
      "company_name": "TechCorp Inc",
      "company_website": "https://techcorp.com",
      "roles_hiring": [...],
      "decision_maker": {
        "name": "Jane Smith",
        "title": "CTO",
        "linkedin_url": "https://linkedin.com/in/janesmith"
      }
    }
    // ... 3 more companies
  ],
  "outreach_email": "Hey John...",
  "timestamp": "2025-11-29T12:34:56Z"
}
```

## Error Handling

### Network Errors
- Automatic retry with exponential backoff (3 attempts)
- Timeout handling for all API calls
- Fallback methods for scraping

### API Failures
- OpenAI: Retry on rate limits
- Apify: 2 retry attempts
- Exa: Continue without decision-maker if search fails

### Validation Failures
- <4 companies: Deliver available companies (log warning)
- 0 companies: Mark run as failed
- Missing decision-makers: Acceptable, continue

## Monitoring

All runs logged to Supabase `agent_logs` table with:
- Run status (started, running, completed, failed)
- Cost tracking per phase
- Company metrics (found, validated, selected)
- Error messages

## Development

### Adding New Phases

1. Create directive in `directives/new_phase.md`
2. Create execution script in `execution/new_script.py`
3. Update `directives/master_workflow.md`
4. Update `config/ai_prompts.py` if using AI

### Testing

```bash
# Test individual scripts
python execution/validate_input.py --input test_input.json --output .tmp/test_validated.json

# Test with sample data
# See test_data/ directory for examples
```

## Support

For issues or questions:
- Check directives for detailed instructions
- Review `config/cost_optimization.md` for cost-saving tips
- Check Supabase logs for run status

## License

Enterprise license - Talkative proprietary system.

---

**Built with the 3-layer architecture: Directives (what) → AI Agent (decision-making) → Execution (how)**
