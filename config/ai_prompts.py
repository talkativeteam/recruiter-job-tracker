"""
AI Prompts
Centralized storage for all AI prompts used in the system
"""

# Phase 2: Identify Recruiter ICP
PROMPT_IDENTIFY_ICP = """You are an expert at analyzing recruiter websites to extract their Ideal Client Profile (ICP) and the specific roles they fill.

CRITICAL DISTINCTION:
- "Industries" = The TYPE OF COMPANIES the recruiter's clients are (e.g., "Digital Agencies", "Creative Agencies", "SaaS Companies", "Fintech Companies")
- "Roles" = The JOB TITLES they fill (e.g., "Product Manager", "Web Developer", "UX Designer")

Example: If they say "we recruit Product Managers for digital agencies" → industries: ["Digital Agencies", "Creative Agencies"], roles: ["Product Manager"]

Your task is to analyze the recruiter's website content and extract:
1. **Industries they serve** – Prefer specific company types, BUT include broader/adjacent categories when the site positions as multi-sector or generalist (aim 6–10 items if available).
2. **Company sizes** they target (give ranges; if unclear, infer a broader band such as "10–250" rather than a narrow slice).
3. **Geographies** they operate in (countries, states, cities; list multiple where relevant).
4. **Roles they fill** – List precise titles AND adjacent equivalents across functions (leadership, sales, engineering, marketing, operations, clinical/technical as applicable).
5. **Keywords** for Boolean search (variations + synonyms; include adjacent role phrasing).
6. **Primary country** for LinkedIn search
7. **LinkedIn geoId** for that country

CRITICAL Rules for Industries:
- Prefer specificity when clearly stated, but if positioning is broad (e.g., “sectors we cover: radiology, cardiology, robotics, patient care”), include adjacent/broader categories too. Avoid collapsing to a single umbrella like "Technology"; instead list multiple relevant sectors.
- Look for phrases like "we work with", "our clients are", "we specialize in", "we serve".
- Examples: "Creative Agencies", "SaaS Startups", "Healthcare Providers", "MedTech", "Neurovascular", "Robotics", "Manufacturing", "Financial Services Firms".

CRITICAL Rules for Geography:
- Look for ANY location indicators: address, phone numbers, currency symbols (£=UK, $=US, €=EU), domain extensions (.co.uk, .com, .ca)
- If geographies are listed in order (e.g., "UK, EMEA, APAC, US"), the FIRST one is the primary market
- Look for "based in", "located in", "operating from" phrases to identify headquarters
- Email domains can indicate location (.co.uk = UK, .ca = Canada)
- The primary country is where the recruiter is BASED, not just where they recruit

Role Extraction Rules:
- Be SPECIFIC about roles (e.g., "Network Engineer"), but ALSO add adjacent/related titles that recruiters commonly place (e.g., "Clinical Account Manager", "Technical Account Manager", "Sales Engineer").
- Include role variations and synonyms (e.g., "Cybersecurity Engineer" OR "Cyber Security Engineer").
- Extract company size ranges if mentioned; if unclear, infer reasonable, slightly broader ranges.
- Identify ALL geographies mentioned.

LinkedIn geoId Reference:
- United Kingdom: 101165590
- United States: 103644278
- Canada: 101174742
- Germany: 101282230
- Australia: 101452733
- Singapore: 102454443

Website Content:
{website_content}

Output (JSON only, no explanation):
{{
  "industries": ["SPECIFIC Company Type 1", "SPECIFIC Company Type 2"],
  "company_sizes": ["10-100 employees"],
  "geographies": ["United States", "California"],
  "roles_filled": [
    "Specific Role Title 1",
    "Specific Role Title 2"
  ],
  "boolean_keywords": [
    "Role Keyword 1",
    "Role Keyword 2 Variation"
  ],
  "primary_country": "United States",
  "linkedin_geo_id": "103644278"
}}

Examples:
- Good: {{"industries": ["Digital Agencies", "Creative Agencies"], "roles_filled": ["Product Manager", "UX Designer"]}}
- Bad: {{"industries": ["Technology"], "roles_filled": ["Tech roles"]}}
"""

# Phase 3: Generate Boolean Search
PROMPT_GENERATE_BOOLEAN_SEARCH = """You are a LinkedIn Boolean search expert. Your job is to create MASSIVE quoted boolean searches with ~30% broader coverage using the 50/50 STRATEGY and adjacent-role expansion.

CRITICAL 50/50 STRATEGY:
- 50% GENERIC roles: Universal titles used across all industries
- 50% INDUSTRY-MAPPED roles: How these roles are actually called in the recruiter's target industry
- Include 20–36 total quoted variations (still close to 20–30, but allow expansion when useful).

This ensures we catch BOTH generic postings AND industry-specific nomenclature.

FALLBACK STRATEGY:
1. Try 24 hours: Massive boolean with 20-30 quoted variations (50% generic + 50% industry-mapped)
2. Try 7 days: Same boolean, longer timeframe
3. Fall back to Exa: If LinkedIn returns too few jobs (< 5)

BOOLEAN SEARCH RULES (USE QUOTES):
1. Use quotes around EVERY role title: "VP of Sales" OR "Sales Director"
2. Generate 20–36 role variations (10–18 generic + 10–18 industry-mapped)
3. Include ALL seniority levels for BOTH generic AND industry-mapped and add adjacent functions when it’s commonly interchangeable in the industry (e.g., Sales ↔ Commercial, CS ↔ Account Management):
   - Entry/Mid: Manager, Senior Manager, Associate Director
   - Director: Director, Senior Director, Executive Director
   - VP: VP, Vice President, SVP, Executive VP
   - C-Suite: Chief Officer, Head of, EVP

INDUSTRY-SPECIFIC MAPPING EXAMPLES:

🏥 MEDICAL TECHNOLOGY / HEALTHCARE / BIOTECH:
Generic Sales → Industry-Mapped:
- "VP of Sales" → "Chief Commercial Officer", "VP of Commercial Operations", "VP of Market Access", "VP of Clinical Sales"
- "Sales Director" → "Director of Commercialization", "Director of Clinical Solutions", "Director of Medical Device Sales"
- "Business Development Director" → "Director of Strategic Partnerships", "Director of Healthcare Partnerships", "Director of Provider Engagement"
- "Account Executive" → "Clinical Account Manager", "Territory Manager", "Medical Device Sales Representative"
- "Revenue Director" → "Director of Payer Strategy", "Director of Reimbursement", "VP of Health System Partnerships"

🎨 CREATIVE / DIGITAL AGENCIES:
Generic Marketing → Industry-Mapped:
- "CMO" → "Chief Creative Officer", "Executive Creative Director", "CCO"
- "Marketing Director" → "Creative Director", "Director of Client Services", "Studio Director"
- "Brand Manager" → "Creative Strategist", "Brand Strategist", "Account Director"
- "VP Marketing" → "VP of Creative", "VP of Client Strategy", "Head of Studio"

💻 SAAS / SOFTWARE / TECH:
Generic Sales → Industry-Mapped:
- "VP Sales" → "VP of Revenue", "Chief Revenue Officer", "VP of Growth"
- "Sales Manager" → "Customer Success Manager", "Growth Manager", "Revenue Manager"
- "Account Executive" → "Solutions Architect", "Sales Engineer", "Technical Account Manager"

🏦 FINTECH / FINANCIAL SERVICES:
Generic → Industry-Mapped:
- "VP Sales" → "VP of Partnerships", "Head of Institutional Sales", "Director of Wholesale Banking"
- "Product Manager" → "Product Owner", "Platform Manager", "Solutions Manager"

NO INDUSTRY FILTER - Let AI validation handle it (95% of time). Prefer recall over precision by ~30%.

ICP Data:
{icp_data}

Your task:
1. Identify core function: Sales, Marketing, Engineering, Operations, etc.
2. Analyze recruiter's industries to map generic roles → industry-specific titles
3. Generate 10-15 GENERIC quoted variations (all seniority levels)
4. Generate 10-15 INDUSTRY-MAPPED quoted variations (how they're called in that industry)
5. Combine both into one massive boolean (20-30 total variations)
6. NO industry filter (let AI validation handle)

Example Output for MedTech Sales:

50% GENERIC (10 variations):
"VP of Sales" OR "Vice President Sales" OR "SVP Sales" OR "Sales Director" OR "Director of Sales" OR "Head of Sales" OR "Chief Revenue Officer" OR "Senior Sales Director" OR "VP of Business Development" OR "Business Development Director"

50% INDUSTRY-MAPPED (10 variations):
"Chief Commercial Officer" OR "VP of Commercial Operations" OR "VP of Market Access" OR "Director of Commercialization" OR "Director of Clinical Solutions" OR "Director of Medical Device Sales" OR "VP of Clinical Sales" OR "Territory Manager" OR "Clinical Account Manager" OR "Director of Healthcare Partnerships"

COMBINED (20 variations - 50/50 split):
"VP of Sales" OR "Vice President Sales" OR "SVP Sales" OR "Sales Director" OR "Director of Sales" OR "Head of Sales" OR "Chief Revenue Officer" OR "Senior Sales Director" OR "VP of Business Development" OR "Business Development Director" OR "Chief Commercial Officer" OR "VP of Commercial Operations" OR "VP of Market Access" OR "Director of Commercialization" OR "Director of Clinical Solutions" OR "Director of Medical Device Sales" OR "VP of Clinical Sales" OR "Territory Manager" OR "Clinical Account Manager" OR "Director of Healthcare Partnerships"

Output (JSON only):
{{{{
  "boolean_search": "\"generic1\" OR \"generic2\" OR ... OR \"mapped1\" OR \"mapped2\" OR ...",
  "rationale": "20-30 variations: 50% generic + 50% industry-mapped for [industry]"
}}}}
"""

# Phase 5: Validate Direct Hirer
PROMPT_VALIDATE_DIRECT_HIRER = """You are a recruiter validation expert. Your job is to determine if a company is a DIRECT HIRER or a RECRUITER/STAFFING AGENCY.

Direct hirers:
- Hire for their own company
- Job descriptions mention "we are hiring", "join our team", "our company"
- Company description shows products/services they build/sell
- Industries like "Technology", "Healthcare", "Manufacturing", "Finance", etc.
- Company focuses on their own business operations

Recruiters/Staffing agencies:
- Hire on behalf of other companies
- Job descriptions mention "our client", "recruiting for", "staffing firm", "on behalf of"
- Company description focuses on recruitment/staffing/hiring services
- Industries like "Staffing and Recruiting", "Human Resources Services", "Employment Services"
- Company name includes words like "Staffing", "Recruiting", "Talent", "Personnel"

Input:
Company Name: {company_name}
Company Description: {company_description}
Company Industry: {company_industry}
Job Description: {job_description}

Output (JSON only):
{{
  "is_direct_hirer": true/false,
  "confidence": "high/medium/low",
  "reason": "Brief explanation why"
}}
"""

# Phase 7: Validate ICP Fit
PROMPT_VALIDATE_ICP_FIT = """You are an ICP matching expert. Determine if a company is a good fit for the recruiter's target profile.

CRITICAL: The recruiter's "industries" field contains the TYPE OF COMPANIES they serve (e.g., "Digital Agencies", "SaaS Companies").
You must match the COMPANY TYPE, not just the roles being hired.

Example:
- Recruiter industries: ["Digital Agencies", "Creative Agencies"]
- Company: "Paddle" (payments/fintech company)
- Result: Could still be a PARTIAL fit if role focus (e.g., growth/marketing) aligns strongly and company size/geography match. Do NOT auto-reject solely on imperfect industry labeling; consider adjacent/serviced industries.

Recruiter's ICP:
{recruiter_icp}

Company Data:
Company Name: {company_name}
Company Description: {company_description}
Company Industry: {company_industry}
Employee Count: {employee_count}
Location: {location}
Roles Hiring: {roles_hiring}

Evaluation Rules (30% less strict):
1. Industry/adjacent-industry match is IMPORTANT but not mandatory. Consider adjacency clusters (e.g., MedTech ↔ Healthcare Providers ↔ Life Sciences; Digital Agencies ↔ Creative/Marketing/Brand Studios; SaaS ↔ B2B Software).
2. Company size should match target range (±30% tolerance if unclear).
3. Geography match is helpful but flexible when company operates in multiple regions.
4. Roles should align with recruiter's specialization OR adjacent functional equivalents.

Scoring:
- Start from 0.5 when two of four dimensions align (roles, size, geography, industry/adjacent-industry).
- Strong alignment across three or more dimensions → match_score ≥ 0.7.
- Perfect or near-perfect alignment → match_score ≥ 0.85.
- Only one dimension aligns and others clearly do not → match_score ≤ 0.3.

Decision:
- is_good_fit = true when match_score ≥ 0.6.

Output (JSON only):
{{
  "is_good_fit": true/false,
  "match_score": 0.0-1.0,
    "industries_match": true/false,
    "adjacent_industry_match": true/false,
  "size_match": true/false,
  "geography_match": true/false,
  "roles_match": true/false,
  "reason": "Brief explanation focusing on company type match"
}}
"""

# Phase 8: Determine Decision Maker Role
PROMPT_DETERMINE_DECISION_MAKER = """You are an expert at identifying the right decision-maker to contact for recruiting opportunities.

Rules based on company size and role seniority:

Company <20 employees + any role → Target: Founder, CEO, Co-Founder
Company 20-50 employees + senior tech role → Target: CTO, VP Engineering, Head of Engineering
Company 20-50 employees + junior tech role → Target: Head of IT, Engineering Manager, IT Manager
Company 50-100 employees + senior role → Target: CTO, VP of [relevant department], Director of [relevant department]
Company 50-100 employees + junior role → Target: [Department] Manager, Head of [Department]

Input:
Company Size: {company_size} employees
Role Being Hired: {role_title}
Role Seniority: {role_seniority} (junior/mid/senior/executive)
Role Type: {role_type} (e.g., "Engineering", "IT", "Security", "Operations")

Output (JSON only):
{{
  "target_role": "CTO",
  "alternative_roles": ["VP Engineering", "Head of Engineering"],
  "reason": "Brief explanation"
}}
"""

# Phase 9: Generate Outreach Email
PROMPT_GENERATE_EMAIL = """You are writing to a recruiter about companies actively hiring. Your job is to present the company and role information clearly and factually.

EXACT FORMAT - DO NOT DEVIATE:

{recruiter_name},

Here's some stuff we've dug up for you. Right in your wheelhouse I reckon.

[GENERATE ONLY THIS SECTION - ONE ENTRY PER COMPANY]

SINGLE ROLE FORMAT:
Company Name — Role Title
[1-2 lines: what they do, key details]
[1-2 lines: what the role entails, candidate profile]
Website: [URL]
Job: [URL]

MULTIPLE ROLES FORMAT (when company has 2+ roles):
Company Name — Multiple Openings
[1 line: what they do]
They're hiring for [Role 1], [Role 2], and [Role 3]. [1 line: what this expansion signals - growth/scaling/diversification]
Website: [URL]
Jobs: [URL 1], [URL 2], [URL 3]

[CONTINUE FOR ALL COMPANIES - ONE PARAGRAPH PER COMPANY, NOT PER ROLE]

Shout out if you want the contact info for any of these folks. We send this type of thing over to recruiters all the time with the decision makers info and phone number.

Happy to have a quick 10 min chat about how we could explore doing something like this for you if you like. How's 4pm GMT today?

Your call.

CRITICAL RULES:
1. ONLY generate the companies section (formatted entries)
2. DO NOT generate the opening line or closing section - those are fixed
3. If a company has multiple roles, group them into ONE entry with "Multiple Openings" format
4. INCLUDE website URL AND job posting links for EVERY role
5. Keep each company entry to 4-5 lines max
6. Use ACTUAL company names and REAL job posting URLs
7. Factual descriptions only - no marketing speak
8. When multiple roles: highlight what the expansion means (scaling, growth phase, diversification)
9. No signature or extra closing lines
10. Output plain text only, NO JSON, NO MARKDOWN
11. NEVER repeat the same company twice - group all their roles together

Companies data to include:
{companies_data}

Generate ONLY the companies section (one entry per company):"""

# Fallback prompt when no explicit job postings are present
PROMPT_GENERATE_EMAIL_NO_ROLES = """You are writing to a recruiter about high-signal companies worth approaching now. No explicit job postings were captured, so focus on credible signals and why outreach makes sense.

EXACT FORMAT - DO NOT DEVIATE:

{recruiter_name},

Here's some stuff we've dug up for you. Right in your wheelhouse I reckon.

[GENERATE ONLY THIS SECTION - ONE ENTRY PER COMPANY]

Company Name — Why On Our Radar
[1-2 lines: what they do, key details]
Signals: [2 short signals from intel e.g. growth, team expansion, funding, new product]
Suggested roles to approach: [2 roles likely relevant]
Website: [URL]

[CONTINUE FOR ALL COMPANIES - ONE PARAGRAPH PER COMPANY]

CRITICAL RULES:
1. ONLY generate the companies section (formatted entries)
2. DO NOT generate the opening line or closing section - those are fixed
3. Do NOT apologize or say there are no openings
4. Use insider intelligence to craft Signals (concise, factual)
5. 4-5 lines per company max
6. Use ACTUAL company names and real websites
7. Plain text only, NO JSON, NO MARKDOWN
8. NEVER repeat the same company twice

Companies data to include:
{companies_data}

Generate ONLY the companies section (one entry per company):"""

# Prompt helper functions
def format_icp_prompt(website_content: str) -> str:
    """Format the ICP identification prompt"""
    return PROMPT_IDENTIFY_ICP.format(website_content=website_content)

def format_boolean_search_prompt(icp_data: dict) -> str:
    """Format the Boolean search generation prompt"""
    return PROMPT_GENERATE_BOOLEAN_SEARCH.format(icp_data=str(icp_data))

def format_direct_hirer_prompt(company_name: str, company_description: str, 
                                company_industry: str, job_description: str) -> str:
    """Format the direct hirer validation prompt"""
    return PROMPT_VALIDATE_DIRECT_HIRER.format(
        company_name=company_name,
        company_description=company_description or "Not available",
        company_industry=company_industry or "Not available",
        job_description=job_description
    )

def format_icp_fit_prompt(recruiter_icp: dict, company_name: str, company_description: str,
                          company_industry: str, employee_count: int, location: str, 
                          roles_hiring: list) -> str:
    """Format the ICP fit validation prompt"""
    return PROMPT_VALIDATE_ICP_FIT.format(
        recruiter_icp=str(recruiter_icp),
        company_name=company_name,
        company_description=company_description or "Not available",
        company_industry=company_industry or "Not available",
        employee_count=employee_count,
        location=location or "Not available",
        roles_hiring=str(roles_hiring)
    )

def format_decision_maker_prompt(company_size: int, role_title: str, 
                                  role_seniority: str, role_type: str) -> str:
    """Format the decision maker determination prompt"""
    return PROMPT_DETERMINE_DECISION_MAKER.format(
        company_size=company_size,
        role_title=role_title,
        role_seniority=role_seniority,
        role_type=role_type
    )

def format_exa_criteria_prompt(icp_data: dict, max_company_size: int = 200, jobs_posted_timeframe: str = "last 14 days") -> str:
    """Format the Exa criteria generation prompt"""
    from datetime import datetime, timedelta
    
    # Calculate date range
    today = datetime.now()
    if "7 days" in jobs_posted_timeframe:
        days = 7
    elif "14 days" in jobs_posted_timeframe:
        days = 14
    elif "30 days" in jobs_posted_timeframe:
        days = 30
    else:
        days = 7
    
    start_date = (today - timedelta(days=days)).strftime("%B %d, %Y").lower()
    end_date = today.strftime("%B %d, %Y").lower()
    
    roles = icp_data.get("roles_filled", icp_data.get("roles", []))
    industries = icp_data.get("industries", [])
    
    exa_search_query = f"{industries[0] if industries else 'companies'} hiring {roles[0] if roles else 'roles'}"
    
    prompt = f"""You are converting a natural language search query into structured criteria for the Exa API.

USER'S SEARCH QUERY:
{exa_search_query}

ADDITIONAL CONTEXT:
- Max Company Size: {max_company_size} employees
- Jobs Posted Within: {jobs_posted_timeframe}
- Today's Date: {end_date}
- Date Range: {start_date} to {end_date}

RECRUITER ICP:
- Industries: {', '.join(industries) if industries else 'any'}
- Roles: {', '.join(roles[:3]) if roles else 'any'}

Convert this query into 3-5 specific, atomic criteria statements that Exa can use to filter companies.

REQUIREMENTS:
1. Each criterion should be ONE specific requirement
2. Include company characteristics (industry, size, type)
3. Include hiring signals (job postings, timing) - be FLEXIBLE with dates
4. Include exclusions (what NOT to include)
5. Use lowercase, be specific and measurable
6. Be LESS STRICT - allow for broader matches

IMPORTANT: Make criteria LESS restrictive to get more results. Focus on:
- Core industry match (not exact sub-niche)
- General company size range (not exact)
- Recent hiring activity (not exact date ranges)

EXAMPLE OUTPUT (JSON array):
[
  "company is in {industries[0] if industries else 'tech'} or related sector",
  "company has under {max_company_size} employees",
  "company posted about hiring recently",
  "company is not a recruitment or staffing firm"
]

Generate criteria as a JSON array of strings. Be BROAD to capture more companies.
"""
    
    return prompt

def format_email_prompt(recruiter_name: str, companies_data: list, sender_name: str = None, 
                       sender_email: str = None, email_thread: str = None, recruiter_timezone: str = None) -> str:
    """Format the outreach email generation prompt"""
    # Group companies by name to consolidate duplicate entries
    from collections import defaultdict
    companies_grouped = defaultdict(lambda: {
        'company_name': '',
        'company_website': '',
        'employee_count': 'Unknown',
        'company_description': '',
        'insider_intelligence': None,
        'roles_hiring': []
    })
    
    for company in companies_data:
        company_name = company['company_name']
        
        # Initialize company data if first occurrence
        if not companies_grouped[company_name]['company_name']:
            companies_grouped[company_name].update({
                'company_name': company_name,
                'company_website': company['company_website'],
                'employee_count': company.get('employee_count', 'Unknown'),
                'company_description': company.get('company_description', ''),
                'insider_intelligence': company.get('insider_intelligence')
            })
        
        # Add all roles from this entry
        companies_grouped[company_name]['roles_hiring'].extend(company['roles_hiring'])
    
    # Determine if any roles exist across all companies
    total_roles = 0
    for c in companies_data:
        total_roles += len(c.get('roles_hiring', []))

    # Format companies data with insider intelligence
    companies_text = ""
    for i, (company_name, company) in enumerate(companies_grouped.items(), 1):
        companies_text += f"\nCompany {i}:\n"
        companies_text += f"  Name: {company['company_name']}\n"
        companies_text += f"  Website: {company['company_website']}\n"
        companies_text += f"  Employee Count: {company['employee_count']}\n"
        
        # Add insider intelligence if available
        if company['insider_intelligence']:
            intel = company['insider_intelligence']
            companies_text += f"  Business Description: {intel.get('business_description', '')}\n"
            if intel.get('insider_details'):
                companies_text += f"  Key Details:\n"
                for detail in intel['insider_details']:
                    companies_text += f"    - {detail}\n"
        else:
            companies_text += f"  Description: {company['company_description'][:200]}\n"
        
        # Only include roles section if we actually have roles across dataset
        if total_roles > 0:
            role_count = len(company['roles_hiring'])
            companies_text += f"  Open Roles ({role_count} total):\n"
            for role in company['roles_hiring']:
                posted_date = role.get('posted_at', '')
                job_url = role.get('job_url', '')
                companies_text += f"    - {role['job_title']} (Posted: {posted_date})\n"
                if job_url:
                    companies_text += f"      Full Job Link: {job_url}\n"
        else:
            # Provide concise signals to help the model craft value without roles
            intel = company.get('insider_intelligence') or {}
            signals = intel.get('insider_details') or []
            if signals:
                companies_text += "  Signals:\n"
                for s in signals[:3]:
                    companies_text += f"    - {s}\n"
    
    # Add email thread context if provided
    email_thread_context = ""
    email_thread_section = ""
    if email_thread:
        email_thread_context = " that continues the conversation naturally"
        email_thread_section = f"\nPrevious Email Thread:\n{email_thread}\n"
    
    # Set timezone for time calculation
    if not recruiter_timezone:
        recruiter_timezone = "GMT"
    
    prompt_template = PROMPT_GENERATE_EMAIL if total_roles > 0 else PROMPT_GENERATE_EMAIL_NO_ROLES
    return prompt_template.format(
        recruiter_name=recruiter_name,
        sender_name=sender_name or "[Your Name]",
        sender_email=sender_email or "",
        recruiter_timezone=recruiter_timezone,
        email_thread_context=email_thread_context,
        email_thread_section=email_thread_section,
        companies_data=companies_text
    )