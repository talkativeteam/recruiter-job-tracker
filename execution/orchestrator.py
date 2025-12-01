"""
Orchestrator - Full 10-Phase Pipeline
Recruiter ICP Job Tracker for Talkative
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from execution.validate_input import InputValidator
from execution.call_openai import OpenAICaller
from execution.call_apify_linkedin_scraper import ApifyLinkedInScraper
from execution.scrape_website import WebsiteScraper
from execution.filter_companies import CompanyFilter
from execution.prioritize_companies import CompanyPrioritizer
from execution.enrich_company_intel import CompanyIntelligence
from execution.generate_outreach_email import EmailGenerator
from execution.supabase_logger import SupabaseLogger
from execution.send_webhook_response import send_webhook
from config import ai_prompts
from config.config import TMP_DIR


class Orchestrator:
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id
        self.logger = SupabaseLogger() if run_id else None
        self.validated_input = {}
        self.recruiter_icp = {}
        self.boolean_search = ""
        self.jobs_scraped = []
        self.verified_companies = []
        self.outreach_email = ""
        self.stats = {
            "total_jobs_scraped": 0,
            "companies_found": 0,
            "companies_validated": 0,
            "final_companies_selected": 0,
            "total_cost": "$0.00"
        }
    
    def run_full_pipeline(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run complete 10-phase recruitment pipeline"""
        
        try:
            # Phase 1: Validate Input
            print("\n📋 Phase 1: Validating input...")
            validator = InputValidator()
            is_valid, error_msg, validated = validator.validate_input(input_data)
            
            if not is_valid:
                raise Exception(f"Input validation failed: {error_msg}")
            
            self.validated_input = validated
            print("✅ Input validated successfully")
            
            # Phase 2: Extract ICP from Client Website
            print("🎯 Phase 2: Extracting recruiter ICP from client website...")
            openai = OpenAICaller(run_id=self.run_id)
            
            # Scrape client website
            website_scraper = WebsiteScraper(run_id=self.run_id)
            website_content = website_scraper.scrape_http(validated.get("client_website", ""))[1] or validated.get("client_website", "")
            
            # Generate ICP extraction prompt
            icp_prompt = ai_prompts.format_icp_prompt(website_content or validated.get("client_website", ""))
            
            # Call OpenAI to extract ICP
            icp_response = openai.call_with_retry(
                prompt=icp_prompt,
                model="gpt-4o-mini",
                response_format="json"
            )
            
            try:
                self.recruiter_icp = json.loads(icp_response)
            except:
                self.recruiter_icp = {
                    "industries": [],
                    "roles": [],
                    "skills": [],
                    "seniority_levels": ["mid", "senior"],
                    "keywords": []
                }
            
            print(f"✅ ICP extracted: {json.dumps(self.recruiter_icp, indent=2)}")
            
            # Phase 3: Generate Boolean Search Query
            print("🔍 Phase 3: Generating Boolean search query...")
            boolean_prompt = ai_prompts.format_boolean_search_prompt(self.recruiter_icp)
            
            boolean_response = openai.call_with_retry(
                prompt=boolean_prompt,
                model="gpt-4o-mini",
                response_format="text"
            )
            
            self.boolean_search = boolean_response.strip()
            print(f"✅ Boolean search: {self.boolean_search}")
            
            # Phase 4: Scrape LinkedIn Jobs
            print(f"📊 Phase 4: Scraping LinkedIn jobs ({validated.get('max_jobs_to_scrape', 100)} max)...")
            scraper = ApifyLinkedInScraper(run_id=self.run_id)
            
            # Build LinkedIn search URL (UK-based, Software industry, past week)
            linkedin_url = "https://www.linkedin.com/jobs/search/?keywords=" + self.boolean_search.replace(" ", "%20") + "&location=United%20Kingdom&f_I=4&f_TPR=r604800"
            
            # Apify requires minimum 100 jobs
            jobs_to_scrape = max(100, validated.get('max_jobs_to_scrape', 100))
            
            self.jobs_scraped = scraper.scrape_jobs(
                linkedin_url=linkedin_url,
                max_jobs=jobs_to_scrape
            )
            
            self.stats["total_jobs_scraped"] = len(self.jobs_scraped)
            print(f"✅ Scraped {len(self.jobs_scraped)} jobs from LinkedIn")
            
            if not self.jobs_scraped:
                raise Exception("No jobs scraped from LinkedIn")
            
            # Phase 5: Extract Unique Companies
            print("🏢 Phase 5: Extracting unique companies from job postings...")
            companies_dict = {}
            for job in self.jobs_scraped:
                company_name = job.get("company", "Unknown")
                if company_name not in companies_dict:
                    companies_dict[company_name] = {
                        "name": company_name,
                        "jobs": [],
                        "description": job.get("description", ""),
                        "company_url": job.get("companyUrl", "")
                    }
                companies_dict[company_name]["jobs"].append(job)
            
            companies = list(companies_dict.values())
            self.stats["companies_found"] = len(companies)
            print(f"✅ Found {len(companies)} unique companies")
            
            # Phase 6: Validate Direct Hirers (Not Staffing Agencies)
            print("🔎 Phase 6: Validating direct hirers...")
            company_filter = CompanyFilter(run_id=self.run_id)
            filtered_companies = []
            
            for company in companies:
                # Check if direct hirer using AI
                direct_hirer_prompt = ai_prompts.format_direct_hirer_prompt(
                    company["name"],
                    company.get("description", ""),
                    "",  # industry
                    " ".join([j.get("description", "") for j in company["jobs"][:2]])
                )
                
                response = openai.call_with_retry(
                    prompt=direct_hirer_prompt,
                    model="gpt-4o-mini",
                    response_format="json"
                )
                
                try:
                    result = json.loads(response)
                    if result.get("is_direct_hirer", False):
                        filtered_companies.append(company)
                except:
                    filtered_companies.append(company)  # Default include if error
            
            self.stats["companies_validated"] = len(filtered_companies)
            print(f"✅ Validated {len(filtered_companies)} direct hirers")
            
            # Phase 7: Prioritize Top Companies
            print("⭐ Phase 7: Prioritizing top companies...")
            prioritizer = CompanyPrioritizer(run_id=self.run_id)
            top_companies = prioritizer.select_top_n(
                companies=filtered_companies,
                n=4,
                icp_data=self.recruiter_icp
            )
            
            self.stats["final_companies_selected"] = len(top_companies)
            print(f"✅ Selected top {len(top_companies)} companies")
            
            # Phase 8: Enrich Company Intelligence (Website scraping + AI analysis)
            print("🧠 Phase 8: Enriching company intelligence...")
            enricher = CompanyIntelligence(run_id=self.run_id)
            
            for company in top_companies:
                try:
                    # Scrape company website about page
                    website_scraper = WebsiteScraper(run_id=self.run_id)
                    company_url = company.get("company_url", "https://www." + company["name"].lower().replace(" ", "") + ".com")
                    about_page = website_scraper.scrape_http(company_url)[1] or ""
                    
                    # Extract company intelligence
                    enrichment = enricher.enrich_company(
                        company_name=company["name"],
                        company_website_content=about_page,
                        jobs=company["jobs"]
                    )
                    company["enrichment"] = enrichment if enrichment else {}
                except Exception as e:
                    print(f"⚠️ Could not enrich {company['name']}: {e}")
                    company["enrichment"] = {}
            
            self.verified_companies = top_companies
            print(f"✅ Enriched {len(top_companies)} companies")
            
            # Phase 9: Generate Outreach Email
            print("📧 Phase 9: Generating personalized outreach email...")
            email_generator = EmailGenerator(run_id=self.run_id)
            
            # Format companies data for email
            companies_data = [
                {
                    "name": c["name"],
                    "description": c.get("description", ""),
                    "jobs": c.get("jobs", []),
                    "enrichment": c.get("enrichment", {}),
                    "website": c.get("company_url", "")
                }
                for c in top_companies
            ]
            
            # Generate email
            self.outreach_email = email_generator.generate_email(
                recruiter_input=validated,
                companies=companies_data,
                recruiter_icp=self.recruiter_icp
            )
            
            print(f"✅ Generated outreach email ({len(self.outreach_email)} characters)")
            
            # Phase 10: Send Webhook Response
            print("🚀 Phase 10: Sending webhook response...")
            
            result = {
                "run_metadata": {
                    "run_id": self.run_id,
                    "status": "completed",
                    "pipeline_version": "10-phase-full"
                },
                "input": self.validated_input,
                "recruiter_icp": self.recruiter_icp,
                "boolean_search_used": self.boolean_search,
                "stats": self.stats,
                "verified_companies": [
                    {
                        "name": c["name"],
                        "description": c.get("description", ""),
                        "job_count": len(c.get("jobs", [])),
                        "company_website": c.get("company_url", ""),
                        "enrichment": c.get("enrichment", {})
                    }
                    for c in top_companies
                ],
                "outreach_email": self.outreach_email
            }
            
            # Send to webhook if URL provided
            webhook_url = os.getenv("WEBHOOK_URL")
            if webhook_url:
                send_webhook(webhook_url, result)
            
            print("✅ Pipeline completed successfully!")
            print(f"✅ All 10 phases executed successfully")
            return result
            
        except Exception as e:
            print(f"❌ Pipeline failed: {str(e)}")
            import traceback
            traceback.print_exc()
            
            error_result = {
                "run_metadata": {
                    "run_id": self.run_id,
                    "status": "failed",
                    "error": str(e),
                    "pipeline_version": "10-phase-full"
                },
                "input": self.validated_input,
                "recruiter_icp": self.recruiter_icp,
                "boolean_search_used": self.boolean_search,
                "stats": self.stats,
                "verified_companies": [],
                "outreach_email": ""
            }
            
            if self.logger and self.run_id:
                self.logger.mark_failed(self.run_id, str(e), "pipeline")
            
            return error_result

