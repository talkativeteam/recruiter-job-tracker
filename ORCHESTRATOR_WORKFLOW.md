# Complete Orchestrator Pipeline Workflow

## Overview
The orchestrator runs a comprehensive 10-phase recruitment pipeline that finds companies hiring roles matching a recruiter's ICP (Ideal Client Profile). It has two modes: **LinkedIn Primary** (default) and **Exa Direct** (when `linkedin_plus_exa=false`).

---

## LinkedIn Primary Mode (Default Pipeline)

### **Phase 1: Input Validation**
1. Validate all required input fields (`client_website`, `max_jobs_to_scrape`, etc.)
2. Check webhook URL format if provided
3. Set default values for optional fields
4. Store validated input for logging

### **Phase 2: Deep ICP Extraction**
5. Initialize OpenAI caller (reused throughout pipeline)
6. Try deep ICP extraction with Playwright from client website
7. **Fallback**: If deep extraction fails, scrape multiple pages (homepage, /team-build, /sectors, /industries, /specialisms, /expertise, /what-we-do, /services, /roles)
8. Send combined content to GPT-4o-mini with ICP extraction prompt
9. Parse JSON response containing:
   - `recruiter_summary`: 2-3 sentence summary of recruiter's business
   - `primary_country`: Geographic focus
   - `linkedin_geo_id`: LinkedIn location code
10. Map country to 2-letter code (US, GB, CA, etc.)
11. Handle fallback: If extraction fails completely, use generic ICP

### **Phase 2.5: Pipeline Routing Decision**
12. Check `linkedin_plus_exa` flag in input
13. If `false`, jump to Exa Direct pipeline (skip to Phase 3-7 Exa)
14. If `true`, continue with LinkedIn scraping

### **Phase 3: Boolean Search Generation**
15. Format boolean search prompt with recruiter ICP summary
16. Call GPT-4o-mini to generate LinkedIn boolean search string
17. Parse JSON response (handle code fences if present)
18. Normalize quotes (replace single quotes with double quotes)
19. **CRITICAL**: Check boolean search length (LinkedIn 910 char limit)
20. If >910 chars, truncate at last complete "OR" clause before limit
21. Log final boolean search string with character count

### **Phase 4: LinkedIn Job Scraping**
22. Initialize Apify LinkedIn scraper
23. URL encode boolean search for LinkedIn
24. **Attempt 1**: Scrape last 24 hours (r86400) with max_jobs_to_scrape
25. Build LinkedIn URL with:
    - Boolean search keywords
    - Geographic filter (geoId)
    - Industry filter (f_I) - ONLY if boolean has broad roles (CEO, CFO, Manager, Director, VP) AND recruiter summary mentions specific industry
    - Time filter (f_TPR)
    - Relevance sort (sortBy=R)
26. Scrape jobs via Apify actor
27. Check if results >= 20 jobs (minimum acceptable)
28. **Attempt 2**: If <20 jobs, retry with 7 days (r604800)
29. Still <5 jobs? Trigger **Exa Fallback Workflow** (steps 30-37)

### **Phase 4.5: Exa Fallback for Niche ICPs**
30. Initialize Exa company finder
31. Find companies using Exa with ICP criteria (max 20 results)
32. Extract jobs from company websites using JobExtractor
33. Validate which companies are actively hiring (have valid job postings)
34. Convert Exa job format to LinkedIn format for consistency:
    - Map company fields (name, description, url)
    - Map job fields (title, description, link, location)
    - Add `source: "exa_fallback"` tag
35. Update stats with data source
36. If no jobs found via Exa either, raise exception
37. Set `data_source` stat to "exa_fallback" or "linkedin"

### **Phase 4.75: Company Size Filtering**
38. Filter jobs by company employee count (<=100 employees by default)
39. Parse employee count strings like "51-200" → take average (126)
40. Remove jobs from companies over size limit
41. Log filtered companies with employee counts
42. Update jobs list after size filter

### **Phase 5: Extract Unique Companies**
43. Create companies dictionary keyed by company name
44. Aggregate all jobs per company
45. Extract company metadata (description, website URL)
46. Convert dictionary to list of company objects
47. Update stats with `companies_found` count

### **Phase 6: Direct Hirer Validation**
48. Initialize CompanyFilter
49. For each company:
    - Format direct hirer validation prompt with company name, description, industry
    - Include sample job descriptions (first 2 jobs)
    - Call GPT-4o-mini with validation prompt
    - Parse JSON response: `is_direct_hirer` boolean
50. Keep only companies marked as direct hirers (not staffing agencies)
51. **Safety net**: If all companies filtered out, keep all (better lenient than empty)
52. Update stats with `companies_validated` count

### **Phase 6.5: CRITICAL Job-ICP Fit Validation**
53. Initialize JobICPValidator
54. For EACH company, validate EACH job individually:
    - Build validation prompt with recruiter summary, job title, job description, company info
    - Call GPT-4o-mini to check: industry match, role match, seniority match
    - Parse JSON: `is_match`, `confidence` (high/medium/low)
    - Reject low-confidence matches
55. Remove invalid jobs from each company
56. Remove companies with ZERO valid jobs
57. Log validation stats (passed/failed counts, percentages)
58. **CRITICAL FALLBACK**: If 0 companies pass validation:
    - Print "VALIDATION FAILED" warning
    - Trigger Exa fallback workflow (steps 59-67)
59. Update stats with `companies_after_job_validation` count

### **Phase 6.5b: Exa Fallback When Validation Fails**
60. Initialize Exa company finder
61. Find ICP-matching companies via Exa (max 20)
62. Verify employee counts via HeadcountVerifier/BrightData
63. Filter companies to <=100 employees
64. Enrich ALL Exa companies with Playwright before selection
65. Extract jobs from ALL companies using JobExtractor (ATS-aware)
66. Validate hiring activity (keep only companies with valid postings)
67. Select top 4 companies purely by ICP match relevance score

### **Phase 7: Company Prioritization**
68. Initialize CompanyPrioritizer
69. Score each company on:
    - Number of unique job roles (40% weight)
    - ICP fit based on recruiter summary (40% weight)
    - Company size preference (20% weight - favor 10-100 employees)
70. Sort companies by combined score (descending)
71. Select top 4 companies
72. Update stats with `final_companies_selected` count

### **Phase 8: Company Intelligence Enrichment**
73. Initialize CompanyIntelligence enricher
74. Format companies for enrichment with:
    - company_name, company_website, careers_url
    - company_description, employee_count
75. For each company:
    - Scrape website content with Playwright (handles JavaScript)
    - Extract careers page content if available
    - Analyze company culture, tech stack, growth signals
    - Generate insider intelligence summary via GPT-4o-mini
76. Map enrichment results back to top companies
77. Add `enrichment` field to each company
78. Handle enrichment failures gracefully (empty enrichment dict)

### **Phase 9: Outreach Email Generation**
79. Initialize EmailGenerator
80. Format companies for email with:
    - company_name, company_website, company_description
    - employee_count
    - `roles_hiring` array with job_title, description, job_url, posted_at
81. Enrich jobs with clickable LinkedIn URLs
82. Generate email using PROMPT_GENERATE_EMAIL with:
    - Recruiter name, company name, ICP summary
    - List of 4 companies with jobs
83. Parse email content from GPT-4 response
84. **NEW**: Humanize email for natural tone:
    - Call GPT-4 with PROMPT_HUMANIZE_EMAIL
    - Temperature=0.8 for variation
    - Preserve all details and links
85. Fallback to original email if humanization fails
86. Log email character count

### **Phase 10: Cost Calculation & Webhook Response**
87. Calculate OpenAI costs:
    - Track all model calls (gpt-4o-mini, gpt-4, etc.)
    - Count input/output tokens per model
    - Apply pricing: gpt-4o-mini ($0.150/$0.600 per 1M tokens), gpt-4 ($5/$15 per 1M tokens)
88. Calculate Exa costs:
    - $1 per 1000 searches
89. Calculate Apify costs:
    - $0.05 flat rate (only if LinkedIn was used, not Exa fallback)
90. Print detailed cost breakdown by service
91. Build final result JSON with:
    - run_metadata (run_id, status, pipeline_version)
    - input (validated input)
    - recruiter_icp (extracted ICP)
    - boolean_search_used
    - stats (job counts, company counts, costs, data_source)
    - verified_companies (top 4 with enrichment)
    - outreach_email (humanized)
92. Send result to webhook URL if provided
93. Log completion to Supabase if run_id exists
94. Print "✅ Pipeline completed successfully!"

---

## Exa Direct Mode (When linkedin_plus_exa=false)

### **Phases 1-2: Same as LinkedIn Mode**
(Steps 1-11 identical - input validation and ICP extraction)

### **Phase 3-7 (Exa Direct): Company Discovery**
95. Skip LinkedIn boolean generation completely
96. Initialize Exa company finder
97. Find companies matching ICP via Exa neural search (max 20)
98. Use recruiter summary for semantic matching
99. Get company metadata: name, url, description, employee count estimate

### **Phase 7.5: Employee Count Verification**
100. Initialize HeadcountVerifier with BrightData integration
101. For each Exa company:
    - Query BrightData for accurate employee count
    - Verify company is <=100 employees (configurable MAX_COMPANY_SIZE)
102. Filter out companies over size limit
103. Raise exception if no companies under limit found

### **Phase 8: Enrich ALL Companies BEFORE Selection**
104. Initialize CompanyIntelligence enricher
105. Enrich ALL Exa companies (not just top 4):
    - Scrape website with Playwright
    - Extract careers page content
    - Analyze company intel
    - Generate relevance score based on ICP match
106. Map enrichment back to Exa companies
107. Add `relevance_score` to each company

### **Phase 8.5: Job Extraction from ALL Companies**
108. Initialize JobExtractor (ATS-aware)
109. For each Exa company:
    - Visit careers page with Playwright
    - Detect ATS system (Greenhouse, Lever, Workday, etc.)
    - Extract job postings with title, description, URL
110. Validate hiring activity:
    - Keep companies with at least 1 valid job (has title + description)
    - Separate into companies_hiring vs companies_not_hiring
111. Build selection pool from hiring companies only

### **Phase 9: Select Top 4 by ICP Match**
112. Initialize CompanyPrioritizer
113. Score hiring companies by ICP relevance
114. Select top 4 companies based on semantic match to recruiter summary
115. Update stats with `final_companies_selected`

### **Phase 10: Email Generation (Same as LinkedIn Mode)**
116. Format companies for email with roles_hiring from ATS extraction
117. Generate email content with PROMPT_GENERATE_EMAIL or PROMPT_GENERATE_EMAIL_NO_ROLES
118. Humanize email with GPT-4 (temp=0.8)
119. Log email character count

### **Phase 11: Cost Calculation & Response**
120. Calculate Exa costs only (no Apify)
121. Calculate OpenAI costs (GPT-4 + GPT-4o-mini)
122. Build final result with `data_source: "exa_direct"`
123. Send to webhook if provided
124. Mark run as completed in Supabase

---

## Error Handling & Fallbacks

### **Global Error Handler**
125. Wrap entire pipeline in try-except
126. On any exception:
    - Print error message with stack trace
    - Build error_result JSON with status="failed"
    - Include error message, current stats, partial results
    - Mark run as failed in Supabase
    - Return error_result (don't crash completely)

### **Fallback Hierarchy**
127. **LinkedIn → Exa Fallback**: Triggers when <5 LinkedIn jobs found
128. **Validation Failure → Exa Fallback**: Triggers when 0 companies pass job-ICP validation
129. **Deep ICP → Multi-Page Scrape**: If Playwright extraction fails
130. **Multi-Page → Generic ICP**: If all extraction fails
131. **Enrichment Failure**: Continue with empty enrichment dicts
132. **Email Humanization Failure**: Use original non-humanized email

---

## Key Features

### **Industry Filtering (LinkedIn URLs)**
- Only applied when boolean has broad roles (CEO, CFO, Manager, Director, VP)
- Matches 30+ industries from recruiter summary keywords
- Examples: Software (f_I=4), IT Services (96), Financial Services (43), Healthcare (14), Manufacturing (55)

### **Boolean Search Truncation**
- LinkedIn hard limit: 910 characters
- Truncates at last complete "OR" clause before limit
- Preserves search validity

### **Cost Optimization**
- Reuse single OpenAI caller throughout pipeline (avoid reinitialization)
- Skip Apify if using Exa fallback
- Track per-model token usage for detailed billing

### **Data Source Tracking**
- LinkedIn primary: `data_source: "linkedin"`
- Exa fallback: `data_source: "exa_fallback"`
- Exa direct: `data_source: "exa_direct"`

### **Email Humanization**
- Uses GPT-4 with temperature=0.8 for natural variation
- Preserves all job URLs and company details
- Falls back to original if humanization fails

---

## Total Step Count: **132 distinct steps** across both pipeline modes
