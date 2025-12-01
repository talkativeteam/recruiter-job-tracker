# Complete Workflow Breakdown - Step by Step

## Input
```json
{
  "client_name": "Vince Dunne",
  "client_email": "vince@dunnesearchgroup.com",
  "client_website": "https://dunnesearchgroup.com/",
  "email_sender_name": "Sid Kennedy",
  "email_sender_address": "kenne.s@talkativecrew.com",
  "max_jobs_to_scrape": 100
}
```

---

## 📋 PHASE 1: Input Validation
**File:** `execution/validate_input.py`

### Steps:
1. Check all required fields present (client_name, client_email, client_website, etc.)
2. Validate email format
3. Validate URL format
4. Check max_jobs_to_scrape is between 100-400
5. Return validated input or raise error

### Output:
```json
{
  "client_name": "Vince Dunne",
  "client_email": "vince@dunnesearchgroup.com",
  "client_website": "https://dunnesearchgroup.com/",
  "max_jobs_to_scrape": 100,
  "validated": true
}
```

---

## 🎯 PHASE 2: Deep ICP Extraction (NEW!)
**File:** `execution/extract_icp_deep.py`

### Step 2.1: Discover Relevant Pages
- Launch Playwright browser (Chromium)
- Navigate to `https://dunnesearchgroup.com/`
- Wait for page load (networkidle)
- Find all `<a>` links on page
- Search for pages matching keywords:
  - **About:** "about", "about-us", "who-we-are", "our-story"
  - **Services:** "services", "what-we-do", "solutions", "offerings"
  - **Sectors:** "sectors", "industries", "specialisms", "expertise"
  - **Team:** "team", "our-team", "people", "leadership"

**Example Output:**
```python
{
  "homepage": "https://dunnesearchgroup.com/",
  "about": "https://dunnesearchgroup.com/about",
  "services": "https://dunnesearchgroup.com/services",
  "sectors": "https://dunnesearchgroup.com/sectors"
}
```

### Step 2.2: Scrape All Pages with Playwright
For each page:
1. Launch new Playwright page
2. Navigate to URL (90s timeout)
3. Wait for networkidle
4. Get full HTML content with `page.content()`
5. Parse with BeautifulSoup
6. Remove `<script>`, `<style>`, `<nav>`, `<footer>`, `<header>` tags
7. Convert to Markdown with `markdownify`
8. Store content with page type label

**Example:**
```
--- HOMEPAGE PAGE ---

Dunne Search Group
Executive Search for Biotech & Pharmaceutical Companies
We place Sales Directors, Marketing Managers, and Business Development...

--- ABOUT PAGE ---

About Dunne Search Group
Founded in 2015, we specialize in placing commercial leadership...
Our focus: Biotech, Pharmaceutical, Healthcare Technology sectors...

--- SERVICES PAGE ---

Our Services
- Sales Leadership Recruiting
- Marketing Executive Search
- Business Development Placement
...
```

### Step 2.3: AI Analysis (GPT-4o-mini)
Send combined content (max 20,000 chars) to OpenAI with prompt:

```
You are an expert at analyzing recruiter websites...

Analyze these multiple pages and extract:
1. Industries (e.g., "Biotech", "Pharmaceutical")
2. Company sizes (e.g., "10-100 employees")
3. Geographies (countries, states, cities)
4. Specific roles (e.g., "Sales Director", "Marketing Manager")
5. Boolean keywords
6. Primary country
7. LinkedIn geoId

[HOMEPAGE content]
[ABOUT content]
[SERVICES content]
[SECTORS content]

Return JSON only...
```

### Step 2.4: Parse AI Response
**Output:**
```json
{
  "industries": ["Biotech", "Pharmaceutical", "Healthcare Technology"],
  "company_sizes": ["10-100 employees", "100-500 employees"],
  "geographies": ["United States", "California"],
  "roles_filled": [
    "Sales Director",
    "Marketing Manager",
    "Business Development Manager",
    "VP of Sales",
    "Head of Sales"
  ],
  "boolean_keywords": [
    "Sales Director",
    "Sales Manager",
    "Marketing Manager",
    "Business Development Manager",
    "VP Sales",
    "Head of Sales"
  ],
  "primary_country": "United States",
  "linkedin_geo_id": "103644278"
}
```

---

## 🔍 PHASE 3: Generate Boolean Search
**File:** `execution/orchestrator.py` (calls AI prompt)

### Steps:
1. Take ICP data from Phase 2
2. Format prompt for OpenAI:
   ```
   Generate a Boolean search for LinkedIn...
   ICP: Biotech, Pharmaceutical companies
   Roles: Sales Director, Marketing Manager, Business Development Manager
   ```
3. AI generates Boolean string
4. URL encode for LinkedIn

**Output:**
```
Boolean: ("Sales Director" OR "Sales Manager" OR "Marketing Manager" OR "Business Development Manager" OR "VP Sales" OR "Head of Sales")

LinkedIn URL: https://www.linkedin.com/jobs/search/?keywords=%22Sales+Director%22+OR+%22Sales+Manager%22+OR+%22Marketing+Manager%22+OR+%22Business+Development+Manager%22+OR+%22VP+Sales%22+OR+%22Head+of+Sales%22&geoId=103644278&f_TPR=r86400
```

---

## 📊 PHASE 4: LinkedIn Job Scraping (with Exa Fallback)
**File:** `execution/call_apify_linkedin_scraper.py` + `execution/call_exa_api.py`

### Step 4.1: Try LinkedIn First (24 hours)
1. Send LinkedIn URL to Apify Actor
2. Request 100 jobs from past 24 hours
3. Wait for scraping to complete
4. Receive job results

**Example Result:**
```json
{
  "jobs_scraped": 100,
  "unique_companies": 41
}
```

### Step 4.2: Check Threshold
```python
if len(jobs_scraped) < 10:  # Too niche!
    # Trigger Exa fallback
```

### Step 4.3: Exa Fallback (if < 10 jobs)
**File:** `execution/call_exa_api.py`

#### 4.3.1: Build Natural Language Search Criteria
```python
# Calculate date range (last 7 days)
date_start = "november 24, 2025"
date_end = "december 01, 2025"

# Build criteria
criteria = "company in biotech or pharmaceutical or healthcare technology sector, company hiring sales director or marketing manager or business development manager, company has under 100 employees, posted about hiring between november 24, 2025 and december 01, 2025, company is not a recruitment or staffing firm"
```

#### 4.3.2: Call Exa API
```python
from exa_py import Exa

exa_client = Exa(api_key=EXA_API_KEY)
results = exa_client.search_and_contents(
    query=criteria,
    num_results=20,
    text={"max_characters": 2000}
)
```

#### 4.3.3: Parse Exa Results
For each result:
1. Extract domain from URL
2. Filter out job boards (linkedin, indeed, glassdoor, etc.)
3. Filter out large companies (google, apple, microsoft, etc.)
4. Extract company name from domain
5. Check if URL contains career page indicators
6. Return company object:

```json
{
  "name": "Sepax Bio",
  "company_url": "https://sepaxbio.com",
  "careers_url": "https://sepaxbio.com/careers/",
  "description": "Biotech company specializing in...",
  "jobs": [],
  "source": "exa"
}
```

**Exa Output:**
```
Found 19 companies:
- Montanamolecular
- Sepax Bio
- Grovebiopharma
- Andelynbio
- Orchestrabiomed
- Kalocyte
- Xerispharma
- Enliventherapeutics
- 35pharma
- Conceptrabio
... (9 more)
```

#### 4.3.4: Scrape Career Pages
**File:** `execution/extract_jobs_from_website.py`

For each company:

**A. Try HTTP First (Fast & Free)**
```python
response = requests.get(careers_url, timeout=10)
html_content = response.text
soup = BeautifulSoup(html_content, 'html.parser')
# Remove scripts, styles, nav, footer
markdown_content = markdownify(soup)
```

**B. If HTTP Fails → Try Playwright**
```python
# HTTP got 404 or timeout
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(careers_url, timeout=90000)
    page.wait_for_load_state("networkidle")
    html_content = page.content()
    # Parse and convert to markdown
    markdown_content = clean_and_convert(html_content)
    browser.close()
```

**Example:** 35pharma
- HTTP: `404 Not Found` ❌
- Playwright: `Success - 2880 characters` ✅

#### 4.3.5: Extract Jobs with AI (GPT-4o-mini)
**File:** `execution/extract_jobs_from_website.py`

For each scraped page:

```python
prompt = f"""You are analyzing the careers/jobs page of {company_name}.

Extract all job listings from the following content. For each job, extract:
- job_title: The job title/position name
- description: Brief description (2-3 sentences)
- job_url: Link to apply or view details (if available)
- location: Job location (if mentioned)

Return a JSON array of jobs. If no jobs are found, return an empty array.

Website Content:
{markdown_content[:8000]}

Return format:
{{
  "jobs": [
    {{
      "job_title": "Senior Software Engineer",
      "description": "Build scalable systems...",
      "job_url": "https://...",
      "location": "Remote"
    }}
  ]
}}
"""

response = openai.call_with_retry(prompt, model="gpt-4o-mini")
jobs = json.loads(response)["jobs"]
```

**Example Output:**
```json
{
  "name": "Oncofirmdiagnostics",
  "careers_url": "https://oncofirmdiagnostics.com/careers",
  "jobs": [
    {
      "job_title": "Sales Director, East Coast",
      "description": "Lead sales team for molecular diagnostics products...",
      "job_url": "https://oncofirmdiagnostics.com/careers/sales-director",
      "location": "Boston, MA"
    },
    {
      "job_title": "Marketing Manager",
      "description": "Develop marketing strategies for new product launches...",
      "job_url": "https://oncofirmdiagnostics.com/careers/marketing-manager",
      "location": "Remote"
    }
  ],
  "job_count": 2
}
```

#### 4.3.6: Validate Hiring Activity
```python
companies_hiring = []
companies_not_hiring = []

for company in companies:
    real_jobs = [j for j in company["jobs"] if len(j["job_title"]) > 5]
    if len(real_jobs) > 0:
        companies_hiring.append(company)
    else:
        companies_not_hiring.append(company)
```

**Output:**
```
Companies hiring: 8
Companies not hiring: 11
```

#### 4.3.7: Convert to LinkedIn Format
**File:** `execution/orchestrator.py`

```python
linkedin_format_jobs = []

for company in companies_hiring:
    for job in company["jobs"]:
        linkedin_job = {
            "companyName": company["name"],
            "companyDescription": company["description"],
            "companyWebsite": company["company_url"],
            "title": job["job_title"],
            "description": job["description"],
            "descriptionText": job["description"],
            "link": job["job_url"],
            "location": job["location"],
            "source": "exa_fallback"
        }
        linkedin_format_jobs.append(linkedin_job)

# Replace original jobs_scraped with Exa results
self.jobs_scraped = linkedin_format_jobs
```

**Final Output:**
```
Total jobs: 19 (from 8 companies)
Source: exa_fallback
```

---

## 🏢 PHASE 5: Extract Unique Companies
**File:** `execution/orchestrator.py`

### Steps:
1. Loop through all scraped jobs
2. Extract unique company names
3. Group jobs by company
4. Count jobs per company
5. Return list of unique companies with their jobs

**Example:**
```json
[
  {
    "company_name": "Oncofirmdiagnostics",
    "company_website": "https://oncofirmdiagnostics.com",
    "jobs": [
      {"title": "Sales Director", "link": "..."},
      {"title": "Marketing Manager", "link": "..."}
    ],
    "job_count": 2
  },
  {
    "company_name": "Sepax Bio",
    "company_website": "https://sepaxbio.com",
    "jobs": [
      {"title": "Business Development Manager", "link": "..."}
    ],
    "job_count": 1
  }
]
```

**Output:**
```
Found 8 unique companies (19 total jobs)
```

---

## 🔎 PHASE 6: Validate Direct Hirers
**File:** `execution/filter_companies.py`

### Steps:
1. For each company, check company website and description
2. Look for recruiter/staffing keywords:
   - "recruiting", "staffing", "talent acquisition"
   - "headhunter", "executive search"
   - "placement", "recruitment agency"
3. Filter out any companies matching these patterns
4. Return only direct hiring companies

**Example:**
```
Input: 8 companies
Filtered: 0 recruiters removed
Output: 8 direct hirers
```

---

## ⭐ PHASE 7: Prioritize Companies
**File:** `execution/prioritize_companies.py`

### Steps:
1. Calculate priority score for each company based on:
   - **Multiple roles** (2+ jobs = higher score)
   - **Role alignment** with ICP (Sales/Marketing roles)
   - **Company size match** (10-100 employees preferred)
   - **Industry match** (Biotech/Pharma)
   
2. Score calculation:
   ```python
   score = 0
   score += job_count * 10  # More jobs = better
   score += roles_match_count * 5  # Roles match ICP
   score += industry_match * 3  # Industry match
   score += size_match * 2  # Size match
   ```

3. Sort companies by score (highest first)
4. Select top 4 companies

**Example Output:**
```json
[
  {
    "company_name": "Oncofirmdiagnostics",
    "priority_score": 47,
    "job_count": 2,
    "reason": "Multiple roles, perfect industry match"
  },
  {
    "company_name": "Dcndx",
    "priority_score": 38,
    "job_count": 1,
    "reason": "Strong industry match, target size"
  },
  {
    "company_name": "Sepax Bio",
    "priority_score": 35,
    "job_count": 1,
    "reason": "Perfect role alignment"
  },
  {
    "company_name": "Grovebiopharma",
    "priority_score": 32,
    "job_count": 1,
    "reason": "Biotech sector match"
  }
]
```

---

## 🧠 PHASE 8: Enrich Company Intelligence
**File:** `execution/enrich_company_intel.py`

### For each of the top 4 companies:

#### Step 8.1: Scrape About Page
```python
# Try multiple URL patterns
urls_to_try = [
    f"{company_website}/about",
    f"{company_website}/about-us",
    f"{company_website}/"
]

for url in urls_to_try:
    success, content = scraper.scrape_http(url)
    if success:
        break
```

#### Step 8.2: AI Analysis (GPT-4o-mini)
```python
prompt = f"""Analyze this company website and extract:

1. What they do (1-2 sentences)
2. Key products/services
3. Recent news/developments
4. Company culture/values
5. Why they're hiring

Company: {company_name}
Website Content:
{about_page_content[:5000]}

Return JSON with insights.
"""

response = openai.call_with_retry(prompt)
intelligence = json.loads(response)
```

**Example Output:**
```json
{
  "company_name": "Oncofirmdiagnostics",
  "what_they_do": "Develops molecular diagnostic tests for early cancer detection",
  "products": ["OncoTest™", "BioMarker Panel"],
  "recent_news": "Raised $15M Series A, expanding commercial team",
  "culture": "Fast-paced biotech startup, mission-driven",
  "hiring_context": "Scaling sales team for new product launch"
}
```

---

## 🎯 PHASE 9: Find Decision Makers
**File:** `execution/find_contact_person.py`

### For each company:

#### Step 9.1: Determine Target Role
Based on company size and job seniority:

```python
if company_size < 20:
    target_role = "Founder" or "CEO" or "Co-Founder"
elif company_size < 50 and job_is_senior:
    target_role = "CTO" or "VP Engineering"
elif company_size < 50 and job_is_junior:
    target_role = "Engineering Manager" or "Head of IT"
elif company_size < 100 and job_is_senior:
    target_role = "VP of [Department]" or "Director of [Department]"
else:
    target_role = "[Department] Manager"
```

**Example for Oncofirmdiagnostics:**
- Size: ~30 employees
- Job: Sales Director (senior role)
- Target: **VP of Sales** or **Head of Sales** or **Chief Commercial Officer**

#### Step 9.2: Search with Exa
```python
query = f"VP of Sales at Oncofirmdiagnostics OR Head of Sales at Oncofirmdiagnostics OR Chief Commercial Officer at Oncofirmdiagnostics"

results = exa.search(query, num_results=5)
```

#### Step 9.3: Parse Results
```python
for result in results:
    # Extract name from LinkedIn profile or company page
    if "linkedin.com/in/" in result.url:
        # Parse LinkedIn profile
        name = extract_name_from_linkedin(result)
        title = extract_title_from_linkedin(result)
    else:
        # Parse from company page
        name = extract_name_from_text(result.text)
        title = extract_title_from_text(result.text)
```

**Example Output:**
```json
{
  "company_name": "Oncofirmdiagnostics",
  "decision_maker": {
    "name": "Sarah Martinez",
    "title": "VP of Sales",
    "linkedin": "https://linkedin.com/in/sarah-martinez-biotech",
    "confidence": "high"
  },
  "alternatives": [
    {
      "name": "John Chen",
      "title": "Head of Commercial Operations"
    }
  ]
}
```

---

## 📧 PHASE 10: Generate Outreach Email
**File:** `execution/generate_outreach_email.py`

### Step 10.1: Format Company Data
```python
email_data = []

for company in top_4_companies:
    company_section = f"""
{company_name} — {main_role_title}
{what_they_do}
{why_hiring}
Website: {company_website}
Job: {job_link}
"""
    email_data.append(company_section)
```

### Step 10.2: AI Email Generation (GPT-4o-mini)
```python
prompt = f"""You are writing to a recruiter about companies actively hiring.

Recruiter: {recruiter_name}
Recruiter specializes in: {industries} - {roles}

EXACT FORMAT:

{recruiter_name},

Here's some stuff we've dug up for you. Right in your wheelhouse I reckon.

1. {company_1_data}

2. {company_2_data}

3. {company_3_data}

4. {company_4_data}

Shout out if you want the contact info for any of these folks. We send this type of thing over to recruiters all the time with the decision makers info and phone number.

Cheers,
{sender_name}
"""

email = openai.call_with_retry(prompt)
```

### Step 10.3: Final Email Output
```
Vince,

Here's some stuff we've dug up for you. Right in your wheelhouse I reckon.

1. Oncofirmdiagnostics — Sales Director, East Coast
Develops molecular diagnostic tests for early cancer detection. Recently raised $15M Series A and expanding their commercial team across the US.
Looking for an experienced sales leader to build relationships with oncology labs and hospital systems. Ideal candidate has 7+ years in diagnostic sales.
Website: https://oncofirmdiagnostics.com
Job: https://oncofirmdiagnostics.com/careers/sales-director

2. Sepax Bio — Business Development Manager
Biotech company specializing in cell separation technologies for research and therapeutics. Growing fast with new partnerships in the works.
Seeking a BD professional to identify and close deals with pharma and biotech companies. Experience in life sciences required.
Website: https://sepaxbio.com
Job: https://sepaxbio.com/careers/bd-manager

3. Grovebiopharma — Marketing Manager
Pharmaceutical company focused on rare disease treatments. Just launched a new product line and need marketing support.
Looking for a marketing manager to lead product positioning, create sales materials, and manage digital campaigns.
Website: https://grovebiopharma.com
Job: https://grovebiopharma.com/careers/marketing-manager

4. Dcndx — Sales Executive
Diagnostic testing company for precision medicine. Expanding into new markets and building their sales organization.
Hiring multiple sales reps to sell molecular testing services to physicians and labs across California.
Website: https://dcndx.com
Job: https://dcndx.com/careers/sales-executive

Shout out if you want the contact info for any of these folks. We send this type of thing over to recruiters all the time with the decision makers info and phone number.

Cheers,
Sid Kennedy
```

---

## 🚀 PHASE 11: Send Webhook Response
**File:** `execution/send_webhook_response.py`

### Step 11.1: Package Results
```json
{
  "run_id": "run_12345",
  "status": "success",
  "statistics": {
    "total_jobs_scraped": 19,
    "companies_found": 8,
    "companies_validated": 8,
    "final_companies_selected": 4,
    "data_source": "exa_fallback",
    "total_cost": "$0.15"
  },
  "client": {
    "name": "Vince Dunne",
    "email": "vince@dunnesearchgroup.com"
  },
  "results": {
    "email_body": "[full email text]",
    "companies": [
      {
        "company_name": "Oncofirmdiagnostics",
        "jobs": [...],
        "decision_maker": {...}
      }
    ]
  }
}
```

### Step 11.2: Send to Webhook
```python
if callback_webhook_url:
    response = requests.post(
        callback_webhook_url,
        json=webhook_payload,
        headers={"Content-Type": "application/json"}
    )
```

### Step 11.3: Log to Supabase
```python
supabase.table("agent_logs").insert({
    "run_id": run_id,
    "agent_name": "recruiter_job_tracker",
    "run_status": "success",
    "cost_of_run": "$0.15",
    "client_name": "Vince Dunne",
    "companies_found": 8,
    "companies_validated": 8,
    "final_companies_selected": 4,
    "phase": "complete"
}).execute()
```

---

## 📊 FINAL OUTPUT

### Console Summary:
```
================================================================================
✅ PROCESSING COMPLETE
================================================================================

📊 Statistics:
  total_jobs_scraped: 19
  companies_found: 8
  companies_validated: 8
  final_companies_selected: 4
  data_source: exa_fallback
  total_cost: $0.15

📧 Email Preview:

Vince,

Here's some stuff we've dug up for you. Right in your wheelhouse I reckon.

1. Oncofirmdiagnostics — Sales Director, East Coast
[...]

💰 Total Cost: $0.15

✅ Full result saved to: .tmp/local_test_output.json
```

### Cost Breakdown:
```
OpenAI API Calls:
- ICP Extraction: $0.02 (710 tokens)
- Job Extraction (5x): $0.08 (4520 tokens total)
- Company Intelligence (4x): $0.03 (1500 tokens)
- Email Generation: $0.01 (500 tokens)

Exa API:
- Company Search: $0.01 (20 results)
- Decision Maker Search (4x): $0.00 (20 results)

Total: $0.15
```

---

## 🎯 KEY DIFFERENCES: Exa Fallback vs LinkedIn

| Aspect | LinkedIn Path | Exa Fallback Path |
|--------|--------------|-------------------|
| **Trigger** | Default (always tried first) | Only if LinkedIn < 10 jobs |
| **Data Source** | LinkedIn job postings | Company career pages |
| **Scraping Method** | Apify Actor | HTTP → Playwright |
| **Company Size** | Any size | < 100 employees (filtered) |
| **Job Extraction** | Pre-structured from LinkedIn | AI extraction from HTML |
| **Recency** | 24 hours or 7 days | Posted about hiring in last 7 days |
| **Cost** | ~$5 per run | ~$0.15 per run |
| **Speed** | 2-3 minutes | 3-5 minutes |
| **Best For** | Broad ICPs (IT, Finance, etc.) | Niche ICPs (Biotech, Quantum, etc.) |

---

## 🔄 ERROR HANDLING & FALLBACKS

### Layer 1: ICP Extraction
```
Playwright Multi-Page ❌
  ↓
Playwright Homepage ❌
  ↓
HTTP Scraping ✅
```

### Layer 2: Job Scraping
```
LinkedIn (24h) ❌ (< 10 jobs)
  ↓
LinkedIn (7d) ❌ (< 10 jobs)
  ↓
Exa Fallback ✅
```

### Layer 3: Career Page Scraping
```
HTTP Request ❌
  ↓
Playwright ❌
  ↓
Bright Data (not implemented) ❌
  ↓
Skip company
```

### Layer 4: AI Extraction
```
GPT-4o-mini (attempt 1) ❌
  ↓
GPT-4o-mini (attempt 2) ❌
  ↓
GPT-4o-mini (attempt 3) ✅
```

---

## ✅ COMPLETE SUCCESS PATH

```
Input Validation ✅
  ↓
Deep ICP Extraction (Playwright Multi-Page) ✅
  ↓
Boolean Search Generation ✅
  ↓
LinkedIn Scraping ❌ (0 jobs - niche ICP)
  ↓
Exa Company Discovery ✅ (19 companies found)
  ↓
HTTP/Playwright Career Page Scraping ✅ (8 with jobs)
  ↓
AI Job Extraction ✅ (19 jobs total)
  ↓
Hiring Validation ✅ (8 companies hiring)
  ↓
Format Conversion ✅ (LinkedIn format)
  ↓
Extract Unique Companies ✅ (8 companies)
  ↓
Filter Direct Hirers ✅ (8 direct hirers)
  ↓
Prioritize Companies ✅ (scored and sorted)
  ↓
Select Top 4 ✅
  ↓
Enrich Company Intelligence ✅ (about pages scraped)
  ↓
Find Decision Makers ✅ (Exa search)
  ↓
Generate Email ✅ (GPT-4o-mini)
  ↓
Send Webhook + Log ✅
  ↓
COMPLETE ✅
```

---

## 🎓 SUMMARY

This workflow now has **two complete paths**:

1. **LinkedIn Path** (default): Fast, expensive, works for broad ICPs
2. **Exa Fallback Path** (automatic): Slower, cheaper, works for niche ICPs

The system **automatically chooses** the right path based on LinkedIn results. If LinkedIn finds < 10 jobs (indicating a niche ICP), it seamlessly switches to Exa, scrapes company career pages with Playwright, extracts jobs with AI, and continues the rest of the pipeline normally.

**Key Innovation:** Deep multi-page ICP extraction with Playwright ensures the Exa fallback gets accurate search criteria (e.g., "Biotech + Sales Director" instead of "Healthcare + Recruiter"), resulting in highly relevant company matches.
