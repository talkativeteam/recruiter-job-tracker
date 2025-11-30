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
    geo_id = icp_data.get("linkedin_geo_id", "103644278")  # Default to US
    
    # Build LinkedIn URL parameters
    params = {
        "f_JT": LINKEDIN_JOB_TYPE,  # Full-time
        "f_TPR": "r604800",  # Past week (r604800) - more results than 24h (r86400)
        "geoId": geo_id,
        "keywords": boolean_search,
        "sortBy": "R"  # Relevance
    }
    
    # Add industry filter if industry is Software
    industries = icp_data.get("industries", [])
    if "Software" in industries or "Technology" in industries:
        params["f_I"] = "4"  # Software Development industry filter
    
    # Manual URL construction (urlencode doesn't handle parentheses properly)
    industry_param = f"&f_I={params['f_I']}" if "f_I" in params else ""
    linkedin_url = f"{LINKEDIN_BASE_URL}?f_JT={params['f_JT']}&f_TPR={params['f_TPR']}&geoId={params['geoId']}{industry_param}&keywords={quote_plus(params['keywords'])}&sortBy={params['sortBy']}"
    
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
    print(f"✅ URL: {result['linkedin_url']}")
    print(f"✅ Saved to: {output_path}")

if __name__ == "__main__":
    main()
