# Generate Peer-to-Peer Outreach Email

## Purpose

Write a casual, charming, peer-to-peer email highlighting the 4 companies and opportunities.

## Goal

Create an email that:
- Feels like a colleague texting another colleague
- Is NOT formal, corporate, or salesy
- Highlights each company briefly
- Includes decision-maker info
- Is <300 words total

## Input

- `.tmp/final_output/selected_companies.json` - Top 4 companies
- `.tmp/decision_makers/contacts.json` - Decision-makers
- `.tmp/validated_input.json` - Recruiter name

## Tool

`execution/call_openai.py`

**Model**: **gpt-4-turbo-preview** (ONLY time we use premium model - client-facing content)

## Process

### Step 1: Load Data
- Recruiter name (from validated input)
- 4 companies with job listings
- Decision-makers for each company

### Step 2: Format Companies Data
For each company, prepare:
- Company name and website (as clickable link)
- 1-2 sentence description of what they do
- List of roles they're hiring for (unique roles only)
- Decision-maker: Name, title, LinkedIn URL (as clickable link)

### Step 3: Call OpenAI API
- Model: **gpt-4-turbo-preview**
- Prompt: From `config/ai_prompts.py` → `PROMPT_GENERATE_EMAIL`
- Temperature: 0.7 (creative, natural-sounding)
- Max tokens: 800

### Step 4: Parse Email
- Extract plain text email
- Validate:
  - Length <300 words
  - All 4 companies mentioned
  - Decision-makers included (if available)
  - Tone is casual and friendly

### Step 5: Save Email
- Write to `.tmp/final_output/outreach_email.txt`
- Update Supabase log

## Output

`.tmp/final_output/outreach_email.txt`

Example email:
```
Hey [Recruiter Name],

I spotted a few companies that might be perfect for you:

**TechCorp Inc** (https://techcorp.com) – They build SaaS tools for healthcare providers and are hiring for Network Engineer and Cybersecurity Engineer roles. Reach out to Jane Smith, their CTO (https://linkedin.com/in/janesmith).

**HealthTech Co** (https://healthtech.co) – A 35-person startup creating patient engagement software. They're looking for a Senior System Administrator. John Doe, VP Engineering, is your contact (https://linkedin.com/in/johndoe).

**CloudSec Systems** (https://cloudsec.com) – Cloud security platform with 60 employees. Hiring for two roles: Cloud Engineer and IT Help Desk Support. Talk to Sarah Lee, Head of IT (https://linkedin.com/in/sarahlee).

**DataFlow Inc** (https://dataflow.com) – Data analytics company (85 employees) hiring a Network Engineer. Best contact is Mike Chen, Director of Infrastructure (https://linkedin.com/in/mikechen).

These are all direct hirers (not recruiters) and match your sweet spot. Let me know if you want more details!

Cheers,
[System/Talkative]
```

## Email Tone Guidelines

**DO**:
- Use casual language ("spotted", "sweet spot", "reach out")
- Keep sentences short and punchy
- Use bullet points or bold for company names
- Include clickable links
- Be friendly and helpful
- Sound like a peer, not a salesperson

**DON'T**:
- Use corporate jargon ("synergy", "leverage", "value proposition")
- Be overly formal ("Dear Sir/Madam", "Sincerely")
- Write long paragraphs
- Over-explain (keep it brief)
- Sound like a marketing email
- Use excessive punctuation (!!!)

## AI Prompt

Uses `config/ai_prompts.py` → `PROMPT_GENERATE_EMAIL`

Key instructions:
- Casual, friendly, conversational tone
- Brief but informative
- Highlight 4 companies
- Include decision-maker details
- <300 words

## Error Handling

### OpenAI Fails (429, 500, timeout)
- Retry 3 times with exponential backoff
- If all fail:
  - Log: "OpenAI email generation failed after 3 retries: {error}"
  - Update Supabase: `run_status: "failed"`, `phase: "generating_email"`
  - Halt execution

### Email is Too Long (>300 words)
- Log: "Email exceeds 300 words ({count} words)"
- Retry with prompt: "Make it more concise, under 300 words"
- If still too long, accept (not critical failure)

### Email Missing Company Details
- Log: "Email missing details for {company}"
- Retry with emphasis on including all companies
- If still missing after 3 attempts, accept (better than nothing)

### Email Tone is Too Formal
- This is subjective (hard to detect)
- Trust gpt-4-turbo-preview (good at casual tone)
- Manual review recommended for first few runs

## Cost Tracking

Update Supabase `cost_of_run`:
- gpt-4-turbo-preview: ~$0.05 per call (more expensive, but worth it for client-facing)
- Example: `"$0.18 OpenAI (29 gpt-4o-mini + 1 gpt-4-turbo), $0.05 Apify, $0.004 Exa"`

## Supabase Logging

Update log entry:
```python
{
  "phase": "generating_email",
  "run_status": "completed",
  "cost_of_run": "$0.234 OpenAI + Apify + Exa"
}
```

## Script Arguments

```bash
python execution/call_openai.py \
  --prompt-type "generate_email" \
  --companies ".tmp/final_output/selected_companies.json" \
  --decision-makers ".tmp/decision_makers/contacts.json" \
  --recruiter-name "John Doe" \
  --output ".tmp/final_output/outreach_email.txt" \
  --model "gpt-4-turbo-preview" \
  --run-id "uuid-here"
```

## Success Criteria

- ✅ Email generated successfully
- ✅ Tone is casual and friendly (not corporate)
- ✅ All 4 companies included
- ✅ Decision-makers mentioned (if available)
- ✅ Email <300 words (or close)
- ✅ Links are clickable (proper format)
- ✅ Cost tracked in Supabase

## Common Issues & Solutions

### Issue: Email sounds too formal/corporate
**Solution**: Retry with prompt: "Make it sound like a text message to a friend, very casual"

### Issue: Email is too brief (missing details)
**Solution**: Retry with prompt: "Include more details about each company (1-2 sentences)"

### Issue: Company website links not clickable
**Solution**: Ensure format is `(https://example.com)` or `<https://example.com>`

### Issue: Decision-maker missing for some companies
**Solution**: Acceptable. Email should mention company anyway. E.g., "No specific contact yet, but worth researching"

## Testing

Test with sample data:
- 4 companies with decision-makers → Should generate complete email
- 4 companies, 2 without decision-makers → Should mention companies without specific contact
- 2 companies only → Should adapt ("a couple" instead of "four")

## Why gpt-4-turbo-preview?

**This is the ONLY phase where we use the premium model.**

Reasons:
1. Client-facing content (recruiter reads this)
2. Tone is critical (casual, charming, peer-to-peer)
3. Represents Talkative's brand
4. Bad email = lost customer

**Cost**: ~$0.05 per email (worth it for quality)

## Notes

- This email is the final deliverable (most important output)
- Tone matters more than perfect structure
- Links must work (test before sending)
- If decision-maker not found, still include company (recruiter can research)
- Email should feel helpful, not pushy
