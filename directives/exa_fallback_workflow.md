# Exa Fallback Workflow - Niche ICP Handler

## Purpose

When LinkedIn returns insufficient jobs (< 10 jobs), it indicates the ICP is too niche for LinkedIn's public job listings. This directive activates an alternative workflow using Exa to find companies directly and scrape their career pages.

## When This Activates

**Triggers:**
- LinkedIn returns < 10 jobs after trying both 24 hours AND 7 days
- Indicates recruiter specializes in highly niche roles or industries
- Examples: Quantum computing, rare medical specialties, emerging tech sectors

## Why This Approach Works

**Problem with LinkedIn for Niche ICPs:**
- LinkedIn public job search requires volume
- Niche roles often posted on company sites first
- Boolean search too specific → no results
- Boolean search too broad → irrelevant results

**Exa Fallback Solution:**
- Find companies directly via semantic search
- Scrape career pages for actual job listings
- Validate hiring activity in real-time
- More accurate for specialized roles

## Phase 4B: Exa Fallback Flow

### Step 1: Detect Insufficient LinkedIn Results
```python
if len(self.jobs_scraped) < 10:
    print("🔄 ICP TOO NICHE: Activating Exa fallback...")
```

### Step 2: Find Companies via Exa
**Tool**: `execution/call_exa_api.py` - `ExaCompanyFinder`

**Process:**
- Build semantic search query from ICP data
- Focus on finding career pages of relevant companies
- Target 30 companies (to filter down to top 4)

**Exa Query Format:**
```
"companies hiring {roles} in {industries} - careers page"
```

**Example:**
```
Input ICP:
{
  "roles": ["Quantum Software Engineer", "Quantum Research Scientist"],
  "industries": ["Quantum Computing", "Advanced Physics"]
}

Exa Query:
"companies hiring Quantum Software Engineer or Quantum Research Scientist 
in Quantum Computing or Advanced Physics - careers page"
```

**Output**: 
- Array of companies with career page URLs
- Company name, description, domain extracted

### Step 3: Extract Jobs from Career Pages
**Tool**: `execution/extract_jobs_from_website.py` - `JobExtractor`

**Process:**
- For each company, scrape their career page
- Use AI (GPT-4o-mini) to extract job listings
- Parse: job title, description, URL, location

**Scraping Priority:**
1. Try HTTP scraper (fast, cheap)
2. Fallback to Playwright if needed (JS-rendered)
3. Skip if scraping fails (move to next company)

**AI Extraction Prompt:**
```
You are analyzing the careers/jobs page of {company_name}.

Extract all job listings from the following content. For each job, extract:
- job_title: The job title/position name
- description: Brief description (2-3 sentences)
- job_url: Link to apply or view details
- location: Job location

Return JSON array of jobs. Empty array if no jobs found.
```

### Step 4: Validate Hiring Activity
**Tool**: `execution/extract_jobs_from_website.py` - `validate_hiring_activity()`

**Validation Rules:**
- Company must have ≥ 1 real job posting
- Job title must be > 5 characters (filter placeholders)
- Job description must exist

**Output:**
- `companies_hiring`: Companies with active job listings
- `companies_not_hiring`: Companies with no jobs or placeholder content

### Step 5: Convert to Standard Format
Transform Exa results to LinkedIn format for pipeline consistency:

```python
linkedin_format_job = {
    "companyName": company["name"],
    "companyDescription": company.get("description", ""),
    "companyWebsite": company.get("company_url", ""),
    "title": job.get("job_title", ""),
    "description": job.get("description", ""),
    "descriptionText": job.get("description", ""),
    "link": job.get("job_url", ""),
    "location": job.get("location", "Remote"),
    "source": "exa_fallback"
}
```

### Step 6: Continue with Normal Pipeline
- Pipeline proceeds to Phase 5 (Extract Companies)
- No changes needed - same format as LinkedIn
- `source: "exa_fallback"` tag tracks data origin

## Success Criteria

**Minimum Requirements:**
- Find ≥ 4 companies actively hiring
- Each company has ≥ 1 real job posting
- Jobs match recruiter ICP

**Failure Conditions:**
- Exa finds 0 companies
- No companies are actively hiring
- All career pages fail to scrape

If fallback fails:
```python
raise Exception("No jobs found via LinkedIn or Exa fallback")
```

## Cost Considerations

**Exa Fallback Costs:**
- Exa search: ~$0.001 per search
- OpenAI job extraction: ~$0.002 per company
- Website scraping: Free (HTTP) or minimal (Playwright)

**Total per run:** ~$0.06-0.10 (vs $0.05 LinkedIn only)

**Tradeoff:** Slightly higher cost for better accuracy on niche ICPs

## Logging & Tracking

Update stats with fallback indicator:
```python
self.stats["data_source"] = "exa_fallback"
self.stats["total_jobs_scraped"] = len(self.jobs_scraped)
```

Supabase log:
```python
{
  "phase": "scraping_linkedin_jobs_exa_fallback",
  "data_source": "exa_fallback",
  "companies_found": 15,
  "jobs_extracted": 42
}
```

## Example Flow

### Niche ICP Input:
```json
{
  "client_name": "Dr. Sarah Chen",
  "client_email": "sarah@quantumtalent.com",
  "client_website": "https://quantumtalent.com",
  "roles": ["Quantum Software Engineer"],
  "industries": ["Quantum Computing"]
}
```

### LinkedIn Attempt:
```
🔄 Attempt 1: LinkedIn 24h → 3 jobs
🔄 Attempt 2: LinkedIn 7d → 5 jobs
⚠️ ICP TOO NICHE: Only 5 jobs found
```

### Exa Fallback:
```
🌐 Activating Exa fallback...
✅ Exa found 24 companies
🔍 Extracting jobs from IonQ...
✅ Found 4 jobs at IonQ
🔍 Extracting jobs from Rigetti Computing...
✅ Found 3 jobs at Rigetti Computing
...
✅ Exa fallback: 12 companies actively hiring, 38 jobs total
```

### Result:
```
✅ Total: 38 jobs scraped (source: exa_fallback)
📊 Proceeding to Phase 5: Extract Companies
```

## Edge Cases

### All Companies Fail to Scrape
- Move to next company immediately
- Log each failure: "Failed to scrape {company}"
- Continue until 4 valid companies found

### Jobs Are Too Generic
- AI filter extracts only relevant jobs
- Validates job titles match ICP roles
- Skips "General Application" or "Various Roles"

### Career Page Has No Job Listings
- Mark as `companies_not_hiring`
- Exclude from final results
- Continue searching other companies

### Exa Returns Non-Career Pages
- Validate URL contains career indicators
- Check content for hiring keywords
- Skip non-career pages automatically

## Integration Points

**Calls These Modules:**
1. `execution/call_exa_api.py` - Company discovery
2. `execution/extract_jobs_from_website.py` - Job extraction
3. `execution/scrape_website.py` - Website content
4. `execution/call_openai.py` - AI extraction

**Called By:**
- `execution/orchestrator.py` - Phase 4 (conditional)

**No Changes Required:**
- Phase 5-10 remain identical
- Same company/job data structure
- Transparent to downstream pipeline

## Testing

Test with niche ICP:
```json
{
  "client_name": "Test User",
  "client_website": "https://test.com",
  "roles": ["Quantum Cryptographer", "Topological Data Analyst"],
  "industries": ["Quantum Information Theory"]
}
```

Expected:
- LinkedIn fails (< 10 jobs)
- Exa activates
- Returns 4 companies with quantum/crypto roles
