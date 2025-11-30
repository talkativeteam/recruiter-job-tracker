# Filter Direct Hirers (Remove Recruiters & Large Companies)

## Purpose

Validate that companies are direct hirers (NOT recruiters/staffing agencies) and filter out companies >100 employees.

## Goal

Create a clean list of companies that:
1. Have ≤100 employees
2. Are direct hirers (not recruiters)
3. Are not duplicates

## Input

`.tmp/scraped_jobs/linkedin_jobs_raw.json` - Raw job data from Apify

## Tools

- `execution/filter_companies.py`
- `execution/call_openai.py` (for validation)
- `execution/scrape_website.py` (only if Apify data insufficient)

## Process

### Step 1: Load Raw Job Data
- Read `.tmp/scraped_jobs/linkedin_jobs_raw.json`
- Count total jobs
- Group by company name

### Step 2: Filter by Employee Count
- Remove companies with `employeeCount > 100`
- Log: "Filtered out {count} companies with >100 employees"

### Step 3: Validate Direct Hirers
For each remaining company:

#### Option A: Use Apify Data (Preferred - FREE)
- Apify provides: company name, description, industry
- Use OpenAI (gpt-4o-mini) to analyze:
  - Company name (contains "Staffing", "Recruiting", "Talent"?)
  - Company description (mentions "our clients", "staffing services"?)
  - Company industry (is it "Staffing and Recruiting"?)
  - Job description (mentions "our client is hiring"?)

#### Option B: Scrape Company Website (If Apify Data Insufficient)
- ONLY if Apify data is unclear or missing
- Use `execution/scrape_website.py` (HTTP → Playwright → Bright Data)
- Extract company "About Us" page
- Analyze with OpenAI

#### Validation Rules (OpenAI)
**Direct Hirer Indicators**:
- Company description focuses on their products/services
- Job descriptions say "we are hiring", "join our team"
- Industry is NOT staffing/recruiting
- Company name does NOT contain staffing keywords

**Recruiter/Staffing Agency Indicators**:
- Company description mentions "staffing", "recruiting", "talent acquisition"
- Job descriptions say "our client", "on behalf of", "recruiting for"
- Industry is "Staffing and Recruiting" or "Human Resources Services"
- Company name contains: "Staffing", "Recruiting", "Talent", "Personnel", "Workforce"

### Step 4: Remove Duplicates
- Group jobs by company name
- Keep all unique job listings per company
- Remove exact duplicate job postings

### Step 5: Save Filtered Results
- Write to `.tmp/filtered_companies/direct_hirers.json`
- Log: "Validated {count} direct hirers out of {total} companies"
- Update Supabase log

## Output

`.tmp/filtered_companies/direct_hirers.json`

Array of company objects:
```json
[
  {
    "company_name": "TechCorp Inc",
    "company_website": "https://techcorp.com",
    "company_description": "SaaS platform for healthcare providers",
    "company_industry": "Technology",
    "employee_count": 45,
    "company_linkedin": "https://www.linkedin.com/company/techcorp",
    "jobs": [
      {
        "job_title": "Network Engineer",
        "job_url": "https://www.linkedin.com/jobs/view/...",
        "job_description": "We are seeking a Network Engineer to...",
        "posted_at": "2025-11-29T10:00:00Z"
      }
    ],
    "is_direct_hirer": true,
    "validation_confidence": "high",
    "validation_reason": "Company focuses on SaaS products, job description uses 'we are hiring'"
  }
]
```

## AI Prompt

Uses `config/ai_prompts.py` → `PROMPT_VALIDATE_DIRECT_HIRER`

## Error Handling

### OpenAI Validation Fails
- Log: "OpenAI validation failed for {company}: {error}"
- Skip that company (conservative approach)
- Continue with others

### Insufficient Company Data
- If Apify provides no description/industry:
  - Try scraping company website
  - If scraping fails: Skip company (cannot validate)

### All Companies Filtered Out
- Log: "All companies filtered out (all recruiters or >100 employees)"
- Mark run as failed: "No valid companies found"

### <10 Companies Remain
- Log warning: "Only {count} companies remain after filtering"
- Continue (may still get 4 valid companies)

## Cost Tracking

Update Supabase `cost_of_run`:
- OpenAI calls: ~$0.10 (20-30 validation calls × $0.005 each)
- Website scraping (if needed): $0.00 (HTTP/Playwright) or $0.05 (Bright Data)
- Example: `"$0.10 OpenAI (23 validation calls), $0.05 Apify (1 run)"`

## Supabase Logging

Update log entry:
```python
{
  "phase": "filtering_direct_hirers",
  "companies_validated": 23,  # Direct hirers
  "cost_of_run": "$0.10 OpenAI (23 calls), $0.05 Apify (1 run)"
}
```

## Script Arguments

```bash
python execution/filter_companies.py \
  --input ".tmp/scraped_jobs/linkedin_jobs_raw.json" \
  --output ".tmp/filtered_companies/direct_hirers.json" \
  --max-employees 100 \
  --run-id "uuid-here"
```

## Success Criteria

- ✅ Companies >100 employees removed
- ✅ All recruiters/staffing agencies removed
- ✅ At least 4 direct hirers remain
- ✅ Duplicates removed
- ✅ Data saved to `.tmp/filtered_companies/direct_hirers.json`
- ✅ Cost tracked in Supabase

## Common Issues & Solutions

### Issue: OpenAI misclassifies company as recruiter
**Solution**: Confidence scoring. If "medium" or "low" confidence, review manually (or accept risk).

### Issue: Company name is generic (e.g., "ABC Corp")
**Solution**: Rely more on description and industry than name.

### Issue: Apify data is insufficient for validation
**Solution**: Scrape company website. If that fails, skip company.

### Issue: Too many companies filtered out (>80%)
**Solution**: May indicate Boolean search is targeting recruiter-heavy keywords. Log warning.

## Testing

Test with known companies:
- Direct hirer (e.g., "Stripe", "Airbnb") → Should pass
- Recruiter (e.g., "Robert Half", "Kforce") → Should fail
- Borderline (e.g., "Greenhouse" - recruiting software) → Depends on job description

## Optimization

### Deterministic Rules (Skip OpenAI for Obvious Cases)
- Company name contains "Staffing" or "Recruiting" → Automatic fail (save $0.005)
- Company industry is "Staffing and Recruiting" → Automatic fail
- Job description contains "our client is hiring" → Automatic fail

This can save 30-40% of OpenAI calls.

## Notes

- Apify's `scrapeCompany: true` makes this phase much cheaper
- Without it, would need to scrape 50+ company websites
- OpenAI is good at detecting subtle recruiter language
- Conservative approach: When in doubt, filter out (better to miss a recruiter than include one)
- Recruiter in final email = bad user experience = lost customer
