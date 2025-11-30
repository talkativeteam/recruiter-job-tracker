# Identify Recruiter ICP & Roles Filled

## Purpose

Use AI to extract the recruiter's Ideal Client Profile (ICP) and specific roles they fill from their website content.

## Goal

Generate structured JSON with industries, company sizes, geographies, and PRECISE role titles.

## Input

`.tmp/recruiter_website.md` - Full website content in Markdown

## Tool

`execution/call_openai.py`

## Process

### Step 1: Load Website Content
- Read `.tmp/recruiter_website.md`
- Validate content is >500 characters

### Step 2: Call OpenAI API
- Model: **gpt-4o-mini** (cheap, sufficient for extraction)
- Prompt: From `config/ai_prompts.py` → `PROMPT_IDENTIFY_ICP`
- Temperature: 0.3 (consistent output)
- Max tokens: 1000

### Step 3: Parse Response
- Extract JSON from AI response
- Validate required fields:
  - `industries` (array of strings)
  - `company_sizes` (array of strings)
  - `geographies` (array of strings)
  - `roles_filled` (array of strings - MUST BE SPECIFIC)
  - `boolean_keywords` (array of strings)
  - `primary_country` (string)
  - `linkedin_geo_id` (string)

### Step 4: Validate Output
- Ensure roles are SPECIFIC (not vague like "Engineer")
- Ensure at least 1 industry, 1 geography, 2+ roles
- Validate LinkedIn geoId is numeric string

### Step 5: Save Output
- Write to `.tmp/recruiter_icp.json`
- Update Supabase log

## Output

`.tmp/recruiter_icp.json`

Example:
```json
{
  "industries": [
    "Technology",
    "Healthcare IT",
    "Financial Services"
  ],
  "company_sizes": [
    "10-50 employees",
    "50-100 employees"
  ],
  "geographies": [
    "United States",
    "California",
    "New York"
  ],
  "roles_filled": [
    "IT Help Desk Support",
    "Network Engineer",
    "Cybersecurity Engineer",
    "System Administrator",
    "Cloud Engineer"
  ],
  "boolean_keywords": [
    "IT Help Desk Support",
    "Help Desk Support",
    "Network Engineer",
    "Cybersecurity Engineer",
    "Cyber Security Engineer",
    "System Administrator",
    "Cloud Engineer"
  ],
  "primary_country": "United States",
  "linkedin_geo_id": "103644278"
}
```

## AI Prompt

Uses `config/ai_prompts.py` → `PROMPT_IDENTIFY_ICP`

Key instructions:
- Be SPECIFIC about roles (e.g., "Network Engineer", NOT "Engineer")
- Include role variations
- Extract company size ranges if mentioned
- Identify ALL geographies
- Determine correct LinkedIn geoId

## Common LinkedIn geoIds

- United States: `103644278`
- United Kingdom: `101165590`
- Canada: `101174742`
- California: `102095887`
- New York: `105080838`
- Texas: `102748797`

(Full list: https://www.linkedin.com/help/linkedin/answer/a1339626)

## Error Handling

### OpenAI API Fails (429, 500, timeout)
- Retry with exponential backoff (3 attempts)
- Log each attempt: "OpenAI API retry {attempt}/3"
- If all retries fail:
  - Log: "OpenAI API failed after 3 retries: {error}"
  - Update Supabase: `run_status: "failed"`, `phase: "identifying_icp"`
  - Halt execution

### Invalid JSON Response
- Log: "OpenAI returned invalid JSON: {response}"
- Retry with different prompt (add "RESPOND WITH VALID JSON ONLY")
- If still fails after 3 attempts, mark run as failed

### Missing Required Fields
- Log: "Missing required field: {field}"
- Retry with prompt emphasizing missing field
- If still fails, mark run as failed

### Vague Role Names (e.g., "Engineer", "Manager")
- Log warning: "Detected vague role name: {role}"
- Retry with prompt: "BE MORE SPECIFIC about role titles"
- Accept if still vague after retry (better than nothing)

## Cost Tracking

Update Supabase `cost_of_run`:
- gpt-4o-mini: ~$0.005 per call (estimate)
- Count input/output tokens
- Example: `"$0.005 OpenAI (1 call, 3K tokens)"`

## Supabase Logging

Update log entry:
```python
{
  "phase": "identifying_icp",
  "cost_of_run": "$0.005 OpenAI (1 call)"
}
```

## Script Arguments

```bash
python execution/call_openai.py \
  --prompt-type "identify_icp" \
  --input ".tmp/recruiter_website.md" \
  --output ".tmp/recruiter_icp.json" \
  --model "gpt-4o-mini" \
  --run-id "uuid-here"
```

## Success Criteria

- ✅ OpenAI returns valid JSON
- ✅ All required fields present
- ✅ Roles are SPECIFIC (not vague)
- ✅ At least 2 roles identified
- ✅ LinkedIn geoId is valid
- ✅ Cost tracked in Supabase

## Common Issues & Solutions

### Issue: AI extracts vague roles like "Engineer"
**Solution**: Prompt includes "BE SPECIFIC" instruction. If still vague, acceptable if that's all the website mentions.

### Issue: Website doesn't mention company sizes
**Solution**: AI should infer from context or default to "10-100 employees"

### Issue: Website is in non-English language
**Solution**: OpenAI can handle multiple languages. No special handling needed.

### Issue: Website has no clear ICP information
**Solution**: Log warning, mark run as failed with reason "Insufficient ICP data on website"

## Testing

Test with known recruiter websites:
- Clear ICP → Should extract easily
- Vague website → Should make best effort
- Multi-industry recruiter → Should list all industries

## Notes

- Use gpt-4o-mini (cheap, sufficient for extraction)
- Temperature 0.3 (balance consistency and creativity)
- Validate output rigorously (garbage in = garbage out)
- LinkedIn geoId is CRITICAL for next phase
