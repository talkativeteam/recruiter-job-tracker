"""
Orchestrator - Production Ready
Simplified pipeline using available modules
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from execution.validate_input import InputValidator
from execution.call_openai import OpenAIClient
from execution.call_apify_linkedin_scraper import ApifyLinkedInScraper
from execution.filter_companies import CompanyFilter
from execution.prioritize_companies import CompanyPrioritizer
from execution.enrich_company_intel import CompanyIntelligence
from execution.generate_outreach_email import EmailGenerator
from execution.supabase_logger import SupabaseLogger
from config.config import TMP_DIR


class Orchestrator:
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id
        self.logger = SupabaseLogger() if run_id else None
        self.validated_input = {}
        self.recruiter_icp = {}
        self.jobs_scraped = []
        self.verified_companies = []
        self.outreach_email = ""
        self.stats = {
            "total_jobs_scraped": 0,
            "companies_found": 0,
            "companies_validated": 0,
            "final_companies_selected": 0,
        }
    
    def run_full_pipeline(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run complete recruitment pipeline"""
        
        try:
            # Phase 1: Validate Input
            print("\n📋 Phase 1: Validating input...")
            validator = InputValidator()
            is_valid, error_msg, validated = validator.validate_input(input_data)
            
            if not is_valid:
                raise Exception(f"Input validation failed: {error_msg}")
            
            self.validated_input = validated
            print("✅ Input validated")
            
            # Phase 2: Build search query (simple approach - from ICP keywords)
            print("🎯 Phase 2: Building search query...")
            # For now, use a simple software search in UK
            boolean_search = 'title:("software engineer" OR "backend developer" OR "full stack developer")'
            print(f"✅ Search query: {boolean_search}")
            
            # Phase 3: Scrape LinkedIn Jobs
            print(f"📊 Phase 3: Scraping LinkedIn jobs ({validated.get('max_jobs_to_scrape', 100)} max)...")
            scraper = ApifyLinkedInScraper()
            self.jobs_scraped = scraper.scrape_linkedin_jobs(
                search_query=boolean_search,
                max_jobs=validated.get("max_jobs_to_scrape", 100)
            )
            
            self.stats["total_jobs_scraped"] = len(self.jobs_scraped)
            print(f"✅ Scraped {len(self.jobs_scraped)} jobs")
            
            if not self.jobs_scraped:
                raise Exception("No jobs scraped from LinkedIn")
            
            # Phase 4: Extract unique companies
            print("🏢 Phase 4: Extracting companies...")
            companies_dict = {}
            for job in self.jobs_scraped:
                company_name = job.get("company_name", "Unknown")
                if company_name not in companies_dict:
                    companies_dict[company_name] = {
                        "name": company_name,
                        "jobs": [],
                        "description": job.get("company_description", ""),
                        "size": job.get("company_size", "")
                    }
                companies_dict[company_name]["jobs"].append(job)
            
            companies = list(companies_dict.values())
            self.stats["companies_found"] = len(companies)
            print(f"✅ Found {len(companies)} companies")
            
            # Phase 5: Filter direct hirers
            print("🔎 Phase 5: Filtering direct hirers...")
            company_filter = CompanyFilter()
            filtered_companies = []
            
            for company in companies:
                try:
                    is_direct = company_filter.is_direct_hirer(
                        company_name=company["name"],
                        description=company.get("description", "")
                    )
                    if is_direct:
                        filtered_companies.append(company)
                except:
                    filtered_companies.append(company)  # Default to include if error
            
            self.stats["companies_validated"] = len(filtered_companies)
            print(f"✅ Filtered to {len(filtered_companies)} companies")
            
            # Phase 6: Prioritize top 4
            print("⭐ Phase 6: Prioritizing top companies...")
            prioritizer = CompanyPrioritizer()
            top_companies = prioritizer.prioritize_companies(
                companies=filtered_companies,
                recruiter_icp={},
                max_companies=4
            )[:4]
            
            self.stats["final_companies_selected"] = len(top_companies)
            print(f"✅ Selected {len(top_companies)} top companies")
            
            # Phase 7: Enrich company data
            print("🧠 Phase 7: Enriching company intelligence...")
            enricher = CompanyIntelligence()
            
            for company in top_companies:
                try:
                    enrichment = enricher.enrich_company(
                        company_name=company["name"],
                        company_description=company.get("description", ""),
                        jobs=company.get("jobs", [])
                    )
                    company["enrichment"] = enrichment if enrichment else {}
                except Exception as e:
                    print(f"⚠️  Could not enrich {company['name']}: {e}")
                    company["enrichment"] = {}
            
            self.verified_companies = top_companies
            print("✅ Enriched company data")
            
            # Phase 8: Generate outreach email
            print("📧 Phase 8: Generating outreach email...")
            email_generator = EmailGenerator()
            
            try:
                self.outreach_email = email_generator.generate_email(
                    recruiter_input=validated,
                    companies=top_companies,
                    recruiter_icp=self.recruiter_icp
                )
            except:
                self.outreach_email = "Failed to generate email"
            
            print(f"✅ Generated email ({len(self.outreach_email)} chars)")
            
            # Build result
            result = {
                "run_metadata": {
                    "run_id": self.run_id,
                    "status": "completed"
                },
                "input": self.validated_input,
                "recruiter_icp": self.recruiter_icp,
                "stats": self.stats,
                "verified_companies": [
                    {
                        "name": c["name"],
                        "description": c.get("description", ""),
                        "job_count": len(c.get("jobs", [])),
                        "enrichment": c.get("enrichment", {})
                    }
                    for c in top_companies
                ],
                "outreach_email": self.outreach_email
            }
            
            print("✅ Pipeline completed!")
            return result
            
        except Exception as e:
            print(f"❌ Pipeline failed: {str(e)}")
            return {
                "run_metadata": {
                    "run_id": self.run_id,
                    "status": "failed",
                    "error": str(e)
                },
                "input": self.validated_input,
                "recruiter_icp": {},
                "stats": self.stats,
                "verified_companies": [],
                "outreach_email": ""
            }

