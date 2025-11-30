# Master Workflow - Recruiter ICP Job Tracker

## Overview

This is the main orchestration directive that coordinates all phases of the recruiter job tracking system.

## Purpose

Transform recruiter contact information (name, email, website) into a qualified list of 4 hiring companies with decision-maker contacts and a personalized outreach email.

## Success Criteria

- ✅ Input validated
- ✅ Recruiter ICP identified
- ✅ LinkedIn Boolean search generated
- ✅ Jobs scraped via Apify
- ✅ Direct hirers validated (no recruiters)
- ✅ 4 top companies selected
- ✅ Decision-makers found for each company
- ✅ Peer-to-peer email generated
- ✅ All costs tracked in Supabase
- ✅ Final output delivered

## Input

JSON with:
- `client_name` (string, required)
- `client_email` (string, required)
- `client_website` (string, required)
- `max_jobs_to_scrape` (integer, optional, default: 50, max: 100)
- `callback_webhook_url` (string, optional)

## Phase Flow

### Phase 0: Input Validation & Initialization
**Tool**: `execution/validate_input.py`
**Output**: `.tmp/validated_input.json`
**Supabase Log**: `run_status: "started"`, `phase: "initialization"`

### Phase 1: Scrape Recruiter Website
**Directive**: `directives/scrape_recruiter_website.md`
**Tool**: `execution/scrape_website.py`
**Output**: `.tmp/recruiter_website.md`
**Supabase Log**: `phase: "scraping_recruiter_website"`

### Phase 2: Identify Recruiter ICP & Roles
**Directive**: `directives/identify_recruiter_icp.md`
**Tool**: `execution/call_openai.py`
**Input**: `.tmp/recruiter_website.md`
**Output**: `.tmp/recruiter_icp.json`
**Supabase Log**: `phase: "identifying_icp"`

### Phase 3: Generate LinkedIn Boolean Search URL
**Directive**: `directives/generate_boolean_search.md`
**Tool**: `execution/generate_linkedin_url.py`
**Input**: `.tmp/recruiter_icp.json`
**Output**: `.tmp/linkedin_boolean_search.json`
**Supabase Log**: `phase: "generating_boolean_search"`

### Phase 4: Scrape LinkedIn Jobs
**Directive**: `directives/scrape_linkedin_jobs.md`
**Tool**: `execution/call_apify_linkedin_scraper.py`
**Input**: `.tmp/linkedin_boolean_search.json`
**Output**: `.tmp/scraped_jobs/linkedin_jobs_raw.json`
**Supabase Log**: `phase: "scraping_linkedin_jobs"`, `companies_found: <count>`

### Phase 5: Filter Direct Hirers
**Directive**: `directives/filter_direct_hirers.md`
**Tool**: `execution/filter_companies.py`
**Input**: `.tmp/scraped_jobs/linkedin_jobs_raw.json`
**Output**: `.tmp/filtered_companies/direct_hirers.json`
**Supabase Log**: `phase: "filtering_direct_hirers"`, `companies_validated: <count>`

### Phase 6: Prioritize Multi-Role Companies
**Directive**: `directives/prioritize_multi_role.md`
**Tool**: `execution/prioritize_companies.py`
**Input**: `.tmp/filtered_companies/direct_hirers.json`
**Output**: `.tmp/filtered_companies/prioritized_companies.json`
**Supabase Log**: `phase: "prioritizing_multi_role"`

### Phase 7: Select Top 4 Companies
**Directive**: `directives/select_top_companies.md`
**Tool**: `execution/prioritize_companies.py` (same script, filter top 4)
**Input**: `.tmp/filtered_companies/prioritized_companies.json`
**Output**: `.tmp/final_output/selected_companies.json`
**Supabase Log**: `phase: "selecting_top_companies"`, `final_companies_selected: <count>`

### Phase 8: Find Decision-Makers
**Directive**: `directives/find_decision_maker.md`
**Tool**: `execution/find_contact_person.py`
**Input**: `.tmp/final_output/selected_companies.json`
**Output**: `.tmp/decision_makers/contacts.json`
**Supabase Log**: `phase: "finding_decision_makers"`

### Phase 9: Generate Outreach Email
**Directive**: `directives/generate_outreach_email.md`
**Tool**: `execution/call_openai.py`
**Input**: `.tmp/final_output/selected_companies.json`, `.tmp/decision_makers/contacts.json`
**Output**: `.tmp/final_output/outreach_email.txt`, `.tmp/final_output/results.json`
**Supabase Log**: `phase: "generating_email"`, `run_status: "completed"`

### Phase 10: Deliver Results
**Tool**: `execution/send_webhook_response.py` (if webhook provided)
**Input**: `.tmp/final_output/results.json`
**Output**: Webhook POST or file delivery
**Supabase Log**: Update `run_status: "completed"`

## Error Handling

### Network Errors
- Retry with exponential backoff (3 attempts)
- Log detailed error to Supabase
- Continue with other companies if possible

### API Failures
- OpenAI: Retry on 429/500, fallback to alternative models
- Apify: Retry 2 times, then fail gracefully
- Exa: Log error, continue without decision-maker if critical

### Scraping Failures
- Try HTTP → Playwright → Bright Data (in order)
- If all fail, log error and skip that website
- Don't fail entire pipeline

### Validation Failures
- If <4 companies found, deliver what's available (log warning)
- If 0 companies found, mark run as "failed"

## Cost Tracking

Track all costs in Supabase `cost_of_run` field:
```
"$0.05 OpenAI (12 calls), 1 Apify run (50 jobs), 3 Playwright sessions, 4 Exa queries"
```

Update after each phase that incurs costs.

## Self-Annealing

When errors occur:
1. Read error message and stack trace
2. Fix the execution script
3. Test the fix
4. Update this directive with learnings
5. System is now stronger

## Output Schema

Final JSON structure:
```json
{
  "run_id": "<uuid>",
  "run_status": "completed",
  "cost_of_run": "$0.25 OpenAI...",
  "recruiter": {
    "name": "...",
    "email": "...",
    "website": "..."
  },
  "icp": {...},
  "linkedin_search_url": "...",
  "companies_found": 50,
  "companies_validated": 23,
  "final_companies": [...4 companies...],
  "outreach_email": "...",
  "timestamp": "2025-11-29T12:34:56Z"
}
```

## Logging

All phases log to Supabase `agent_logs` table with:
- `agent_name`: "recruiter-job-tracker"
- `run_id`: Unique UUID
- `run_status`: "started", "running", "completed", "failed"
- `phase`: Current phase name
- `cost_of_run`: Running cost total
- `companies_found`, `companies_validated`, `final_companies_selected`

## Notes

- This is an enterprise system with ZERO tolerance for misinformation
- Prioritize cost optimization (HTTP before Playwright before Bright Data)
- Use gpt-4o-mini for everything EXCEPT client-facing email
- Apify must use `scrapeCompany: true` to get company data automatically
- Decision-makers found via Exa API neural search
