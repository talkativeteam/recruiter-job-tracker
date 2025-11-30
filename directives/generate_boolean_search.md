# Generate LinkedIn Boolean Search URL

## Purpose

Create a precise LinkedIn Boolean search URL based on the recruiter's ICP.

## Goal

Generate a strict Boolean search string with proper LinkedIn URL parameters.

## Input

`.tmp/recruiter_icp.json` - ICP data with roles, geographies, etc.

## Tool

`execution/generate_linkedin_url.py`

## Process

### Step 1: Load ICP Data
- Read `.tmp/recruiter_icp.json`
- Extract:
  - `roles_filled` (for Boolean search)
  - `boolean_keywords` (role variations)
  - `linkedin_geo_id` (geography)

### Step 2: Generate Boolean Search String
- Use OpenAI (gpt-4o-mini) to create Boolean string
- Rules:
  - ALWAYS quote each role: `"Network Engineer"`
  - Use OR between roles: `"Role 1" OR "Role 2" OR "Role 3"`
  - Include variations: `"Cybersecurity Engineer" OR "Cyber Security Engineer"`
  - Keep focused (don't add vague terms)

Example:
```
("IT Help Desk Support" OR "Help Desk Support" OR "Network Engineer" OR "Cybersecurity Engineer" OR "Cyber Security Engineer" OR "System Administrator")
```

### Step 3: Build LinkedIn URL
- Base URL: `https://www.linkedin.com/jobs/search/`
- Parameters:
  - `f_JT=F` (full-time jobs)
  - `f_TPR=r86400` (last 24 hours - 86400 seconds)
  - `geoId={linkedin_geo_id}` (from ICP)
  - `keywords={url_encoded_boolean_search}`
  - `sortBy=R` (sort by relevance)

Full URL example:
```
https://www.linkedin.com/jobs/search/?f_JT=F&f_TPR=r86400&geoId=103644278&keywords=%28%22IT%20Help%20Desk%20Support%22%20OR%20%22Help%20Desk%20Support%22%20OR%20%22Network%20Engineer%22%29&sortBy=R
```

### Step 4: Validate URL
- Ensure URL is properly encoded
- Test URL format (starts with `https://www.linkedin.com/jobs/search/`)
- Ensure all parameters present

### Step 5: Save Output
- Write to `.tmp/linkedin_boolean_search.json`
- Update Supabase log

## Output

`.tmp/linkedin_boolean_search.json`

Example:
```json
{
  "boolean_search": "(\"IT Help Desk Support\" OR \"Help Desk Support\" OR \"Network Engineer\" OR \"Cybersecurity Engineer\" OR \"Cyber Security Engineer\")",
  "linkedin_url": "https://www.linkedin.com/jobs/search/?f_JT=F&f_TPR=r86400&geoId=103644278&keywords=%28%22IT%20Help%20Desk%20Support%22%20OR%20%22Help%20Desk%20Support%22%20OR%20%22Network%20Engineer%22%20OR%20%22Cybersecurity%20Engineer%22%20OR%20%22Cyber%20Security%20Engineer%22%29&sortBy=R",
  "geo_id": "103644278"
}
```

## LinkedIn URL Parameters

### Time Filters (`f_TPR`)
- `r86400` - Last 24 hours (86400 seconds)
- `r604800` - Last week (604800 seconds)
- `r2592000` - Last month (2592000 seconds)

### Job Type (`f_JT`)
- `F` - Full-time
- `P` - Part-time
- `C` - Contract
- `T` - Temporary
- `I` - Internship

### Sort (`sortBy`)
- `R` - Relevance (recommended)
- `DD` - Date (most recent first)

### Geography (`geoId`)
- See list in `identify_recruiter_icp.md`

## AI Prompt

Uses `config/ai_prompts.py` → `PROMPT_GENERATE_BOOLEAN_SEARCH`

Key instructions:
- ALWAYS use quotes around each role
- ALWAYS use OR operators
- Include variations
- URL-encode for LinkedIn

## Error Handling

### OpenAI Fails
- Retry 3 times with exponential backoff
- If all fail: Log error, mark run as failed

### Invalid Boolean String (no quotes, no OR)
- Log: "Invalid Boolean string generated: {string}"
- Retry with emphasis on format rules
- If still invalid after 3 attempts, fail run

### URL Encoding Fails
- Use Python's `urllib.parse.quote()` as fallback
- Log: "Manual URL encoding applied"

### Missing geoId
- Log: "No geoId found, defaulting to United States (103644278)"
- Use default and continue

## Cost Tracking

Update Supabase `cost_of_run`:
- gpt-4o-mini: ~$0.003 per call
- Example: `"$0.008 OpenAI (2 calls, 5K tokens)"`

## Supabase Logging

Update log entry:
```python
{
  "phase": "generating_boolean_search",
  "cost_of_run": "$0.008 OpenAI (2 calls)"
}
```

## Script Arguments

```bash
python execution/generate_linkedin_url.py \
  --icp ".tmp/recruiter_icp.json" \
  --output ".tmp/linkedin_boolean_search.json" \
  --run-id "uuid-here"
```

## Success Criteria

- ✅ Boolean search string properly formatted (quotes, OR)
- ✅ LinkedIn URL valid and properly encoded
- ✅ All required parameters present
- ✅ URL tested (opens in browser)
- ✅ Cost tracked in Supabase

## Common Issues & Solutions

### Issue: Boolean string too long (>1000 characters)
**Solution**: Prioritize top 5-7 most important roles, drop variations

### Issue: LinkedIn URL returns 0 results
**Solution**: Boolean string may be too specific. Retry with fewer roles or broader terms.

### Issue: Special characters break URL encoding
**Solution**: Use `urllib.parse.quote()` with `safe=''` parameter

### Issue: Multiple geographies in ICP
**Solution**: Use primary country's geoId only (from ICP data)

## Testing

Test Boolean strings:
- Valid: `("Network Engineer" OR "System Administrator")`
- Invalid: `Network Engineer OR System Administrator` (no quotes)
- Invalid: `"Network Engineer", "System Administrator"` (commas, not OR)

## Notes

- Boolean search is CRITICAL for finding relevant jobs
- Too broad = too many irrelevant jobs
- Too narrow = zero results
- Use quotes to ensure exact phrase matching
- LinkedIn's search is case-insensitive
