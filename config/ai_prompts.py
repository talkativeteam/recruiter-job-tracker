"""
AI Prompts - NEW SIMPLIFIED VERSION
Centralized storage for all AI prompts used in the system
"""

# Phase 2: Identify Recruiter ICP
PROMPT_IDENTIFY_ICP = """You have been given a scrape of a company website of a recruiter, identify their target market and the roles they fill, and where they fill those roles (ie what countries). 

Rules for Geography:
- Look for ANY location indicators: address, phone numbers, currency symbols (£=UK, $=US, €=EU), domain extensions (.co.uk, .com, .ca)
- If geographies are listed in order (e.g., "UK, EMEA, APAC, US"), the FIRST one is the primary market
- Look for "based in", "located in", "operating from" phrases to identify headquarters
- Email domains can indicate location (.co.uk = UK, .ca = Canada)

LinkedIn geoId Reference:
- United Kingdom: 101165590
- United States: 103644278
- Canada: 101174742
- Germany: 101282230
- Australia: 101452733
- Singapore: 102454443

Website Content:
{website_content}

CRITICAL: Be specific about what type of roles they fill. Don't just say "regulatory affairs" - say "regulatory affairs specialists managing FDA submissions and clinical trial compliance" or "supply chain QA specialists managing distribution logistics". The specificity matters for matching.

Examples:
- ❌ BAD: "places clinical research roles"
- ✅ GOOD: "places clinical research associates who monitor trial sites and manage patient recruitment"

- ❌ BAD: "fills regulatory affairs positions" 
- ✅ GOOD: "fills regulatory affairs specialists focused on trial protocol design and FDA submissions, NOT supply chain or logistics roles"

Output as JSON:
{{
  "recruiter_summary": "Brief 2-3 sentence summary of what the recruiter does, their target market (ICP), which industries/company types they serve, and which roles they typically fill. BE SPECIFIC about what the roles actually DO (e.g., patient-facing vs lab work, trial management vs supply chain, etc.)",
  "primary_country": "United States",
  "linkedin_geo_id": "103644278"
}}
"""

# Phase 3: Generate Boolean Search
PROMPT_GENERATE_BOOLEAN_SEARCH = """The below data is the ICP of a recruitment company. Your job is to create a boolean search that can be used for LinkedIn jobs that would capture the roles they fill.

CRITICAL: The boolean search MUST be under 910 characters total (LinkedIn limit). Keep it focused and efficient.

The boolean search should capture the most important roles they fill. If their ICP is very niche, then put job titles that might be specific to that industry.

An example of a good boolean (for an MSP recruiter for example) is the below:

("Help Desk Support" OR "IT Help Desk Support" OR "Help Desk Technician" OR "Tier 1 Support" OR "Tier 2 Support" OR "Tier 3 Support" OR "IT Service Desk" OR "IT Support Engineer" OR "Help Desk Manager" OR "IT Technician" OR "IT Field Technician" OR "System Administrator" OR "Network Engineer" OR "Cybersecurity Engineer" OR "Cyber Security Engineer" OR "IT Project Engineer" OR "Virtualization Engineer" OR "Cloud Engineer" OR "NOC Engineer" OR "Network Operations Center Technician" OR "Incident Response Engineer" OR "IR Engineer" OR "Machine Learning Engineer" OR "ML Engineer" OR "AI Engineer" OR "AI/ML Engineer" OR "Deep Learning Engineer" OR "MLOps Engineer" OR "ML Ops Engineer" OR "Applied Scientist" OR "Machine Learning Scientist" OR "NLP Engineer" OR "Computer Vision Engineer" OR "Generative AI Engineer")

Or another example would be if this was the companies icp:

Projectus Consulting places senior MedTech talent in high-impact roles directly tied to device adoption, commercialization, and clinical outcomes.
They serve scaling medical device companies, surgical robotics companies, implant manufacturers, and advanced diagnostics firms (Class II/III) that need commercial leadership, clinical applications, regulatory, or R&D engineering talent.
They fill roles close to the surgeon, payer, or buyer — the people who drive revenue, enable procedures, or navigate reimbursement, not generic ops or junior tech.

The ideal boolean for that would be something like this:

("VP Sales" OR "Vice President Sales" OR "Head of Sales" OR "Director of Sales" OR "Regional Sales Director" OR "Commercial Director" OR "Commercial Manager" OR "Sales Leader" OR "Sales Manager" OR "Territory Manager" OR "Area Sales Manager" OR "Market Access Director" OR "Director Market Access" OR "Manager Market Access" OR "Therapy Development Manager" OR "Field Clinical Specialist" OR "Clinical Applications Specialist" OR "Clinical Specialist" OR "Clinical Field Specialist" OR "Clinical Support Specialist" OR "Director Regulatory Affairs" OR "Head Regulatory Affairs" OR "Senior Regulatory Affairs" OR "QA Director" OR "Director Quality" OR "Director Quality Assurance" OR "R&D Manager" OR "Senior R&D Engineer" OR "Principal R&D Engineer" OR "Senior Mechanical Engineer" OR "Senior Embedded Engineer" OR "Embedded Software Engineer" OR "Senior Product Manager" OR "Director Product Management" OR "Director of Product" OR "Director Engineering" OR "VP Engineering" OR "Director of Business Development")
AND
("Medical Device" OR "MedTech" OR "Surgical" OR "Implant" OR "Spine" OR "Orthopedic" OR "Neuro" OR "Neurology" OR "Cardio" OR "Cardiovascular" OR "Vascular" OR "Stroke" OR "Electrophysiology" OR "EP" OR "Robotics" OR "Surgical Robotics" OR "Catheter" OR "Stent" OR "Endovascular" OR "Diagnostics" OR "Class II" OR "Class III")

ICP Data:
{icp_data}

Output as JSON:
{{
  "boolean_search": "Your boolean search string here with quoted role titles separated by OR"
}}
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
PROMPT_GENERATE_EMAIL = """You are writing to a recruiter about companies actively hiring. Write in a direct, punchy, conversational style.

EXAMPLE OF PERFECT STYLE:

Dan,

Got a couple of roles here that sit right inside your creative wheelhouse. Cool position in the market you've got.

VEED.IO are hiring a Creative Director to lead their brand and product storytelling. Modern SaaS environment. London. It's a high-impact role owning creative direction across an AI-powered video platform used by millions of creators worldwide.

Melotech are pushing the boundaries in generative media, blending AI + video to produce new forms of creative output. They're bringing on an AI Video Creator to experiment, prototype and define how media is made. Start up scale type of spot. 0-50 employees. Seems like exactly the type of candidate you supply.

Holosphere are looking for a Managing Director to steer their immersive/XR studio. Super interesting role. It's a leadership role at the intersection of creative technology, production and client innovation.

Happy to dig up more roles like this if you'd like. You on for a quick 10 min chat, happy to give you a run down of what its all about and can see if this can blend into your biz dev flow you've got running at the moment?

I could do tomorrow (Thursday) at 4pm GMT?

Give me a shout.

---

EXACT FORMAT TO FOLLOW:

{recruiter_name},

Got a couple of roles here that sit right inside your [industry/niche] wheelhouse. [Optional 1-line observation about their position/market].

[GENERATE ONLY THIS SECTION - ONE PARAGRAPH PER COMPANY]

SINGLE ROLE FORMAT:
Company Name are hiring a [Role Title] to [what the role does in 1 line]. [1-2 punchy details about environment/scale/stage]. It's a [characterize the role in 1 line]. [Optional: Company size or growth signal].

MULTIPLE ROLES FORMAT (when company has 2+ roles):
Company Name are [action verb: scaling/expanding/building] their [department/function]. [1 line what they do]. They're bringing on [Role 1], [Role 2], and [Role 3]. [1 line about what this signals - scaling phase, market expansion, etc]. [Company size if relevant].

[CONTINUE FOR ALL COMPANIES - ONE PARAGRAPH PER COMPANY, NOT PER ROLE]

Happy to dig up more roles like this if you'd like. You on for a quick 10 min chat, happy to give you a run down of what its all about and can see if this can blend into your biz dev flow you've got running at the moment?

I could do tomorrow (Thursday) at 4pm GMT?

Give me a shout.

CRITICAL RULES:
1. Generate the COMPLETE email including opening greeting, companies section, and closing
2. Follow the EXACT format shown above - do not deviate
3. The closing is FIXED - always "4pm GMT"
4. Short, punchy sentences. Direct language. No fluff.
5. Use present tense, active voice: "are hiring", "are building", "are scaling"
6. NO urls, NO links, NO websites, NO job posting links - keep it conversational
7. Characterize roles with context: "Modern SaaS environment", "Start up scale type of spot", "Super interesting role"
8. Include company size signals when relevant: "0-50 employees", "scaling fast", "established player"
9. If multiple roles, frame as company growth narrative, not a list
10. Each company = one tight paragraph (3-5 sentences max)
11. Match the tone: direct, insider knowledge, peer-to-peer, slightly casual but professional
12. Output plain text only, NO JSON, NO MARKDOWN formatting
13. NEVER repeat the same company twice - group all their roles into one paragraph
14. Be specific about what makes each role interesting - avoid generic descriptions

Companies data to include:
{companies_data}

Generate ONLY the companies section (one paragraph per company):"""

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

# Phase 10: Humanize Email
PROMPT_HUMANIZE_EMAIL = """You are an email editor making AI-generated business emails sound more natural and human.

Your task: Take the email below and make it more interesting and natural to read while keeping ALL details and links intact.

RULES:
1. Keep ALL company names, websites, job links, and key facts EXACTLY as they are
2. Make the tone more conversational and engaging
3. Vary sentence structure to avoid repetition
4. Add natural transitions between companies
5. Keep it concise - don't make it longer
6. Maintain the casual, peer-to-peer tone
7. Do NOT add pleasantries or formalities
8. Do NOT change the opening or closing lines
9. Output plain text only (no markdown, no JSON)

Original Email:
{original_email}

Generate the humanized version (same structure, more natural flow):"""

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
    
    # Extract data from ICP
    industries = icp_data.get("industries", [])
    roles = icp_data.get("roles_filled", icp_data.get("roles", []))
    
    # Create a simple summary from the structured data
    industry_text = industries[0] if industries else "companies"
    roles_text = ", ".join(roles[:3]) if roles else "various roles"
    
    prompt = f"""You convert recruiter information into simple search criteria for the Exa API.

This recruiter works with {industry_text} companies and fills roles like {roles_text}.

Create 4-5 criteria statements for Exa. Use simple 5th grade language.

ADDITIONAL CONTEXT:
- Max Company Size: {max_company_size} employees
- Jobs Posted Within: {jobs_posted_timeframe}
- Today's Date: {end_date}
- Date Range: {start_date} to {end_date}

REQUIREMENTS:
1. First criterion: what industry or company type they work with
2. Second criterion: company size requirement
3. Third criterion: what SPECIFIC ROLES they posted jobs for (not just "hiring recently" - be specific about role types)
4. Fourth criterion: what to exclude
5. Use lowercase, be specific and measurable
6. Be LESS STRICT - allow for broader matches

IMPORTANT: Make criteria LESS restrictive to get more results. Focus on:
- Core industry match (not exact sub-niche)
- General company size range (not exact)
- Recent hiring activity (not exact date ranges)
- SPECIFIC role types from the summary (commercial, engineering, clinical, etc)

EXAMPLE OUTPUT (JSON array):
[
  "company is in medical device or medtech space",
  "company has under {max_company_size} employees",
  "company posted job openings in the last 30-90 days related to commercial leadership, therapy development, market access, clinical applications, or R&D engineering",
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

def format_humanize_email_prompt(original_email: str) -> str:
    """Format the email humanization prompt"""
    return PROMPT_HUMANIZE_EMAIL.format(original_email=original_email)