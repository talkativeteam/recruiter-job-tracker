# Select Top 4 Companies

## Purpose

Select the top 4 companies that are the best fit for the recruiter's ICP.

## Goal

Choose exactly 4 companies to feature in the outreach email.

## Input

`.tmp/filtered_companies/prioritized_companies.json` - Ranked companies

## Tool

`execution/prioritize_companies.py` (same script, just take top 4)

## Process

### Step 1: Load Prioritized Companies
- Read `.tmp/filtered_companies/prioritized_companies.json`
- Already sorted by priority (multi-role first, then ICP fit)

### Step 2: Select Top 4
- Take companies ranked 1-4
- If <4 companies available, take all available

### Step 3: Validate ICP Fit (Final Check)
For each selected company:
- Use OpenAI (gpt-4o-mini) to validate ICP fit
- Input: Recruiter ICP + Company data
- Output: Is this company a good fit? (yes/no + confidence)

Validation checks:
- ✅ Industries match?
- ✅ Company size matches?
- ✅ Geography matches?
- ✅ Roles align with recruiter's specialization?

If company fails validation:
- Log: "Company {name} failed final ICP validation: {reason}"
- Skip to next company (rank 5, 6, etc.)
- Continue until 4 valid companies found

### Step 4: Enrich Company Data (If Needed)
If Apify data is insufficient:
- Use `execution/scrape_website.py` to get more details
- Extract: Company mission, products, key info for email

### Step 5: Save Final 4
- Write to `.tmp/final_output/selected_companies.json`
- Log: "Selected {count} companies for outreach"
- Update Supabase log

## Output

`.tmp/final_output/selected_companies.json`

Array of exactly 4 companies:
```json
[
  {
    "rank": 1,
    "company_name": "TechCorp Inc",
    "company_website": "https://techcorp.com",
    "company_description": "SaaS platform for healthcare providers",
    "company_industry": "Technology",
    "employee_count": 45,
    "unique_roles_count": 3,
    "icp_fit_score": 0.92,
    "roles_hiring": [
      {
        "job_title": "Network Engineer",
        "job_url": "https://www.linkedin.com/jobs/view/...",
        "job_description": "We are seeking a Network Engineer to..."
      },
      {
        "job_title": "Cybersecurity Engineer",
        "job_url": "...",
        "job_description": "..."
      }
    ],
    "icp_validation": {
      "is_good_fit": true,
      "match_score": 0.92,
      "industries_match": true,
      "size_match": true,
      "geography_match": true,
      "roles_match": true,
      "reason": "Perfect fit - tech company, 45 employees, hiring for recruiter's core roles"
    }
  }
  // ... 3 more companies
]
```

## Why Exactly 4?

**User Experience**:
- 4 is ideal for email length (not too short, not overwhelming)
- Recruiter can reasonably follow up with 4 companies
- More than 4 = diluted focus
- Fewer than 4 = insufficient value

**If <4 companies available**:
- Log warning: "Only {count} companies available"
- Deliver what's available (2-3 is acceptable)
- If 0-1 companies, mark run as failed

## Error Handling

### <4 Companies Pass Final Validation
- Log warning: "Only {count} companies passed final validation"
- Deliver available companies (if ≥2)
- If <2 companies, mark run as failed: "Insufficient companies for outreach"

### ICP Validation Fails for All Top 4
- Continue checking companies 5-8
- If still none pass, mark run as failed

### Company Website Scraping Fails (Enrichment)
- Continue without enrichment
- Use Apify data only (usually sufficient)

## Cost Tracking

Update Supabase `cost_of_run`:
- OpenAI calls: ~$0.02 (4 validation calls)
- Website scraping (if needed): $0.00-0.05
- Example: `"$0.13 OpenAI (29 calls), $0.05 Apify (1 run)"`

## Supabase Logging

Update log entry:
```python
{
  "phase": "selecting_top_companies",
  "final_companies_selected": 4,
  "cost_of_run": "$0.13 OpenAI (29 calls)"
}
```

## Script Arguments

```bash
python execution/prioritize_companies.py \
  --input ".tmp/filtered_companies/prioritized_companies.json" \
  --icp ".tmp/recruiter_icp.json" \
  --output ".tmp/final_output/selected_companies.json" \
  --count 4 \
  --validate-icp \
  --run-id "uuid-here"
```

## Success Criteria

- ✅ Exactly 4 companies selected (or all available if <4)
- ✅ All companies validated against ICP
- ✅ Company data sufficient for email generation
- ✅ Data saved to `.tmp/final_output/selected_companies.json`
- ✅ Cost tracked in Supabase

## Common Issues & Solutions

### Issue: Top 4 companies all fail ICP validation
**Solution**: Check companies 5-8. If still none pass, ranking logic may be flawed.

### Issue: Company data too sparse for email
**Solution**: Scrape company website for more details.

### Issue: All 4 companies are in same industry
**Solution**: Acceptable if recruiter specializes in that industry. Otherwise, diversify by taking 2 from top industry, 2 from others.

### Issue: Only 2-3 companies available
**Solution**: Deliver 2-3 (acceptable). Update email to mention "a few opportunities" instead of "4 opportunities".

## Testing

Test with various scenarios:
- 10+ companies available → Should select top 4
- Exactly 4 companies → Should select all 4
- 2 companies → Should deliver 2 with warning
- 0 companies → Should fail run

## Notes

- Final validation is important (double-check ICP fit)
- 4 is ideal, but 2-3 is acceptable
- If 0-1, better to fail than send weak email
- Company data from Apify is usually sufficient (rarely need to scrape websites)
