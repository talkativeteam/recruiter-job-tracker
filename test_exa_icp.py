#!/usr/bin/env python3
"""
Test Exa API with correct biotech/pharmaceutical + sales/marketing ICP
"""

import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from execution.call_exa_api import ExaCompanyFinder

def test_exa_with_correct_icp():
    """Test Exa with biotech/pharma + sales/marketing ICP"""
    
    # ICP data extracted from Vince Dunne's website
    icp_data = {
        "industries": [
            "Biotech",
            "Pharmaceutical",
            "Healthcare Technology"
        ],
        "company_sizes": [
            "10-100 employees",
            "100-500 employees"
        ],
        "geographies": [
            "United States",
            "California"
        ],
        "roles_filled": [
            "Sales Director",
            "Marketing Manager",
            "Business Development Manager",
            "VP of Sales",
            "Head of Sales"
        ],
        "boolean_keywords": [
            "Sales Director",
            "Sales Manager",
            "Marketing Manager",
            "Business Development Manager",
            "VP Sales",
            "Head of Sales"
        ],
        "primary_country": "United States",
        "linkedin_geo_id": "103644278"
    }
    
    print("="*60)
    print("Testing Exa API with Biotech/Pharma + Sales/Marketing ICP")
    print("="*60)
    print("\n📋 ICP Data:")
    print(f"  Industries: {', '.join(icp_data['industries'])}")
    print(f"  Roles: {', '.join(icp_data['roles_filled'])}")
    print(f"  Company Size: {', '.join(icp_data['company_sizes'])}")
    print(f"  Geography: {', '.join(icp_data['geographies'])}")
    
    # Find companies with Exa
    finder = ExaCompanyFinder()
    companies = finder.find_companies(
        icp_data=icp_data,
        max_results=20
    )
    
    print(f"\n✅ Found {len(companies)} companies")
    print("\n" + "="*60)
    print("COMPANIES:")
    print("="*60)
    
    for i, company in enumerate(companies[:10], 1):  # Show first 10
        print(f"\n{i}. {company.get('name', company.get('company_name', 'Unknown'))}")
        print(f"   Domain: {company.get('domain', company.get('company_domain', 'N/A'))}")
        print(f"   Industry: {company.get('industry', 'N/A')}")
        if company.get('url'):
            print(f"   URL: {company['url']}")
    
    if len(companies) > 10:
        print(f"\n... and {len(companies) - 10} more companies")


if __name__ == "__main__":
    test_exa_with_correct_icp()
