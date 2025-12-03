"""
AI Prompts - NEW SIMPLIFIED VERSION
These are the 3 core prompts for ICP extraction, Boolean generation, and LinkedIn URL creation
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

Output as JSON:
{{
  "recruiter_summary": "Brief 2-3 sentence summary of what the recruiter does, their target market (ICP), which industries/company types they serve, and which roles they typically fill",
  "primary_country": "United States",
  "linkedin_geo_id": "103644278"
}}
"""

# Phase 3: Generate Boolean Search
PROMPT_GENERATE_BOOLEAN_SEARCH = """The below data is the ICP of a recruitment company. Your job is to create a boolean search that can be used for LinkedIn jobs that would capture the roles they fill.

The boolean search should be quite large and extensive, capturing every role they might fill. If their ICP is very niche, then put job titles that might be specific to that industry.

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

# Phase 3b: Generate LinkedIn Job Search URLs
PROMPT_GENERATE_LINKEDIN_URLS = """Take the boolean search string provided and convert it into LinkedIn job search URLs with the correct geoId.

Create TWO URLs:
1. Jobs posted in last 24 hours
2. Jobs posted in last week (7 days)

Boolean Search:
{boolean_search}

LinkedIn Geo ID:
{linkedin_geo_id}

Primary Country:
{primary_country}

Output as JSON:
{{
  "url_24_hours": "Full LinkedIn jobs URL with 24 hour filter",
  "url_7_days": "Full LinkedIn jobs URL with 7 day filter"
}}
"""

# Helper functions
def format_icp_prompt(website_content: str) -> str:
    """Format the ICP identification prompt"""
    return PROMPT_IDENTIFY_ICP.format(website_content=website_content)

def format_boolean_search_prompt(icp_data: dict) -> str:
    """Format the Boolean search generation prompt"""
    return PROMPT_GENERATE_BOOLEAN_SEARCH.format(icp_data=str(icp_data))

def format_linkedin_urls_prompt(boolean_search: str, linkedin_geo_id: str, primary_country: str) -> str:
    """Format the LinkedIn URLs generation prompt"""
    return PROMPT_GENERATE_LINKEDIN_URLS.format(
        boolean_search=boolean_search,
        linkedin_geo_id=linkedin_geo_id,
        primary_country=primary_country
    )
