"""
Company Intelligence Enrichment
Scrapes company about pages and extracts insider details
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))
from execution.scrape_website import WebsiteScraper
from execution.call_openai import OpenAICaller

class CompanyIntelligence:
    def __init__(self):
        self.scraper = WebsiteScraper()
        self.openai_caller = OpenAICaller()
    
    def scrape_about_page(self, company_name: str, website: str, careers_url: str = None) -> str:
        """Smart scraping: use Exa URL first, then fallback to homepage → career page detection"""
        print(f"\n🔍 Enriching {company_name}...")
        
        base_url = website.rstrip('/')
        
        # Step 1: If Exa provided a careers_url, try that first
        if careers_url and careers_url != website:
            print(f"🔍 Trying Exa career page: {careers_url}...")
            content = self.scraper.scrape_url_content(careers_url)
            if content and len(content) > 500:
                print(f"  ✅ Scraped {len(content)} chars from Exa career page")
                return content
            else:
                print(f"  ⚠️ Exa career page failed, falling back to homepage...")
        
        # Step 2: Try homepage with Playwright (don't waste time on /about pages that may not exist)
        print(f"🎭 Trying homepage: {base_url}...")
        homepage_content = self.scraper.scrape_url_content(base_url)
        
        if not homepage_content or len(homepage_content) < 500:
            print(f"  ❌ Could not scrape homepage")
            return ""
        
        print(f"  ✅ Scraped homepage ({len(homepage_content)} chars)")
        
        # Step 3: Look for career page links from homepage
        print(f"🔍 Searching for career page links...")
        career_links = self.scraper.find_career_links(homepage_content, base_url)
        
        if career_links:
            print(f"  📋 Found {len(career_links)} potential career links")
            
            # Try to scrape career pages and check for job listings
            for career_url in career_links:
                print(f"  🔍 Checking career page: {career_url}...")
                career_content = self.scraper.scrape_url_content(career_url)
                
                if career_content and len(career_content) > 500:
                    # Check if page has actual job listings (look for job-related keywords)
                    job_indicators = ['apply', 'position', 'role', 'opening', 'vacancy', 'join our team']
                    content_lower = career_content.lower()
                    job_mentions = sum(1 for indicator in job_indicators if indicator in content_lower)
                    
                    if job_mentions >= 2:
                        print(f"    ✅ Found career page with job listings ({job_mentions} job indicators)")
                        # Combine homepage + career page for better context
                        return f"{homepage_content[:1500]}\n\n--- CAREER PAGE ---\n\n{career_content[:1500]}"
                    else:
                        print(f"    ⚠️ Career page found but no job listings detected")
        
        # Step 4: No career page found, use homepage content
        print(f"  ℹ️ Using homepage content (no active job listings found)")
        return homepage_content
    
    def extract_insider_details(self, company_name: str, description: str, 
                                scraped_content: str, employee_count: int) -> Dict[str, str]:
        """Extract insider intelligence using AI"""
        
        combined_content = f"""
Company: {company_name}
Employee Count: {employee_count}
LinkedIn Description: {description}
Website Content: {scraped_content[:2000] if scraped_content else 'Not available'}
"""
        
        prompt = f"""You are analyzing a company for a recruiter lead. Extract the most compelling insider intelligence that shows you deeply understand this company.

{combined_content}

Extract 2-3 insider details in a 1-2 sentence format. Focus on:
- SPECIFIC business model details (e.g., "FCA regulated derivatives advisory firm", "quant hedge fund and systematic asset manager")
- Exact role context with technical terminology (e.g., "The role sits in Derivative Risk Operations — daily reconciliation, lifecycle events, margin management")
- Recent concrete achievements with NUMBERS and DATES (e.g., "Just closed UK's largest IOS portfolio financing with Apollo", "posted 6 days ago")
- Notable clients, investors, or partnerships with NAMES (e.g., "backed by Sequoia", "trusted by 4 of top 10 UK banks")
- Market position or scale with METRICS (e.g., "200+ dApps secured", "£2.2bn AUM")

Return ONLY a JSON object:
{{
  "business_description": "1-2 sentence precise description using industry terminology",
  "insider_details": ["specific detail with numbers/dates", "another specific detail"]
}}

Be clinical and precise. Use real numbers, real dates, real names from the content. If you don't have specific data, don't make it up - use what's actually there.
"""
        
        result = self.openai_caller.call_with_retry(
            prompt, 
            temperature=0.2,  # Low temp for factual extraction
            max_tokens=300,
            model='gpt-4o-mini'
        )
        
        if result:
            try:
                # Parse JSON from response
                import re
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    intel = json.loads(json_match.group())
                    print(f"  ✅ Extracted intelligence")
                    return intel
            except:
                pass
        
        print(f"  ⚠️ Using basic description")
        return {
            "business_description": description[:200],
            "insider_details": []
        }
    
    def _enrich_single_company(self, company: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a single company (for parallel processing)"""
        company_name = company["company_name"]
        website = company.get("company_website", "")
        careers_url = company.get("careers_url", "")
        description = company.get("company_description", "")
        employee_count = company.get("employee_count", 0)
        
        # Scrape website for more context
        scraped_content = ""
        if website:
            scraped_content = self.scrape_about_page(company_name, website, careers_url)
        
        # Extract insider intelligence
        intel = self.extract_insider_details(
            company_name, 
            description, 
            scraped_content,
            employee_count
        )
        
        # Add intelligence to company data
        enriched_company = company.copy()
        enriched_company["insider_intelligence"] = intel
        return enriched_company
    
    def enrich_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich companies with insider intelligence using parallel processing"""
        print(f"🔍 Enriching {len(companies)} companies with insider intelligence (parallel)...\n")
        
        enriched = []
        
        # Use ThreadPoolExecutor for parallel processing
        # Limit to 5 concurrent threads to avoid overwhelming APIs
        max_workers = min(5, len(companies))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all enrichment tasks
            future_to_company = {
                executor.submit(self._enrich_single_company, company): company 
                for company in companies
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_company):
                company = future_to_company[future]
                try:
                    enriched_company = future.result()
                    enriched.append(enriched_company)
                except Exception as e:
                    print(f"⚠️ Enrichment failed for {company.get('company_name', 'Unknown')}: {e}")
                    # Add company without enrichment
                    enriched_company = company.copy()
                    enriched_company["insider_intelligence"] = {
                        "business_description": company.get("company_description", "")[:200],
                        "insider_details": []
                    }
                    enriched.append(enriched_company)
        
        print(f"\n✅ Completed enrichment of {len(enriched)} companies")
        return enriched

def main():
    parser = argparse.ArgumentParser(description="Enrich companies with insider intelligence")
    parser.add_argument("--input", required=True, help="Input companies JSON")
    parser.add_argument("--output", required=True, help="Output enriched companies JSON")
    
    args = parser.parse_args()
    
    # Load companies
    with open(args.input, 'r') as f:
        companies = json.load(f)
    
    # Enrich
    enricher = CompanyIntelligence()
    enriched = enricher.enrich_companies(companies)
    
    # Save
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(enriched, f, indent=2)
    
    print(f"\n✅ Enriched {len(enriched)} companies")
    print(f"✅ Saved to {output_path}")

if __name__ == "__main__":
    main()
