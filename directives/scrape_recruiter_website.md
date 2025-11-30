# Scrape Recruiter Website

## Purpose

Extract full website content from the recruiter's website to understand their ICP and roles filled.

## Goal

Get the complete website content (text, headings, links) in Markdown format for AI analysis.

## Input

- Recruiter website URL (from validated input)

## Tool

`execution/scrape_website.py`

## Process

### Step 1: Try HTTP Request First (FREE)
- Make plain HTTP GET request
- Parse HTML with BeautifulSoup
- Extract text content
- Convert to Markdown
- **If successful**: Save and exit
- **If failed**: Continue to Step 2

### Step 2: Try Playwright (FREE)
- Launch headless browser
- Navigate to URL
- Wait for page load (JavaScript execution)
- Extract rendered HTML
- Convert to Markdown
- **If successful**: Save and exit
- **If failed**: Continue to Step 3

### Step 3: Use Bright Data (PAID - Last Resort)
- Use Bright Data `scrape_as_markdown` MCP tool
- Get structured Markdown output
- **If successful**: Save and exit
- **If failed**: Log error, mark run as failed

## Output

`.tmp/recruiter_website.md` - Full website content in Markdown format

Example:
```markdown
# ABC Recruiting - Technology Staffing Experts

We specialize in placing IT professionals in growing tech companies...

## Our Focus Areas
- Network Engineering
- Cybersecurity
- IT Help Desk Support

## Industries We Serve
- Technology (SaaS, Cloud, Cybersecurity)
- Healthcare IT
- Financial Services

## Company Sizes
We work with startups and mid-sized companies (10-100 employees)...
```

## Error Handling

### HTTP Fails (404, 403, timeout)
- Log: "HTTP request failed: {error}"
- Try Playwright

### Playwright Fails (JavaScript errors, timeout)
- Log: "Playwright failed: {error}"
- Try Bright Data

### Bright Data Fails
- Log: "All scraping methods failed for {url}"
- Update Supabase: `run_status: "failed"`, `phase: "scraping_recruiter_website"`
- Notify agent to halt execution

### Invalid URL
- Log: "Invalid URL format: {url}"
- Mark run as failed immediately

## Cost Tracking

Update Supabase `cost_of_run`:
- HTTP: $0.00 (free)
- Playwright: $0.00 (free, self-hosted)
- Bright Data: ~$0.01-0.05 per request

Example: `"$0.00 HTTP (1 request)"`

## Supabase Logging

Update log entry:
```python
{
  "phase": "scraping_recruiter_website",
  "cost_of_run": "$0.00 HTTP (1 request)"
}
```

## Script Arguments

```bash
python execution/scrape_website.py \
  --url "https://recruitingfirm.com" \
  --output ".tmp/recruiter_website.md" \
  --run-id "uuid-here"
```

## Success Criteria

- ✅ Website content extracted
- ✅ Content saved to `.tmp/recruiter_website.md`
- ✅ File is >500 characters (sufficient content)
- ✅ Cost tracked in Supabase

## Common Issues & Solutions

### Issue: Website blocks HTTP requests (403)
**Solution**: Use Playwright (handles JavaScript anti-bot checks)

### Issue: Playwright timeout after 90s
**Solution**: Increase timeout or use Bright Data

### Issue: Website requires login
**Solution**: Skip if content is behind paywall, log warning

### Issue: Website has no text content (only images)
**Solution**: Log warning, try to extract alt text and meta descriptions

## Testing

Test with known URLs:
- Simple static site (should work with HTTP)
- JavaScript-heavy site (needs Playwright)
- Protected site (needs Bright Data)

## Notes

- ALWAYS try HTTP first (cheapest)
- Playwright is free but slower (use as fallback)
- Bright Data is last resort (paid)
- Extract as much text as possible for AI analysis
- Ignore navigation menus, footers (focus on main content)
