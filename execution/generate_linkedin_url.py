"""
LinkedIn URL Generator
Generates LinkedIn Boolean search URLs
"""

import sys
import json
import argparse
from pathlib import Path
from urllib.parse import urlencode, quote_plus

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.config import LINKEDIN_BASE_URL, LINKEDIN_TIME_FILTER, LINKEDIN_JOB_TYPE
from execution.call_openai import OpenAICaller

MAX_KEYWORDS_LENGTH = 910  # LinkedIn keywords param hard limit
LINKEDIN_JOB_BASE = "https://www.linkedin.com/jobs/search/"

def is_valid_linkedin_jobs_url(url: str) -> bool:
    """Enterprise-grade validation for LinkedIn jobs search URLs."""
    import re
    from urllib.parse import urlparse, parse_qs

    if not url or not url.startswith(LINKEDIN_JOB_BASE):
        return False

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    # keywords required and must be a single string
    if has_broad_role:
        # Log why industry filter will be applied (gated by role breadth)
        if run_id:
            try:
                from execution.supabase_logger import SupabaseLogger
                SupabaseLogger().update_phase(
                    run_id=run_id,
                    phase="industry_filter_applied",
                    details={
                        "reason": "c-suite-only without specific roles",
                        "boolean_preview": boolean_search[:140]
                    }
                )
            except Exception:
                pass
    # Basic safety on length
        # Map industries to LinkedIn industry codes - only when broad C-suite
        if "software" in recruiter_summary or "saas" in recruiter_summary:
            params["f_I"] = "4"  # Computer Software
        elif "it services" in recruiter_summary or "it consulting" in recruiter_summary:
            params["f_I"] = "96"  # Information Technology and Services
        elif "financial services" in recruiter_summary or "investment" in recruiter_summary:
            params["f_I"] = "43"  # Financial Services
        elif "banking" in recruiter_summary:
            params["f_I"] = "41"  # Banking
        elif "accounting" in recruiter_summary:
            params["f_I"] = "47"  # Accounting
        elif "healthcare" in recruiter_summary or "health care" in recruiter_summary:
            params["f_I"] = "14"  # Hospital & Health Care
        elif "pharmaceutical" in recruiter_summary or "pharma" in recruiter_summary:
            params["f_I"] = "15"  # Pharmaceuticals
        elif "medical device" in recruiter_summary:
            params["f_I"] = "17"  # Medical Devices
        elif "biotechnology" in recruiter_summary or "biotech" in recruiter_summary:
            params["f_I"] = "12"  # Biotechnology
        elif "manufacturing" in recruiter_summary:
            params["f_I"] = "55"  # Machinery
        elif "retail" in recruiter_summary:
            params["f_I"] = "27"  # Retail
        elif "food" in recruiter_summary or "beverage" in recruiter_summary:
            params["f_I"] = "34"  # Food & Beverages
        elif "cpg" in recruiter_summary or "consumer packaged goods" in recruiter_summary or "consumer goods" in recruiter_summary:
            params["f_I"] = "25"  # Consumer Goods
        elif "real estate" in recruiter_summary:
            params["f_I"] = "44"  # Real Estate
        elif "construction" in recruiter_summary:
            params["f_I"] = "48"  # Construction
        elif "consulting" in recruiter_summary:
            params["f_I"] = "11"  # Management Consulting
        elif "marketing" in recruiter_summary or "advertising" in recruiter_summary:
            params["f_I"] = "80"  # Marketing and Advertising
        elif "legal" in recruiter_summary or "law" in recruiter_summary:
            params["f_I"] = "9"  # Law Practice
        elif "education" in recruiter_summary:
            params["f_I"] = "69"  # Education Management
        elif "nonprofit" in recruiter_summary or "non-profit" in recruiter_summary:
            params["f_I"] = "100"  # Non-Profit Organization Management
        elif "logistics" in recruiter_summary or "supply chain" in recruiter_summary:
            params["f_I"] = "116"  # Logistics and Supply Chain
        elif "hospitality" in recruiter_summary or "hotel" in recruiter_summary:
            params["f_I"] = "31"  # Hospitality
        elif "insurance" in recruiter_summary:
            params["f_I"] = "42"  # Insurance
        elif "telecommunications" in recruiter_summary or "telecom" in recruiter_summary:
            params["f_I"] = "8"  # Telecommunications
        elif "automotive" in recruiter_summary:
            params["f_I"] = "53"  # Automotive
        elif "aerospace" in recruiter_summary or "aviation" in recruiter_summary:
            params["f_I"] = "52"  # Aviation & Aerospace
        elif "oil" in recruiter_summary or "energy" in recruiter_summary:
            params["f_I"] = "57"  # Oil & Energy
    else:
        # Explicitly skip industry filter when specific roles are present or no C-suite
        if run_id:
            try:
                from execution.supabase_logger import SupabaseLogger
                SupabaseLogger().update_phase(
                    run_id=run_id,
                    phase="industry_filter_skipped",
                    details={
                        "reason": "specific roles present or no c-suite",
                        "has_specific_roles": has_specific_roles,
                        "is_c_suite_only": is_c_suite_only,
                        "boolean_preview": boolean_search[:140]
                    }
                )
            except Exception:
                pass
    s = boolean_search.strip()
    # Balance quotes: make sure count of double quotes is even
    if s.count('"') % 2 == 1:
        s = s + '"'
    # Balance parentheses: add closing ) if more opens than closes
    opens = s.count('(')
    closes = s.count(')')
    if opens > closes:
        s = s + (')' * (opens - closes))
    # Remove trailing boolean operator
    for tail in (" OR", " AND", " NOT"):
        if s.endswith(tail):
            s = s[:-len(tail)].rstrip()
    return s

def generate_linkedin_url(icp_data: dict, run_id: str = None) -> dict:
    """
    Generate LinkedIn Boolean search URL from ICP data
    """
    # Log ICP data to Supabase
    if run_id:
        from execution.supabase_logger import SupabaseLogger
        logger = SupabaseLogger()
        logger.update_phase(
            run_id=run_id,
            phase="generating_boolean_search",
            icp_data=icp_data
        )
    
    # Call OpenAI to generate Boolean search string
    caller = OpenAICaller(run_id=run_id)
    result = caller.generate_boolean_search(icp_data)
    
    if not result:
        raise Exception("Failed to generate Boolean search")
    
    boolean_search = result.get("boolean_search")

    # Enforce LinkedIn keywords length limit with safe truncation
    original_len = len(boolean_search) if boolean_search else 0
    truncated_search = _truncate_boolean(boolean_search, MAX_KEYWORDS_LENGTH)
    if run_id and truncated_search != boolean_search:
        try:
            from execution.supabase_logger import SupabaseLogger
            SupabaseLogger().update_phase(
                run_id=run_id,
                phase="boolean_truncated",
                details={
                    "original_length": original_len,
                    "truncated_length": len(truncated_search)
                }
            )
        except Exception:
            pass
    normalized = _normalize_boolean(truncated_search)
    boolean_search = normalized

    # Log normalization, length, and terminal character checks
    if run_id:
        try:
            from execution.supabase_logger import SupabaseLogger
            SupabaseLogger().update_phase(
                run_id=run_id,
                phase="boolean_normalized",
                details={
                    "length": len(boolean_search),
                    "endswith_paren": boolean_search.endswith(")"),
                    "preview": boolean_search[:180]
                }
            )
        except Exception:
            pass
    geo_id = icp_data.get("linkedin_geo_id", "103644278")  # Default to US
    
    # Build LinkedIn URL parameters
    params = {
        "f_JT": LINKEDIN_JOB_TYPE,  # Full-time
        "f_TPR": "r604800",  # Past week (r604800) - more results than 24h (r86400)
        "geoId": geo_id,
        "keywords": boolean_search,
        "sortBy": "R"  # Relevance
    }
    
    # Add industry filter ONLY if boolean search is VERY broad/generic (C-suite only)
    # Don't use filter if boolean already has specific role titles
    boolean_lower = boolean_search.lower()
    recruiter_summary = icp_data.get("recruiter_summary", "").lower()
    
    # Count how many specific role keywords vs generic C-suite keywords
    specific_keywords = ["developer", "engineer", "specialist", "analyst", "coordinator", 
                        "consultant", "administrator", "technician", "designer", "architect",
                        "accountant", "recruiter", "planner", "buyer", "controller"]
    
    c_suite_only = ["cfo", "ceo", "coo", "cto", "cmo", "chief financial officer", 
                    "chief executive officer", "chief operating officer"]
    
    has_specific_roles = any(keyword in boolean_lower for keyword in specific_keywords)
    # Must contain at least one C-suite term and no specific-role keywords
    is_c_suite_only = any(keyword in boolean_lower for keyword in c_suite_only)
    
    # Only apply industry filter if C-suite roles AND no specific titles
    has_broad_role = is_c_suite_only and not has_specific_roles
    
    if has_broad_role:
        # Optional: log why industry filter applied
        if run_id:
            try:
                from execution.supabase_logger import SupabaseLogger
                SupabaseLogger().update_phase(
                    run_id=run_id,
                    phase="industry_filter_applied",
                    details={
                        "reason": "c-suite-only without specific roles",
                        "boolean_preview": boolean_search[:140]
                    }
                )
            except Exception:
                pass
        # Map industries to LinkedIn industry codes - only use if very specific match
        if "software" in recruiter_summary or "saas" in recruiter_summary:
            params["f_I"] = "4"  # Computer Software
        elif "it services" in recruiter_summary or "it consulting" in recruiter_summary:
            params["f_I"] = "96"  # Information Technology and Services
        elif "financial services" in recruiter_summary or "investment" in recruiter_summary:
            params["f_I"] = "43"  # Financial Services
        elif "banking" in recruiter_summary:
            params["f_I"] = "41"  # Banking
        elif "accounting" in recruiter_summary:
            params["f_I"] = "47"  # Accounting
        elif "healthcare" in recruiter_summary or "health care" in recruiter_summary:
            params["f_I"] = "14"  # Hospital & Health Care
        elif "pharmaceutical" in recruiter_summary or "pharma" in recruiter_summary:
            params["f_I"] = "15"  # Pharmaceuticals
        elif "medical device" in recruiter_summary:
            params["f_I"] = "17"  # Medical Devices
        elif "biotechnology" in recruiter_summary or "biotech" in recruiter_summary:
            params["f_I"] = "12"  # Biotechnology
        elif "manufacturing" in recruiter_summary:
            params["f_I"] = "55"  # Machinery
        elif "retail" in recruiter_summary:
            params["f_I"] = "27"  # Retail
        elif "food" in recruiter_summary or "beverage" in recruiter_summary:
            params["f_I"] = "34"  # Food & Beverages
        elif "cpg" in recruiter_summary or "consumer packaged goods" in recruiter_summary or "consumer goods" in recruiter_summary:
            params["f_I"] = "25"  # Consumer Goods
        elif "real estate" in recruiter_summary:
            params["f_I"] = "44"  # Real Estate
        elif "construction" in recruiter_summary:
            params["f_I"] = "48"  # Construction
        elif "consulting" in recruiter_summary:
            params["f_I"] = "11"  # Management Consulting
        elif "marketing" in recruiter_summary or "advertising" in recruiter_summary:
            params["f_I"] = "80"  # Marketing and Advertising
        elif "legal" in recruiter_summary or "law" in recruiter_summary:
            params["f_I"] = "9"  # Law Practice
        elif "education" in recruiter_summary:
            params["f_I"] = "69"  # Education Management
        elif "nonprofit" in recruiter_summary or "non-profit" in recruiter_summary:
            params["f_I"] = "100"  # Non-Profit Organization Management
        elif "logistics" in recruiter_summary or "supply chain" in recruiter_summary:
            params["f_I"] = "116"  # Logistics and Supply Chain
        elif "hospitality" in recruiter_summary or "hotel" in recruiter_summary:
            params["f_I"] = "31"  # Hospitality
        elif "insurance" in recruiter_summary:
            params["f_I"] = "42"  # Insurance
        elif "telecommunications" in recruiter_summary or "telecom" in recruiter_summary:
            params["f_I"] = "8"  # Telecommunications
        elif "automotive" in recruiter_summary:
            params["f_I"] = "53"  # Automotive
        elif "aerospace" in recruiter_summary or "aviation" in recruiter_summary:
            params["f_I"] = "52"  # Aviation & Aerospace
        elif "oil" in recruiter_summary or "energy" in recruiter_summary:
            params["f_I"] = "57"  # Oil & Energy
    
    # Manual URL construction (urlencode doesn't handle parentheses properly)
    industry_param = f"&f_I={params['f_I']}" if "f_I" in params else ""
    linkedin_url = f"{LINKEDIN_BASE_URL}?f_JT={params['f_JT']}&f_TPR={params['f_TPR']}&geoId={params['geoId']}{industry_param}&keywords={quote_plus(params['keywords'])}&sortBy={params['sortBy']}"

    # Enterprise-grade validation + auto-correction attempts
    if not is_valid_linkedin_jobs_url(linkedin_url):
        # Attempt correction: re-normalize keywords and rebuild
        params["keywords"] = quote_plus(_normalize_boolean(_truncate_boolean(params["keywords"], MAX_KEYWORDS_LENGTH)))
        linkedin_url = f"{LINKEDIN_BASE_URL}?f_JT={params['f_JT']}&f_TPR={params['f_TPR']}&geoId={params['geoId']}{industry_param}&keywords={params['keywords']}&sortBy={params['sortBy']}"
        # If still invalid, drop non-essential params and retry
        if not is_valid_linkedin_jobs_url(linkedin_url):
            linkedin_url = f"{LINKEDIN_BASE_URL}?geoId={params['geoId']}&keywords={params['keywords']}&f_TPR={params['f_TPR']}"
        # Log validation outcome
        if run_id:
            try:
                from execution.supabase_logger import SupabaseLogger
                SupabaseLogger().update_phase(
                    run_id=run_id,
                    phase="linkedin_url_validation",
                    details={
                        "final_valid": is_valid_linkedin_jobs_url(linkedin_url),
                        "url_length": len(linkedin_url)
                    }
                )
            except Exception:
                pass
    # Sanity log for URL length and correctness
    if run_id:
        try:
            from execution.supabase_logger import SupabaseLogger
            SupabaseLogger().update_phase(
                run_id=run_id,
                phase="linkedin_url_generated",
                details={
                    "url_length": len(linkedin_url),
                    "has_keywords": "keywords=" in linkedin_url,
                    "contains_geo": f"geoId={geo_id}" in linkedin_url
                }
            )
        except Exception:
            pass
    
    return {
        "boolean_search": boolean_search,
        "linkedin_url": linkedin_url,
        "geo_id": geo_id
    }

def main():
    parser = argparse.ArgumentParser(description="Generate LinkedIn Boolean search URL")
    parser.add_argument("--icp", required=True, help="Path to ICP JSON file")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--run-id", help="Run ID for logging")
    args = parser.parse_args()
    
    # Load ICP data
    with open(args.icp, 'r') as f:
        icp_data = json.load(f)
    
    # Generate URL
    result = generate_linkedin_url(icp_data, run_id=args.run_id)
    
    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"✅ Generated LinkedIn URL")
    print(f"✅ Boolean search: {result['boolean_search']}")
    if len(result['boolean_search']) > MAX_KEYWORDS_LENGTH:
        print(f"⚠️ Truncated keywords to {MAX_KEYWORDS_LENGTH} chars for LinkedIn limit")
    # Local stdout validations
    print(f"🔎 Boolean length: {len(result['boolean_search'])}")
    print(f"🔎 Ends with ')': {str(result['boolean_search'].endswith(')'))}")
    print(f"✅ URL: {result['linkedin_url']}")
    print(f"🔎 URL length: {len(result['linkedin_url'])}")
    print(f"✅ Saved to: {output_path}")

if __name__ == "__main__":
    main()
