"""
Company Intelligence Enrichment
Scrapes company about pages and extracts insider details
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))
from execution.scrape_website import WebsiteScraper
from execution.call_openai import OpenAICaller

class CompanyIntelligence:
    def __init__(self):
        self.scraper = WebsiteScraper()
        self.openai_caller = OpenAICaller()
    
    def scrape_about_page(self, company_name: str, website: str) -> str:
        """Try to scrape company about page or homepage"""
        print(f"\n🔍 Enriching {company_name}...")
        
        # Try about page first, fall back to homepage
        urls_to_try = [
            f"{website.rstrip('/')}/about",
            f"{website.rstrip('/')}/about-us",
            website
        ]
        
        for url in urls_to_try:
            try:
                content = self.scraper.scrape(url, f".tmp/{company_name.replace(' ', '_')}_scrape.json")
                if content and len(content) > 200:
                    print(f"  ✅ Scraped {len(content)} chars from {url}")
                    return content
            except Exception as e:
                continue
        
        print(f"  ⚠️ Could not scrape website, using existing description")
        return ""
    
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
    
    def enrich_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich companies with insider intelligence"""
        print(f"🔍 Enriching {len(companies)} companies with insider intelligence...\n")
        
        enriched = []
        
        for company in companies:
            company_name = company["company_name"]
            website = company.get("company_website", "")
            description = company.get("company_description", "")
            employee_count = company.get("employee_count", 0)
            
            # Scrape website for more context
            scraped_content = ""
            if website:
                scraped_content = self.scrape_about_page(company_name, website)
            
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
            enriched.append(enriched_company)
        
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
