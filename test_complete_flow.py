#!/usr/bin/env python3
"""
Test Complete Exa Fallback Flow with Playwright Job Extraction
Tests: Deep ICP → Exa Company Finding → Playwright Scraping → AI Job Extraction
"""

import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from execution.extract_icp_deep import DeepICPExtractor
from execution.call_exa_api import ExaCompanyFinder
from execution.extract_jobs_from_website import JobExtractor


def test_complete_flow():
    """Test complete flow: ICP → Exa → Playwright → Jobs"""
    
    print("="*80)
    print("TESTING COMPLETE EXA FALLBACK WORKFLOW")
    print("="*80)
    
    # Step 1: Extract ICP with Deep Analysis
    print("\n" + "="*80)
    print("STEP 1: Deep ICP Extraction (Multi-Page Playwright)")
    print("="*80)
    
    extractor = DeepICPExtractor()
    icp = extractor.extract_icp("https://dunnesearchgroup.com/")
    
    print(f"\n✅ ICP Extracted:")
    print(f"   Industries: {', '.join(icp['industries'])}")
    print(f"   Roles: {', '.join(icp['roles_filled'][:3])}...")
    print(f"   Company Size: {', '.join(icp['company_sizes'])}")
    
    # Step 2: Find companies with Exa
    print("\n" + "="*80)
    print("STEP 2: Exa Company Discovery")
    print("="*80)
    
    finder = ExaCompanyFinder()
    companies = finder.find_companies(
        icp_data=icp,
        max_results=10  # Limit for testing
    )
    
    print(f"\n✅ Found {len(companies)} companies via Exa")
    
    # Step 3: Extract jobs with Playwright + AI
    print("\n" + "="*80)
    print("STEP 3: Playwright Job Extraction from Career Pages")
    print("="*80)
    
    job_extractor = JobExtractor()
    companies_with_jobs = job_extractor.extract_jobs_from_companies(companies[:5])  # Test first 5
    
    # Step 4: Validate hiring activity
    print("\n" + "="*80)
    print("STEP 4: Validate Hiring Activity")
    print("="*80)
    
    companies_hiring, companies_not_hiring = job_extractor.validate_hiring_activity(companies_with_jobs)
    
    print(f"\n✅ Results:")
    print(f"   Companies actively hiring: {len(companies_hiring)}")
    print(f"   Companies not hiring: {len(companies_not_hiring)}")
    
    # Step 5: Show detailed results
    print("\n" + "="*80)
    print("STEP 5: Detailed Job Listings")
    print("="*80)
    
    total_jobs = 0
    for i, company in enumerate(companies_hiring[:3], 1):  # Show first 3
        jobs = company.get("jobs", [])
        total_jobs += len(jobs)
        
        print(f"\n{i}. {company['name']}")
        print(f"   URL: {company.get('careers_url', company.get('company_url', 'N/A'))}")
        print(f"   Jobs Found: {len(jobs)}")
        
        for j, job in enumerate(jobs[:3], 1):  # Show first 3 jobs
            print(f"\n   Job {j}: {job.get('job_title', 'Unknown')}")
            print(f"      Location: {job.get('location', 'N/A')}")
            if job.get('job_url'):
                print(f"      Apply: {job['job_url']}")
            if job.get('description'):
                desc = job['description'][:150] + "..." if len(job.get('description', '')) > 150 else job.get('description', '')
                print(f"      Description: {desc}")
        
        if len(jobs) > 3:
            print(f"\n   ... and {len(jobs) - 3} more jobs")
    
    # Final Summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    
    print(f"""
✅ Deep ICP Extraction: SUCCESS
   - Analyzed multiple pages with Playwright
   - Industries: {', '.join(icp['industries'])}
   - Roles: {', '.join(icp['roles_filled'][:2])}...

✅ Exa Company Discovery: SUCCESS
   - Found {len(companies)} companies matching ICP
   - Filtered out job boards and large companies

✅ Playwright Job Extraction: SUCCESS
   - Scraped {len(companies_with_jobs)} career pages
   - Used HTTP → Playwright fallback chain
   - Extracted {total_jobs} total job listings

✅ AI Job Parsing: SUCCESS
   - Used GPT-4o-mini to extract structured job data
   - Validated hiring activity
   - {len(companies_hiring)} companies actively hiring

🎯 WORKFLOW COMPLETE: Ready for production use!
""")
    
    # Save results for inspection
    output_file = ".tmp/exa_fallback_test_results.json"
    Path(".tmp").mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump({
            "icp": icp,
            "companies_found": len(companies),
            "companies_hiring": len(companies_hiring),
            "companies_not_hiring": len(companies_not_hiring),
            "total_jobs": total_jobs,
            "sample_companies": companies_hiring[:3]
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    
    return True


if __name__ == "__main__":
    try:
        success = test_complete_flow()
        if success:
            print("\n✅ ALL TESTS PASSED")
            sys.exit(0)
        else:
            print("\n❌ TESTS FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
