"""
Demo: Show actual Exa API response
Run this to see real Exa results for a sample ICP
"""

import sys
import json
from pathlib import Path

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent))

from execution.call_exa_api import ExaCompanyFinder


def demo_exa_response():
    """Show actual Exa API response for Smile Digital Talent ICP"""
    
    # Sample ICP (from Smile Digital Talent - digital agency recruiter)
    icp_data = {
        "industries": ["Digital Agencies", "Creative Agencies", "Marketing Agencies"],
        "roles_filled": [
            "Creative Content Strategist",
            "Account Director",
            "Paid Social Manager",
            "Digital Marketing Manager",
            "SEO Specialist",
            "Product Manager"
        ],
        "company_sizes": ["10-100 employees"],
        "geographies": ["United Kingdom", "Birmingham", "London"]
    }
    
    print("=" * 80)
    print("EXA API RESPONSE DEMO")
    print("=" * 80)
    print("\n📋 Testing with ICP:")
    print(json.dumps(icp_data, indent=2))
    
    print("\n🔍 Calling Exa API...")
    print("-" * 80)
    
    finder = ExaCompanyFinder()
    
    # This will call the real Exa API
    companies = finder.find_companies(icp_data, max_results=5)  # Only 5 to save costs
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    if not companies:
        print("❌ No companies found")
        return
    
    print(f"\n✅ Found {len(companies)} companies:\n")
    
    for i, company in enumerate(companies, 1):
        print(f"{i}. {company['name']}")
        print(f"   URL: {company.get('company_url', 'N/A')}")
        print(f"   Careers: {company.get('careers_url', 'N/A')}")
        print(f"   Description: {company.get('description', 'N/A')[:150]}...")
        print(f"   Source: {company.get('source', 'N/A')}")
        print()
    
    print("=" * 80)
    print("RAW DATA (First Result)")
    print("=" * 80)
    print(json.dumps(companies[0], indent=2))
    
    print("\n" + "=" * 80)
    print(f"💰 Cost: ${finder.get_cost_estimate():.4f}")
    print("=" * 80)


if __name__ == "__main__":
    demo_exa_response()
