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
1. **Industries they serve** - VERY SPECIFIC company types their clients are (e.g., "Digital/Creative Agencies", "Early-stage SaaS", "Healthcare Providers", NOT just "Technology")
2. **Company sizes** they target (e.g., "10-100 employees", "100-500 employees")
3. **Geographies** they operate in (countries, states, cities)
4. **Specific roles** they fill (be PRECISE - e.g., "Product Manager", "Network Engineer", NOT vague like "Tech roles")
5. **Keywords** for Boolean search (variations of role names)
6. **Primary country** for LinkedIn search
7. **LinkedIn geoId** for that country

CRITICAL Rules for Industries:
- Be HYPER-SPECIFIC about company types (e.g., "Digital Agencies" NOT "Technology")
- Look for phrases like "we work with", "our clients are", "we specialize in", "we serve"
- Examples: "Creative Agencies", "SaaS Startups", "Healthcare Providers", "Manufacturing", "Financial Services Firms"

CRITICAL Rules for Geography:
- Look for ANY location indicators: address, phone numbers, currency symbols (£=UK, $=US, €=EU), domain extensions (.co.uk, .com, .ca)
- If geographies are listed in order (e.g., "UK, EMEA, APAC, US"), the FIRST one is the primary market
- Look for "based in", "located in", "operating from" phrases to identify headquarters
- Email domains can indicate location (.co.uk = UK, .ca = Canada)
- The primary country is where the recruiter is BASED, not just where they recruit

Role Extraction Rules:
- Be SPECIFIC about roles (e.g., "Network Engineer", NOT "Engineer")
- Include role variations (e.g., "Cybersecurity Engineer" OR "Cyber Security Engineer")
- Extract company size ranges if mentioned
- Identify ALL geographies mentioned

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
PROMPT_GENERATE_BOOLEAN_SEARCH = """You are a LinkedIn Boolean search expert. Your job is to create a STRICT, PRECISE Boolean search string that finds roles AT THE RIGHT TYPE OF COMPANIES.

CRITICAL: The boolean search must filter by BOTH role AND company type to avoid irrelevant results.

Rules:
1. ALWAYS include company type/industry filters using AND operators
2. Use quotes around each role (e.g., "Product Manager")
3. Use OR operators between role variations
4. Use AND operators to combine roles WITH company type filters
5. NEVER use vague terms alone

Format: (role search) AND (company type search)

Examples:
- Good: ("Product Manager" OR "Senior Product Manager") AND ("digital agency" OR "creative agency" OR "marketing agency")
- Good: ("Network Engineer" OR "Infrastructure Engineer") AND ("SaaS" OR "software company" OR "tech startup")
- Bad: ("Product Manager" OR "Senior Product Manager") [missing company filter]
- Bad: ("Engineer") [too vague]

ICP Data:
{icp_data}

CRITICAL: Use the "industries" field to create the company type filter. Be specific!
- If industries = ["Digital Agencies", "Creative Agencies"] → AND ("digital agency" OR "creative agency" OR "marketing agency")
- If industries = ["SaaS Companies", "Tech Startups"] → AND ("SaaS" OR "software company" OR "tech startup")
- If industries = ["Healthcare Providers"] → AND ("hospital" OR "healthcare provider" OR "medical center")

Generate:
1. Boolean search string combining roles AND company types
2. URL-encoded version for LinkedIn
3. Full LinkedIn URL with parameters

Output (JSON only):
{{{{
  "boolean_search": "(role search) AND (company type search)",
  "linkedin_url": "https://www.linkedin.com/jobs/search/?f_JT=F&f_TPR=r86400&geoId=103644278&keywords=...&sortBy=R",
  "geo_id": "103644278"
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
- Result: is_good_fit = FALSE (wrong company type, even if roles match)

Recruiter's ICP:
{recruiter_icp}

Company Data:
Company Name: {company_name}
Company Description: {company_description}
Company Industry: {company_industry}
Employee Count: {employee_count}
Location: {location}
Roles Hiring: {roles_hiring}

Evaluation Rules:
1. **Industry match is MANDATORY** - Company type must match recruiter's target industries
2. Company size should match target range (flexible if close)
3. Geography match is important but can be flexible
4. Roles should align with recruiter's specialization

Scoring:
- If industries don't match → is_good_fit = false (automatic rejection)
- If all criteria match well → match_score >= 0.8
- If some criteria match → match_score 0.5-0.7
- If industries don't match → match_score < 0.3

Output (JSON only):
{{
  "is_good_fit": true/false,
  "match_score": 0.0-1.0,
  "industries_match": true/false,
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
1. [Company Name] — [Role Title]
[1-2 lines: what they do, key details]
[1-2 lines: what the role entails, candidate profile]
Website: [company website URL]
Job: [FULL JOB POSTING LINK]

2. [Company Name] — [Role Title]
[repeat format for each company]

[CONTINUE FOR ALL COMPANIES]

Shout out if you want the contact info for any of these folks. We send this type of thing over to recruiters all the time with the decision makers info and phone number.

Happy to have a quick 10 min chat about how we could explore doing something like this for you if you like. How's 4pm GMT today?

Your call.

CRITICAL RULES:
1. ONLY generate the companies section (numbered list with details)
2. DO NOT generate the opening line or closing section - those are fixed
3. INCLUDE website URL AND job posting link for EVERY company
4. Keep each company to 4 lines max
5. Use ACTUAL company names and REAL job posting URLs
6. Factual descriptions only - no marketing speak
7. No signature or extra closing lines
8. Output plain text only, NO JSON, NO MARKDOWN

Companies data to include:
{companies_data}

Generate ONLY the numbered companies section (starting with "1. "):"""

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

def format_exa_criteria_prompt(icp_data: dict, max_company_size: int = 100, jobs_posted_timeframe: str = "last 7 days") -> str:
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
    # Format companies data with insider intelligence
    companies_text = ""
    for i, company in enumerate(companies_data, 1):
        companies_text += f"\nCompany {i}:\n"
        companies_text += f"  Name: {company['company_name']}\n"
        companies_text += f"  Website: {company['company_website']}\n"
        companies_text += f"  Employee Count: {company.get('employee_count', 'Unknown')}\n"
        
        # Add insider intelligence if available
        if 'insider_intelligence' in company:
            intel = company['insider_intelligence']
            companies_text += f"  Business Description: {intel.get('business_description', '')}\n"
            if intel.get('insider_details'):
                companies_text += f"  Key Details:\n"
                for detail in intel['insider_details']:
                    companies_text += f"    - {detail}\n"
        else:
            companies_text += f"  Description: {company.get('company_description', '')[:200]}\n"
        
        companies_text += f"  Open Roles:\n"
        for role in company['roles_hiring']:
            posted_date = role.get('posted_at', '')
            job_url = role.get('job_url', '')
            companies_text += f"    - {role['job_title']} (Posted: {posted_date})\n"
            if job_url:
                companies_text += f"      Full Job Link: {job_url}\n"
    
    # Add email thread context if provided
    email_thread_context = ""
    email_thread_section = ""
    if email_thread:
        email_thread_context = " that continues the conversation naturally"
        email_thread_section = f"\nPrevious Email Thread:\n{email_thread}\n"
    
    # Set timezone for time calculation
    if not recruiter_timezone:
        recruiter_timezone = "GMT"
    
    return PROMPT_GENERATE_EMAIL.format(
        recruiter_name=recruiter_name,
        sender_name=sender_name or "[Your Name]",
        sender_email=sender_email or "",
        recruiter_timezone=recruiter_timezone,
        email_thread_context=email_thread_context,
        email_thread_section=email_thread_section,
        companies_data=companies_text
    )