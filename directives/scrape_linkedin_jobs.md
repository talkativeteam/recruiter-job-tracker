# Scrape LinkedIn Jobs Using Apify

## Purpose

Use Apify's LinkedIn Jobs Scraper to extract job listings matching the Boolean search.

## Goal

Get job data with company information automatically included.

## Input

`.tmp/linkedin_boolean_search.json` - LinkedIn URL with Boolean search

## Tool

`execution/call_apify_linkedin_scraper.py`

## Apify Actor

`curious_coder/linkedin-jobs-scraper`

**CRITICAL**: Must use `"scrapeCompany": true` to get company data automatically.

## Process

### Step 1: Load LinkedIn URL
- Read `.tmp/linkedin_boolean_search.json`
- Extract `linkedin_url`

### Step 2: Prepare Apify Input
```json
{
  "count": 50,
  "scrapeCompany": true,
  "urls": [
    "https://www.linkedin.com/jobs/search/?f_JT=F&f_TPR=r86400&geoId=103644278&keywords=..."
  ]
}
```

**CRITICAL PARAMETERS**:
- `count`: Number of jobs to scrape (from input `max_jobs_to_scrape`, default 50, max 100)
- `scrapeCompany`: **MUST BE TRUE** - This automatically scrapes company details, saving time and API calls
- `urls`: Array with single LinkedIn URL

### Step 3: Call Apify API
- Use Apify Python SDK or MCP tool
- Set timeout: 120 seconds (jobs scraping can take time)
- Wait for run to complete

### Step 4: Parse Apify Output
Apify returns array of job objects with:
```json
{
  "title": "Network Engineer",
  "company": "TechCorp Inc",
  "location": "San Francisco, CA",
  "description": "We are seeking a Network Engineer to...",
  "url": "https://www.linkedin.com/jobs/view/...",
  "postedAt": "2025-11-29T10:00:00Z",
  "companyInfo": {
    "name": "TechCorp Inc",
    "website": "https://techcorp.com",
    "description": "SaaS platform for healthcare providers",
    "industry": "Technology",
    "employeeCount": 45,
    "linkedinUrl": "https://www.linkedin.com/company/techcorp"
  }
}
```

### Step 5: Save Raw Output
- Write to `.tmp/scraped_jobs/linkedin_jobs_raw.json`
- Count total jobs scraped
- Count unique companies found
- Update Supabase log

## Output

`.tmp/scraped_jobs/linkedin_jobs_raw.json`

Array of job objects with company data included.

## Why `scrapeCompany: true` is CRITICAL

**Without it**:
- Get job data only
- Need to scrape each company website separately (50 companies = 50 scraping operations)
- Costs time, money, and API calls
- Risk of hitting rate limits

**With it**:
- Get job data + company data in ONE operation
- Company name, website, description, industry, size all included
- Saves ~50 scraping operations per run
- Dramatically reduces Phase 5 (filtering) complexity

**Always use `scrapeCompany: true`.**

## Apify Cost

- ~$0.05 per run (50 jobs)
- ~$0.10 per run (100 jobs)

## Error Handling

### Apify API Fails (429, 500, timeout)
- Retry 2 times with delay (30 seconds between retries)
- Log each attempt: "Apify retry {attempt}/2"
- If all retries fail:
  - Log: "Apify failed after 2 retries: {error}"
  - Update Supabase: `run_status: "failed"`, `phase: "scraping_linkedin_jobs"`
  - Halt execution

### Apify Returns 0 Jobs
- Log: "Apify found 0 jobs for search URL"
- Check if Boolean search is too narrow
- Mark run as failed (cannot proceed without jobs)

### Apify Returns Incomplete Data
- Log: "Some jobs missing company data"
- Continue with available data
- Note which jobs are incomplete (log warning)

### LinkedIn Blocks Apify
- Rare, but possible
- Log: "LinkedIn blocked Apify scraper"
- Mark run as failed
- Notify team to check Apify account status

## Cost Tracking

Update Supabase `cost_of_run`:
- Example: `"$0.05 Apify (1 run, 50 jobs), $0.008 OpenAI (2 calls)"`

## Supabase Logging

Update log entry:
```python
{
  "phase": "scraping_linkedin_jobs",
  "companies_found": 47,  # Unique companies
  "cost_of_run": "$0.05 Apify (1 run, 50 jobs)"
}
```

## Script Arguments

```bash
python execution/call_apify_linkedin_scraper.py \
  --url-file ".tmp/linkedin_boolean_search.json" \
  --output ".tmp/scraped_jobs/linkedin_jobs_raw.json" \
  --max-jobs 50 \
  --run-id "uuid-here"
```

## Success Criteria

- ✅ Apify run completes successfully
- ✅ At least 10 jobs scraped (if fewer, search may be too narrow)
- ✅ Company data included for all jobs (`companyInfo` present)
- ✅ Data saved to `.tmp/scraped_jobs/linkedin_jobs_raw.json`
- ✅ Cost tracked in Supabase

## Common Issues & Solutions

### Issue: Apify timeout after 120 seconds
**Solution**: This is rare. LinkedIn may be slow. Retry once.

### Issue: Some jobs missing `companyInfo`
**Solution**: Apify occasionally fails to scrape some companies. Continue with available data.

### Issue: Duplicate jobs in results
**Solution**: Normal. Will be deduplicated in Phase 6.

### Issue: Jobs from wrong geography
**Solution**: Boolean search may be wrong. Check `geoId` in URL.

## Testing

Test with known LinkedIn searches:
- Common roles (e.g., "Software Engineer") → Should return many jobs
- Rare roles (e.g., "Quantum Computing Engineer") → May return few jobs
- Invalid search → Should return 0 jobs (expected)

## Notes

- **Always use `scrapeCompany: true`** - Cannot emphasize this enough
- Apify is reliable but can be slow (30-60 seconds per run)
- LinkedIn may occasionally block (very rare with Apify)
- Raw data will be filtered in next phases
- Keep raw data (don't filter yet) for debugging
