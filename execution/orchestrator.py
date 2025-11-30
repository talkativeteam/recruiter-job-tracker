"""
Orchestrator
Coordinates the full recruitment pipeline
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from execution.validate_input import InputValidator
from execution.identify_icp import ICPIdentifier
from execution.generate_boolean_search import BooleanSearchGenerator
from execution.scrape_linkedin_jobs import LinkedInJobScraper
from execution.validate_direct_hirer import DirectHirerValidator
from execution.validate_icp_fit import ICPFitValidator
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
        self.companies = []
        self.verified_companies = []
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
            
            # Phase 2: Identify ICP
            print("🎯 Phase 2: Identifying ICP from website...")
            icp_identifier = ICPIdentifier(run_id=self.run_id)
            self.recruiter_icp = icp_identifier.identify_icp(validated.get("client_website"))
            
            if not self.recruiter_icp:
                raise Exception("Failed to identify recruiter ICP")
            
            # Phase 3: Generate Boolean Search
            print("🔍 Phase 3: Generating Boolean search...")
            search_generator = BooleanSearchGenerator(run_id=self.run_id)
            search_data = search_generator.generate_boolean_search(self.recruiter_icp)
            
            if not search_data:
                raise Exception("Failed to generate Boolean search")
            
            # Phase 4: Scrape LinkedIn Jobs
            print(f"📊 Phase 4: Scraping LinkedIn jobs ({validated.get('max_jobs_to_scrape', 100)} max)...")
            scraper = LinkedInJobScraper(run_id=self.run_id)
            self.jobs_scraped = scraper.scrape_linkedin_jobs(
                search_data.get("boolean_search"),
                max_jobs=validated.get("max_jobs_to_scrape", 100)
            )
            
            self.stats["total_jobs_scraped"] = len(self.jobs_scraped)
            
            if not self.jobs_scraped:
                raise Exception("No jobs scraped from LinkedIn")
            
            # Phase 5-7: Validate & Filter Companies
            print("✅ Phase 5-7: Validating and filtering companies...")
            direct_hirer_validator = DirectHirerValidator(run_id=self.run_id)
            icp_fit_validator = ICPFitValidator(run_id=self.run_id)
            
            for job in self.jobs_scraped:
                company_name = job.get("company_name", "Unknown")
                
                # Check if direct hirer
                is_direct = direct_hirer_validator.validate_direct_hirer(
                    company_name,
                    job.get("company_description", ""),
                    job.get("company_industry", ""),
                    job.get("job_description", "")
                )
                
                if not is_direct:
                    continue
                
                # Check ICP fit
                icp_fit = icp_fit_validator.validate_icp_fit(
                    self.recruiter_icp,
                    company_name,
                    job.get("company_description", ""),
                    job.get("company_industry", ""),
                    job.get("employee_count", 0),
                    job.get("company_location", ""),
                    [job.get("job_title", "")]
                )
                
                if icp_fit.get("fits_icp"):
                    if not any(c["company_name"] == company_name for c in self.companies):
                        job["jobs"] = [job]
                        self.companies.append(job)
                    else:
                        # Add job to existing company
                        for c in self.companies:
                            if c["company_name"] == company_name:
                                c["jobs"].append(job)
            
            self.stats["companies_found"] = len(self.companies)
            self.stats["companies_validated"] = len(self.companies)
            
            # Phase 8: Prioritize Companies
            print("⭐ Phase 8: Prioritizing companies...")
            prioritizer = CompanyPrioritizer(run_id=self.run_id)
            selected_companies = prioritizer.prioritize_companies(
                self.companies,
                self.recruiter_icp,
                top_n=4
            )
            
            # Phase 9: Enrich Company Intel
            print("🔬 Phase 9: Enriching company intelligence...")
            enricher = CompanyIntelligence(run_id=self.run_id)
            enriched_companies = []
            
            for company in selected_companies:
                enriched = enricher.enrich_company(company)
                if enriched:
                    enriched_companies.append(enriched)
            
            self.verified_companies = enriched_companies
            self.stats["final_companies_selected"] = len(enriched_companies)
            
            # Phase 10: Generate Outreach Email
            print("📧 Phase 10: Generating outreach email...")
            email_generator = EmailGenerator(run_id=self.run_id)
            email_body = email_generator.generate_email_content(
                enriched_companies,
                {},  # decision_makers not used
                self.validated_input
            )
            
            # Build result
            result = {
                "status": "completed",
                "recruiter_icp": self.recruiter_icp,
                "stats": self.stats,
                "verified_companies": self.verified_companies,
                "outreach_email_body": email_body,
                "cost_estimate": "$0.40 (estimated)",
            }
            
            print("✅ Pipeline completed successfully!")
            return result
        
        except Exception as e:
            print(f"❌ Pipeline failed: {e}")
            raise

def main():
    """Test the orchestrator locally"""
    # Load sample input
    sample_file = Path(__file__).parent.parent / "sample_input.json"
    with open(sample_file) as f:
        input_data = json.load(f)
    
    # Run pipeline
    orchestrator = Orchestrator()
    result = orchestrator.run_full_pipeline(input_data)
    
    # Save result
    output_file = Path(__file__).parent.parent / ".tmp" / "pipeline_result.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\n✅ Result saved to {output_file}")

if __name__ == "__main__":
    main()
