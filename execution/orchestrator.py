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
from execution.find_contact_person import DecisionMakerFinder
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
        self.openai_caller = None  # Will be initialized once
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
            
            # Initialize OpenAI caller (reuse throughout pipeline)
            self.openai_caller = OpenAICaller(run_id=self.run_id)
            
            # Phase 2: Extract ICP from Client Website
            print("🎯 Phase 2: Extracting recruiter ICP from client website...")
            openai = self.openai_caller
            
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
            
            # Apify requires minimum 100 jobs
            jobs_to_scrape = max(100, validated.get('max_jobs_to_scrape', 100))
            minimum_acceptable_jobs = 30  # Fallback to 7 days if fewer than 30 jobs found
            
            # Try 24 hours first (fresher results)
            print(f"🔄 Attempt 1: Scraping past 24 hours (r86400)...")
            linkedin_url_24h = "https://www.linkedin.com/jobs/search/?keywords=" + self.boolean_search.replace(" ", "%20") + "&location=United%20Kingdom&f_I=4&f_TPR=r86400"
            
            self.jobs_scraped = scraper.scrape_jobs(
                linkedin_url=linkedin_url_24h,
                max_jobs=jobs_to_scrape
            )
            
            # If insufficient results, fallback to 7 days
            if len(self.jobs_scraped) < minimum_acceptable_jobs:
                print(f"⚠️ Only {len(self.jobs_scraped)} jobs found in 24h (need {minimum_acceptable_jobs})")
                print(f"🔄 Attempt 2: Retrying with past 7 days (r604800)...")
                linkedin_url_7d = "https://www.linkedin.com/jobs/search/?keywords=" + self.boolean_search.replace(" ", "%20") + "&location=United%20Kingdom&f_I=4&f_TPR=r604800"
                
                self.jobs_scraped = scraper.scrape_jobs(
                    linkedin_url=linkedin_url_7d,
                    max_jobs=jobs_to_scrape
                )
            else:
                print(f"✅ Got {len(self.jobs_scraped)} jobs in 24h - using fresh results")
            
            self.stats["total_jobs_scraped"] = len(self.jobs_scraped)
            print(f"✅ Scraped {len(self.jobs_scraped)} jobs from LinkedIn")
            
            if not self.jobs_scraped:
                raise Exception("No jobs scraped from LinkedIn")
            
            # Phase 5: Extract Unique Companies
            print("🏢 Phase 5: Extracting unique companies from job postings...")
            companies_dict = {}
            for job in self.jobs_scraped:
                company_name = job.get("companyName", "Unknown")
                if company_name not in companies_dict:
                    companies_dict[company_name] = {
                        "name": company_name,
                        "jobs": [],
                        "description": job.get("companyDescription", ""),
                        "company_url": job.get("companyWebsite", "")
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
                    company.get("industry", ""),  # Pass available industry
                    " ".join([j.get("description", "") for j in company.get("jobs", [])[:2]])
                )
                
                try:
                    response = openai.call_with_retry(
                        prompt=direct_hirer_prompt,
                        model="gpt-4o-mini",
                        response_format="json"
                    )
                    result = json.loads(response)
                    if result.get("is_direct_hirer", False):
                        filtered_companies.append(company)
                except:
                    # Default include on error to avoid losing all companies
                    filtered_companies.append(company)
            
            # If all companies filtered out, include all (better to be lenient)
            if not filtered_companies and companies:
                print(f"⚠️ All companies filtered. Including all {len(companies)} companies anyway.")
                filtered_companies = companies
            
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
            enricher = CompanyIntelligence()
            
            # Format companies for enrichment (enrich_companies expects specific field names)
            companies_for_enrichment = []
            for company in top_companies:
                companies_for_enrichment.append({
                    "company_name": company["name"],
                    "company_website": company.get("company_url", "https://www." + company["name"].lower().replace(" ", "") + ".com"),
                    "company_description": company.get("description", ""),
                    "employee_count": company.get("employee_count", 0)
                })
            
            # Enrich all companies at once
            try:
                enriched_companies = enricher.enrich_companies(companies_for_enrichment)
                
                # Map enrichment results back to top_companies
                for i, company in enumerate(top_companies):
                    if i < len(enriched_companies):
                        company["enrichment"] = enriched_companies[i].get("insider_intelligence", {})
                    else:
                        company["enrichment"] = {}
            except Exception as e:
                print(f"⚠️ Enrichment failed: {e}")
                for company in top_companies:
                    company["enrichment"] = {}
            
            self.verified_companies = top_companies
            print(f"✅ Enriched {len(top_companies)} companies")
            
            # Phase 9: Generate Outreach Email
            print("📧 Phase 9: Generating personalized outreach email...")
            email_generator = EmailGenerator(run_id=self.run_id)
            
            # Phase 8.5: Find Decision Makers (Contact Extraction)
            print("🔍 Finding decision makers for each company...")
            dm_finder = DecisionMakerFinder(run_id=self.run_id)
            
            # Format companies for decision maker search
            # Normalize job fields to match DecisionMakerFinder expectations (needs job_title only)
            companies_for_dm = []
            for company in top_companies:
                # Normalize jobs - LinkedIn uses different field names
                normalized_jobs = []
                for job in company.get("jobs", []):
                    normalized_job = {
                        "job_title": job.get("title") or job.get("positionTitle") or job.get("name") or "Unknown",
                        "description": job.get("descriptionText") or job.get("description", "")
                    }
                    normalized_jobs.append(normalized_job)
                
                companies_for_dm.append({
                    "company_name": company.get("name", ""),
                    "company_website": company.get("company_url", ""),
                    "company_description": company.get("description", ""),
                    "employee_count": company.get("employee_count", 50),
                    "jobs": normalized_jobs
                })
            
            # Find decision makers
            decision_makers = dm_finder.find_decision_makers(companies_for_dm)
            print(f"✅ Found decision makers for {len(decision_makers)} companies")
            
            # Format companies for email generator (needs full job data with URLs)
            companies_for_email = []
            for company in top_companies:
                # Enrich jobs with both title and URL for email
                enriched_jobs = []
                for job in company.get("jobs", []):
                    enriched_job = {
                        "job_title": job.get("title") or job.get("positionTitle") or job.get("name") or "Unknown",
                        "description": job.get("descriptionText") or job.get("description", ""),
                        "job_url": job.get("link") or job.get("url", ""),  # LinkedIn uses 'link', Apify returns it
                        "posted_at": job.get("postedAt", "")
                    }
                    enriched_jobs.append(enriched_job)
                
                companies_for_email.append({
                    "company_name": company.get("name", ""),
                    "company_website": company.get("company_url", ""),
                    "company_description": company.get("description", ""),
                    "employee_count": company.get("employee_count", 50),
                    "roles_hiring": enriched_jobs  # Email generator uses 'roles_hiring' key
                })
            
            # Generate email with decision makers
            self.outreach_email = email_generator.generate_email_content(
                companies=companies_for_email,
                decision_makers=decision_makers,
                recruiter_data=validated
            )
            
            print(f"✅ Generated outreach email ({len(self.outreach_email)} characters)")
            
            # Calculate total costs
            openai_cost = self.openai_caller.get_cost_estimate() if self.openai_caller else "$0.00"
            apify_cost = "$0.05"  # Fixed Apify cost per run
            total_cost_str = f"{openai_cost} + {apify_cost} Apify"
            self.stats["total_cost"] = total_cost_str
            
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

