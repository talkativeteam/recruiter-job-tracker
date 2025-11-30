# Find Decision-Maker for Each Company

## Purpose

For each of the 4 selected companies, find the best person to reach out to (full name + LinkedIn URL).

## Goal

Identify the right decision-maker based on company size and role seniority.

## Input

`.tmp/final_output/selected_companies.json` - Top 4 companies

## Tool

`execution/find_contact_person.py`

Uses **Exa API** for LinkedIn profile search.

## Process

### Step 1: Load Selected Companies
- Read `.tmp/final_output/selected_companies.json`
- Count: Should be 4 companies (or fewer if that's all available)

### Step 2: Determine Target Role for Each Company
For each company, analyze:
- Company size (employee count)
- Role seniority (junior, mid, senior, executive)
- Role type (Engineering, IT, Security, Operations, etc.)

Use OpenAI (gpt-4o-mini) or deterministic logic:

**Decision-Maker Targeting Rules**:

| Company Size | Role Type | Target Decision-Maker |
|--------------|-----------|----------------------|
| <20 employees | Any role | Founder, CEO, Co-Founder |
| 20-50 employees | Senior tech role | CTO, VP Engineering, Head of Engineering |
| 20-50 employees | Junior tech role | Head of IT, Engineering Manager, IT Manager |
| 50-100 employees | Senior role | CTO, VP of [relevant dept], Director of [relevant dept] |
| 50-100 employees | Junior role | [Department] Manager, Head of [Department] |

Example:
- Company: 35 employees
- Role: "Senior Network Engineer"
- Target: CTO, VP Engineering

### Step 3: Search for Decision-Maker Using Exa API
For each company:

```python
import exa_py

exa = exa_py.Exa(api_key=os.getenv("EXA_API_KEY"))

# Search for decision-maker on LinkedIn
result = exa.search(
    f'"{company_name}" "{target_role}" site:linkedin.com/in',
    num_results=3,
    use_autoprompt=True
)

# Extract best match
linkedin_url = result.results[0].url
name = result.results[0].title  # Usually "Name - Title at Company"
```

Exa returns LinkedIn profiles matching the query.

### Step 4: Parse Exa Results
Extract:
- Full name (e.g., "Jane Smith")
- Job title (e.g., "CTO")
- LinkedIn URL (e.g., "https://www.linkedin.com/in/janesmith")

### Step 5: Validate Result
- Ensure name is not company name
- Ensure LinkedIn URL is valid format
- Ensure result is from target company (not competitor)

If validation fails:
- Try alternative role (e.g., if CTO not found, try "VP Engineering")
- If still fails, log warning and continue without decision-maker for that company

### Step 6: Save Results
- Write to `.tmp/decision_makers/contacts.json`
- Update Supabase log

## Output

`.tmp/decision_makers/contacts.json`

Array of decision-makers:
```json
[
  {
    "company_name": "TechCorp Inc",
    "decision_maker": {
      "name": "Jane Smith",
      "title": "CTO",
      "linkedin_url": "https://www.linkedin.com/in/janesmith"
    },
    "target_role_attempted": "CTO",
    "search_confidence": "high"
  },
  {
    "company_name": "HealthTech Co",
    "decision_maker": {
      "name": "John Doe",
      "title": "VP Engineering",
      "linkedin_url": "https://www.linkedin.com/in/johndoe"
    },
    "target_role_attempted": "VP Engineering",
    "search_confidence": "high"
  }
  // ... 2 more
]
```

## Exa API Details

**Cost**: ~$0.001 per search

**Usage**:
- 4 companies = 4 searches = $0.004 total
- Occasionally need retry with alternative role = +$0.001-0.002

**Advantages**:
- Neural search (understands context)
- Pre-indexed LinkedIn profiles
- Fast (1-2 seconds per search)
- Cheap

**Limitations**:
- May not find everyone (some people have private profiles)
- May return outdated info (if person changed jobs)

## Error Handling

### Exa API Fails (429, 500, timeout)
- Retry 2 times with delay
- If still fails:
  - Log: "Exa API failed for {company}: {error}"
  - Continue without decision-maker for that company
  - Mark in output: `"decision_maker": null`

### No Results Found
- Try alternative roles:
  - CTO → VP Engineering → Head of Engineering → Engineering Manager
  - CEO → Founder → Co-Founder
- If all fail:
  - Log: "No decision-maker found for {company}"
  - Continue without decision-maker

### Invalid Results (Name is Company Name)
- Log: "Invalid result for {company}: {result}"
- Retry with refined query
- If still invalid, skip

### LinkedIn URL is Invalid
- Validate format: `https://www.linkedin.com/in/[username]`
- If invalid, skip result

## Cost Tracking

Update Supabase `cost_of_run`:
- Exa API: ~$0.004 (4 searches)
- Example: `"$0.13 OpenAI (29 calls), $0.05 Apify (1 run), $0.004 Exa (4 queries)"`

## Supabase Logging

Update log entry:
```python
{
  "phase": "finding_decision_makers",
  "cost_of_run": "$0.134 OpenAI + Apify + Exa"
}
```

## Script Arguments

```bash
python execution/find_contact_person.py \
  --companies ".tmp/final_output/selected_companies.json" \
  --output ".tmp/decision_makers/contacts.json" \
  --run-id "uuid-here"
```

## Success Criteria

- ✅ Decision-maker found for at least 3 out of 4 companies
- ✅ All LinkedIn URLs valid format
- ✅ Names are real people (not company names)
- ✅ Data saved to `.tmp/decision_makers/contacts.json`
- ✅ Cost tracked in Supabase

## Common Issues & Solutions

### Issue: Exa returns competitor's employee (wrong company)
**Solution**: Validate result company name matches target company. If not, skip.

### Issue: Multiple results, unsure which is correct
**Solution**: Take first result (highest relevance score from Exa).

### Issue: Person's LinkedIn profile is outdated (changed jobs)
**Solution**: Acceptable risk. Email will still likely reach them or be forwarded.

### Issue: Some companies have no decision-maker found
**Solution**: Continue with available decision-makers. Email can mention companies even without specific contact.

## Testing

Test with known companies:
- Large public company (e.g., "Stripe") → Should find CTO easily
- Small startup → Should find Founder/CEO
- Obscure company → May not find anyone (expected)

## Alternative Approach (If Exa Not Available)

Use Bright Data MCP Tools:
- `scrape_linkedin_profile` (requires LinkedIn URL)
- More expensive, requires knowing LinkedIn URL first

Or use traditional web scraping:
- Google search: `"Company Name" CTO site:linkedin.com`
- Parse results
- Much slower and less reliable

**Exa is strongly preferred.**

## Notes

- Exa API is FAST and CHEAP (perfect for this use case)
- Decision-maker quality impacts email effectiveness
- If no decision-maker found for a company, still include company in email (recruiter can research contact themselves)
- Target role logic is critical (CEO for startups, CTO for tech companies, etc.)
