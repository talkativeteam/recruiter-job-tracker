# Prioritize Multi-Role Companies

## Purpose

Prioritize companies hiring for multiple UNIQUE roles (not duplicates).

## Goal

Rank companies by attractiveness to the recruiter:
1. Primary: Number of unique roles (multi-role > single-role)
2. Secondary: Relevance to recruiter's ICP

## Input

`.tmp/filtered_companies/direct_hirers.json` - Validated direct hirers

## Tool

`execution/prioritize_companies.py`

## Process

### Step 1: Load Direct Hirers
- Read `.tmp/filtered_companies/direct_hirers.json`
- Count total companies

### Step 2: Count Unique Roles Per Company
For each company:
- Extract all job titles
- Deduplicate (exact matches only)
- Count unique roles

Example:
```
Company A:
- "Network Engineer" (posted 2x) → 1 unique role
- "System Administrator" → 1 unique role
Total: 2 unique roles

Company B:
- "Software Engineer" → 1 unique role
Total: 1 unique role
```

### Step 3: Score Companies by ICP Fit (OpenAI)
- Use OpenAI (gpt-4o-mini) to score each company
- Input: Recruiter ICP + Company data
- Output: Fit score 0.0-1.0

Scoring criteria:
- Industry match: 40%
- Company size match: 20%
- Geography match: 20%
- Role alignment: 20%

### Step 4: Rank Companies
Sort by:
1. **Primary**: Number of unique roles (descending)
2. **Secondary**: ICP fit score (descending)

Example ranking:
```
1. Company A - 3 unique roles, 0.92 fit score
2. Company C - 3 unique roles, 0.85 fit score
3. Company B - 2 unique roles, 0.95 fit score
4. Company D - 1 unique role, 0.88 fit score
```

### Step 5: Save Prioritized List
- Write to `.tmp/filtered_companies/prioritized_companies.json`
- Include ranking metadata
- Update Supabase log

## Output

`.tmp/filtered_companies/prioritized_companies.json`

Array of companies sorted by priority:
```json
[
  {
    "rank": 1,
    "company_name": "TechCorp Inc",
    "company_website": "https://techcorp.com",
    "company_description": "...",
    "employee_count": 45,
    "unique_roles_count": 3,
    "icp_fit_score": 0.92,
    "jobs": [
      {
        "job_title": "Network Engineer",
        "job_url": "...",
        "job_description": "..."
      },
      {
        "job_title": "Cybersecurity Engineer",
        "job_url": "...",
        "job_description": "..."
      },
      {
        "job_title": "System Administrator",
        "job_url": "...",
        "job_description": "..."
      }
    ]
  }
]
```

## Why Multi-Role Companies Matter

**For recruiters**:
- Multiple roles = higher contract value
- Easier to establish relationship (multiple placements)
- Shows company is growing (more hiring needs)
- Better ROI for recruiter's time

**Priority**:
- Company hiring 3 roles > Company hiring 1 role
- Even if single-role company has slightly better ICP fit

## Error Handling

### OpenAI Scoring Fails
- Log: "OpenAI scoring failed for {company}: {error}"
- Use default score of 0.5
- Continue with ranking

### All Companies Have 1 Role
- Log: "No multi-role companies found"
- Rank by ICP fit score only
- Continue (still valid output)

### Duplicate Job Titles Not Properly Detected
- Use fuzzy matching (e.g., "Network Engineer" ≈ "Senior Network Engineer")
- Log: "Fuzzy matching applied for duplicate detection"

## Cost Tracking

Update Supabase `cost_of_run`:
- OpenAI calls: ~$0.01 (1-2 scoring calls)
- Example: `"$0.11 OpenAI (25 calls), $0.05 Apify (1 run)"`

## Supabase Logging

Update log entry:
```python
{
  "phase": "prioritizing_multi_role",
  "cost_of_run": "$0.11 OpenAI (25 calls)"
}
```

## Script Arguments

```bash
python execution/prioritize_companies.py \
  --input ".tmp/filtered_companies/direct_hirers.json" \
  --icp ".tmp/recruiter_icp.json" \
  --output ".tmp/filtered_companies/prioritized_companies.json" \
  --run-id "uuid-here"
```

## Success Criteria

- ✅ Companies ranked by unique roles (primary)
- ✅ Companies ranked by ICP fit (secondary)
- ✅ No duplicates in rankings
- ✅ Data saved to `.tmp/filtered_companies/prioritized_companies.json`
- ✅ Cost tracked in Supabase

## Common Issues & Solutions

### Issue: Duplicate job titles not detected (e.g., "Engineer" vs "Senior Engineer")
**Solution**: Use fuzzy string matching (e.g., Levenshtein distance > 80% = duplicate)

### Issue: All companies have same unique role count
**Solution**: Rank by ICP fit score only

### Issue: ICP fit scoring is inconsistent
**Solution**: Use temperature 0.1 for consistent scoring

## Testing

Test with sample data:
- Company A: 3 unique roles, high ICP fit → Should rank #1
- Company B: 1 unique role, perfect ICP fit → Should rank below multi-role companies
- Company C: 2 unique roles (but 1 is duplicate), medium ICP fit → Count should be 1 unique role

## Optimization

### Deterministic Duplicate Detection (Skip OpenAI)
- Exact match → Duplicate
- >90% string similarity → Duplicate
- Only use OpenAI for borderline cases (80-90% similarity)

This can save OpenAI calls.

## Notes

- Multi-role companies are MORE valuable to recruiters
- Don't overthink ICP scoring (simple heuristic is fine)
- Fuzzy matching prevents missing duplicates due to typos
- This phase sets up Phase 7 (selecting top 4)
