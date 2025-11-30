# Cost Optimization Strategy

## Priority Order (Cheapest → Most Expensive)

### 1. Plain HTTP Request - FREE ✅
- **Use for**: Static websites, simple HTML pages
- **Pros**: Free, fast, no overhead
- **Cons**: Doesn't handle JavaScript, dynamic content, or anti-bot protection
- **When to use**: ALWAYS TRY FIRST

### 2. Playwright (no proxy) - FREE ✅
- **Use for**: JavaScript-heavy sites, dynamic content
- **Pros**: Free, handles modern websites, executes JavaScript
- **Cons**: Slower than HTTP, higher resource usage
- **When to use**: When HTTP fails due to JavaScript/dynamic content

### 3. Bright Data MCP Tools - CHEAP 💰
- **Use for**: Structured data (LinkedIn profiles, company info)
- **Pros**: Pre-cached data, reliable, structured output
- **Cons**: Costs money (but relatively cheap)
- **When to use**: For LinkedIn profile/company lookups

### 4. Bright Data Web Unlocker - EXPENSIVE 💰💰💰
- **Use for**: LAST RESORT ONLY
- **Pros**: Bypasses any protection, very reliable
- **Cons**: EXPENSIVE - costs add up quickly
- **When to use**: Only when all other methods fail AND data is critical

## Cost Tracking

Track costs in this format:
```
"$0.05 OpenAI (12 calls), 1 Apify run (50 jobs), 3 Playwright sessions, 4 Exa queries"
```

### Breakdown by Service

**OpenAI**:
- gpt-4o-mini: ~$0.00015 per 1K input tokens, ~$0.0006 per 1K output tokens
- gpt-4-turbo-preview: ~$0.01 per 1K input tokens, ~$0.03 per 1K output tokens
- **Strategy**: Use gpt-4o-mini for everything EXCEPT client-facing email

**Apify**:
- LinkedIn Jobs Scraper: ~$0.05 per run (50 jobs)
- **Strategy**: Maximize efficiency with `scrapeCompany: true` to avoid additional scraping

**Exa API**:
- ~$0.001 per search
- **Strategy**: Use neural search for decision-makers (4 searches = $0.004)

**Bright Data**:
- Web Unlocker: ~$0.01-0.05 per request
- **Strategy**: AVOID unless absolutely necessary, use HTTP → Playwright first

**Playwright**:
- FREE (self-hosted)
- **Strategy**: Use liberally as fallback from HTTP

## Decision Tree

```
Need to scrape a website?
├─ Try HTTP request first (FREE)
│  ├─ Success? → Done ✅
│  └─ Failed? → Continue
├─ Try Playwright (FREE)
│  ├─ Success? → Done ✅
│  └─ Failed? → Continue
├─ Is data critical for client deliverable?
│  ├─ No → Skip, log error, continue
│  └─ Yes → Use Bright Data (PAID) as last resort
```

## AI Model Selection

```
Task type?
├─ Simple extraction, filtering, validation → gpt-4o-mini
├─ ICP analysis, Boolean search generation → gpt-4o-mini
├─ Company validation, prioritization → gpt-4o-mini
└─ Client-facing email generation → gpt-4-turbo-preview (ONLY)
```

## Cost Per Run Estimates

**Typical successful run**:
- Phase 1 (Scraping): $0.00 (HTTP) or $0.01 (Playwright) or $0.05 (Bright Data)
- Phase 2 (ICP): $0.005 (OpenAI gpt-4o-mini, 1 call)
- Phase 3 (Boolean): $0.003 (OpenAI gpt-4o-mini, 1 call)
- Phase 4 (Jobs): $0.05 (Apify, 1 run)
- Phase 5 (Filter): $0.10 (OpenAI gpt-4o-mini, 20 validation calls)
- Phase 6 (Prioritize): $0.01 (OpenAI gpt-4o-mini, 1 call)
- Phase 7 (Select): $0.02 (OpenAI gpt-4o-mini, 4 validation calls)
- Phase 8 (Decision Makers): $0.004 (Exa, 4 queries)
- Phase 9 (Email): $0.05 (OpenAI gpt-4-turbo-preview, 1 call)

**Total estimated cost**: ~$0.25-0.35 per run

## Optimization Strategies

1. **Batch API calls** when possible
2. **Cache results** in `.tmp/` to avoid re-scraping/re-calling
3. **Use Apify's `scrapeCompany: true`** to get company data automatically
4. **Minimize OpenAI calls**:
   - Don't validate obvious cases (e.g., company named "XYZ Staffing" is obviously a recruiter)
   - Use deterministic logic where possible
5. **Fail fast**: Don't retry expensive operations unnecessarily

## Red Flags (High Cost Scenarios)

🚨 **ALERT** if costs exceed:
- $0.50 per run → Something is inefficient
- >50 OpenAI calls per run → Too many validation calls
- >3 Bright Data requests per run → Should use cheaper methods
- >5 Apify runs per request → Should not need multiple runs

## Monthly Cost Projections

**Assumptions**: 100 runs per day

- **Low efficiency** (using expensive methods): $50/day = $1,500/month
- **High efficiency** (optimized path): $25/day = $750/month

**Target**: Stay under $1,000/month for 100 daily runs
