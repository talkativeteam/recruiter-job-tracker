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
from execution.call_exa_api import ExaCompanyFinder
from execution.extract_jobs_from_website import JobExtractor
from execution.extract_icp_deep import DeepICPExtractor
from execution.validate_job_icp_fit import JobICPValidator
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
        self.exa_finder = None  # Track Exa usage
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
            
            # Phase 2: Extract ICP from Client Website (DEEP ANALYSIS)
            print("🎯 Phase 2: Deep ICP extraction from client website...")
            
            # Use deep ICP extractor with Playwright for better analysis
            deep_extractor = DeepICPExtractor(run_id=self.run_id)
            
            try:
                self.recruiter_icp = deep_extractor.extract_icp(validated.get("client_website", ""))
            except Exception as e:
                print(f"  ⚠️ Deep extraction failed, falling back to basic extraction: {e}")
                # Fallback to original HTTP-based extraction
                website_scraper = WebsiteScraper(run_id=self.run_id)
                website_content = website_scraper.scrape_http(validated.get("client_website", ""))[1] or validated.get("client_website", "")
                icp_prompt = ai_prompts.format_icp_prompt(website_content or validated.get("client_website", ""))
                icp_response = self.openai_caller.call_with_retry(
                    prompt=icp_prompt,
                    model="gpt-4o-mini",
                    response_format="json"
                )
                self.recruiter_icp = json.loads(icp_response)
            
            try:
                # Add country code mapping for LinkedIn URL
                country_to_code = {
                    "United States": "US",
                    "United Kingdom": "GB",
                    "Canada": "CA",
                    "Germany": "DE",
                    "Australia": "AU",
                    "Singapore": "SG",
                    "Netherlands": "NL",
                    "France": "FR",
                    "Spain": "ES",
                    "India": "IN",
                    "Japan": "JP",
                }
                primary_country = self.recruiter_icp.get("primary_country", "")
                self.recruiter_icp["country_code"] = country_to_code.get(primary_country, "US")
            except:
                self.recruiter_icp = {
                    "industries": [],
                    "roles": [],
                    "skills": [],
                    "seniority_levels": ["mid", "senior"],
                    "keywords": []
                }
            
            print(f"✅ ICP extracted: {json.dumps(self.recruiter_icp, indent=2)}")
            
            # 🔀 ROUTING: Check if we should skip LinkedIn and go directly to Exa
            if not validated.get("linkedin_plus_exa", True):
                print("\n🚀 DIRECT EXA MODE: Skipping LinkedIn, going straight to Exa...")
                return self._run_exa_direct_pipeline(validated)
            
            # Phase 3: Generate Boolean Search Query
            print("🔍 Phase 3: Generating Boolean search query...")
            boolean_prompt = ai_prompts.format_boolean_search_prompt(self.recruiter_icp)
            
            boolean_response = self.openai_caller.call_with_retry(
                prompt=boolean_prompt,
                model="gpt-4o-mini",
                response_format="text"
            )
            
            # Parse JSON from response (remove code fences if present)
            boolean_text = boolean_response.strip()
            if boolean_text.startswith("```"):
                boolean_text = boolean_text.split("```")[1]
                if boolean_text.startswith("json"):
                    boolean_text = boolean_text[4:]
                boolean_text = boolean_text.strip()
            
            try:
                boolean_data = json.loads(boolean_text)
                self.boolean_search = boolean_data.get("boolean_search", "").strip()
                # Normalize quotes - ensure we use proper double quotes for LinkedIn
                self.boolean_search = self.boolean_search.replace("'", '"')
                geo_id = boolean_data.get("geo_id", self.recruiter_icp.get("linkedin_geo_id", "101165590"))
                country_code = self.recruiter_icp.get("country_code", "US")
                print(f"✅ Parsed boolean search from JSON: {self.boolean_search}")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️ Failed to parse boolean search JSON: {e}")
                # Fallback: try to extract boolean search from raw response
                self.boolean_search = boolean_text.replace("'", '"')
                geo_id = self.recruiter_icp.get("linkedin_geo_id", "101165590")
                country_code = self.recruiter_icp.get("country_code", "US")
            
            print(f"✅ Boolean search: {self.boolean_search}")
            
            # Phase 4: Scrape LinkedIn Jobs (with Exa fallback for niche ICPs)
            print(f"📊 Phase 4: Scraping LinkedIn jobs ({validated.get('max_jobs_to_scrape', 100)} max)...")
            scraper = ApifyLinkedInScraper(run_id=self.run_id)
            
            # STRATEGY: Pull MORE jobs from LinkedIn and let AI validation filter
            jobs_to_scrape = max(150, validated.get('max_jobs_to_scrape', 150))
            minimum_acceptable_jobs = 20  # Fallback to 7 days if fewer than 20 jobs found
            exa_fallback_threshold = 5  # Only use Exa if < 5 jobs (very niche ICP)
            
            # Try 24 hours first (fresher results)
            print(f"🔄 Attempt 1: Scraping past 24 hours (r86400)...")
            print(f"📍 Country: {self.recruiter_icp.get('primary_country')} (code: {country_code}, geoId: {geo_id})")
            # URL encode the boolean search properly for LinkedIn public search
            import urllib.parse
            encoded_search = urllib.parse.quote(self.boolean_search)
            linkedin_url_24h = f"https://www.linkedin.com/jobs/search/?keywords={encoded_search}&geoId={geo_id}&f_I=4&f_TPR=r86400&sortBy=R"
            
            self.jobs_scraped = scraper.scrape_jobs(
                linkedin_url=linkedin_url_24h,
                max_jobs=jobs_to_scrape
            )
            
            # If insufficient results, fallback to 7 days
            if len(self.jobs_scraped) < minimum_acceptable_jobs:
                print(f"⚠️ Only {len(self.jobs_scraped)} jobs found in 24h (need {minimum_acceptable_jobs})")
                print(f"🔄 Attempt 2: Retrying with past 7 days (r604800)...")
                linkedin_url_7d = f"https://www.linkedin.com/jobs/search/?keywords={encoded_search}&geoId={geo_id}&f_I=4&f_TPR=r604800&sortBy=R"
                
                self.jobs_scraped = scraper.scrape_jobs(
                    linkedin_url=linkedin_url_7d,
                    max_jobs=jobs_to_scrape
                )
            else:
                print(f"✅ Got {len(self.jobs_scraped)} jobs in 24h - using fresh results")
            
            # NEW: If still insufficient, trigger Exa fallback workflow
            if len(self.jobs_scraped) < exa_fallback_threshold:
                print(f"\n🔄 ICP TOO NICHE: Only {len(self.jobs_scraped)} jobs found on LinkedIn")
                print(f"🌐 Activating Exa fallback workflow...")
                
                # Use Exa to find companies directly
                self.exa_finder = ExaCompanyFinder(run_id=self.run_id)
                exa_companies = self.exa_finder.find_companies(
                    icp_data=self.recruiter_icp,
                    max_results=20  # Get more companies to filter down
                )
                
                if len(exa_companies) > 0:
                    print(f"✅ Exa found {len(exa_companies)} potential companies")
                    
                    # Extract jobs from company websites
                    job_extractor = JobExtractor(run_id=self.run_id)
                    companies_with_jobs = job_extractor.extract_jobs_from_companies(exa_companies)
                    
                    # Validate which companies are actually hiring
                    companies_hiring, companies_not_hiring = job_extractor.validate_hiring_activity(companies_with_jobs)
                    
                    if len(companies_hiring) > 0:
                        print(f"✅ Exa fallback successful: {len(companies_hiring)} companies actively hiring")
                        
                        # Convert Exa format to LinkedIn format for consistency
                        self.jobs_scraped = []
                        for company in companies_hiring:
                            for job in company.get("jobs", []):
                                linkedin_format_job = {
                                    "companyName": company["name"],
                                    "companyDescription": company.get("description", ""),
                                    "companyWebsite": company.get("company_url", ""),
                                    "title": job.get("job_title", ""),
                                    "description": job.get("description", ""),
                                    "descriptionText": job.get("description", ""),
                                    "link": job.get("job_url", ""),
                                    "location": job.get("location", "Remote"),
                                    "source": "exa_fallback"
                                }
                                self.jobs_scraped.append(linkedin_format_job)
                        
                        print(f"✅ Converted {len(self.jobs_scraped)} jobs from Exa to LinkedIn format")
                    else:
                        print(f"⚠️ Exa fallback found companies but none are hiring")
                        if len(self.jobs_scraped) == 0:
                            raise Exception("No jobs found via LinkedIn or Exa fallback")
                else:
                    print(f"⚠️ Exa fallback found 0 companies")
                    if len(self.jobs_scraped) == 0:
                        raise Exception("No jobs found via LinkedIn or Exa fallback")
            
            self.stats["total_jobs_scraped"] = len(self.jobs_scraped)
            self.stats["data_source"] = "exa_fallback" if len(self.jobs_scraped) > 0 and self.jobs_scraped[0].get("source") == "exa_fallback" else "linkedin"
            print(f"✅ Total: {len(self.jobs_scraped)} jobs scraped (source: {self.stats.get('data_source', 'linkedin')})")
            
            if not self.jobs_scraped:
                raise Exception("No jobs scraped from LinkedIn or Exa fallback")
            
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
            
            # Phase 7.5: CRITICAL - Validate Job-ICP Fit (MUST RUN BEFORE PRIORITIZATION)
            print("🔍 Phase 7.5: CRITICAL JOB-ICP FIT VALIDATION...")
            print("")
            job_validator = JobICPValidator(run_id=self.run_id)
            validated_companies = job_validator.validate_jobs_for_companies(
                companies=filtered_companies,
                recruiter_icp=self.recruiter_icp
            )
            
            # 🔥 CRITICAL: If validation fails, trigger Exa fallback instead of failing
            if len(validated_companies) == 0:
                print(f"\n❌ VALIDATION FAILED: 0/{len(filtered_companies)} companies passed job-ICP validation")
                print(f"🔄 TRIGGERING EXA FALLBACK: LinkedIn jobs were wrong industry/roles")
                print("")
                
                # Use Exa to find companies matching ICP
                print("🔍 Phase 6b: Using Exa to find ICP-matching companies...")
                self.exa_finder = ExaCompanyFinder(run_id=self.run_id)
                exa_companies = self.exa_finder.find_companies(
                    icp_data=self.recruiter_icp,
                    max_results=20
                )
                
                if not exa_companies or len(exa_companies) == 0:
                    raise Exception("No companies found via Exa fallback either.")
                
                print(f"✅ Exa found {len(exa_companies)} ICP-matching companies")
                
                # 🎭 CRITICAL: Enrich ALL Exa companies with Playwright BEFORE selecting top 4
                print(f"🧠 Enriching ALL {len(exa_companies)} Exa companies with Playwright...")
                enricher = CompanyIntelligence()
                
                exa_for_enrichment = []
                for company in exa_companies:
                    exa_for_enrichment.append({
                        "company_name": company["name"],
                        "company_website": company.get("company_url", "https://www." + company["name"].lower().replace(" ", "") + ".com"),
                        "careers_url": company.get("careers_url", ""),
                        "company_description": company.get("description", ""),
                        "employee_count": company.get("employee_count", 0)
                    })
                
                try:
                    enriched_exa = enricher.enrich_companies(exa_for_enrichment)
                    print(f"✅ Enriched {len(enriched_exa)} Exa companies")
                    
                    # Map enrichment back and add relevance scores
                    for i, company in enumerate(exa_companies):
                        if i < len(enriched_exa):
                            company["enrichment"] = enriched_exa[i]
                            company["relevance_score"] = enriched_exa[i].get("relevance_score", 0)
                        else:
                            company["relevance_score"] = 0
                    
                    # Sort by relevance and use for rest of pipeline
                    exa_companies = sorted(exa_companies, key=lambda x: x.get("relevance_score", 0), reverse=True)
                    print(f"✅ Sorted Exa companies by enrichment scores")
                    
                except Exception as e:
                    print(f"⚠️ Exa enrichment failed: {e}, continuing with unsorted results")
                
                # Use enriched Exa companies for rest of pipeline
                validated_companies = exa_companies
            
            self.stats["companies_after_job_validation"] = len(validated_companies)
            print(f"✅ {len(validated_companies)} companies with validated jobs")
            
            # Phase 7: Prioritize Top Companies (from validated companies only)
            print("⭐ Phase 7: Selecting top companies from validated pool...")
            prioritizer = CompanyPrioritizer(run_id=self.run_id)
            top_companies = prioritizer.select_top_n(
                companies=validated_companies,
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
                    "careers_url": company.get("careers_url", ""),
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
            
            # Calculate total costs with detailed breakdown
            openai_cost = self.openai_caller.get_cost_estimate() if self.openai_caller else 0.0
            exa_cost = self.exa_finder.get_cost_estimate() if self.exa_finder else 0.0
            
            # Only add Apify cost if we actually used LinkedIn (not Exa fallback)
            data_source = self.stats.get("data_source", "linkedin")
            apify_cost = 0.05 if data_source == "linkedin" else 0.0
            
            total_cost = openai_cost + exa_cost + apify_cost
            
            # Print detailed cost breakdown
            print(f"\n💰 Cost Breakdown:")
            if openai_cost > 0:
                print(f"  OpenAI: ${openai_cost:.4f} ({self.openai_caller.call_count} calls)")
                for model, usage in self.openai_caller.model_usage.items():
                    print(f"    {model}: {usage['calls']} calls, {usage['input_tokens']} in + {usage['output_tokens']} out tokens")
            if exa_cost > 0:
                print(f"  Exa: ${exa_cost:.4f} ({self.exa_finder.search_count} searches)")
            if apify_cost > 0:
                print(f"  Apify: ${apify_cost:.2f}")
            print(f"  TOTAL: ${total_cost:.4f}")
            
            # Build cost string for stats
            cost_parts = []
            if openai_cost > 0:
                cost_parts.append(f"${openai_cost:.3f} OpenAI")
            if exa_cost > 0:
                cost_parts.append(f"${exa_cost:.3f} Exa")
            if apify_cost > 0:
                cost_parts.append(f"${apify_cost:.2f} Apify")
            
            total_cost_str = f"${total_cost:.3f} ({' + '.join(cost_parts)})"
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
    
    def _run_exa_direct_pipeline(self, validated: Dict[str, Any]) -> Dict[str, Any]:
        """
        Exa-Direct Mode: Skip LinkedIn entirely and go straight to Exa
        Used when linkedin_plus_exa=false in input JSON
        """
        try:
            # Phase 3-7 (Exa): Find companies using Exa
            print("🔍 Phase 3-7 (Exa Direct): Finding ICP-matching companies...")
            self.exa_finder = ExaCompanyFinder(run_id=self.run_id)
            exa_companies = self.exa_finder.find_companies(
                icp_data=self.recruiter_icp,
                max_results=20
            )
            
            if not exa_companies or len(exa_companies) == 0:
                raise Exception("No companies found via Exa direct mode.")
            
            print(f"✅ Exa found {len(exa_companies)} ICP-matching companies")
            
            # Phase 8: Enrich ALL Companies with World-Class Playwright (BEFORE selecting top 4)
            print(f"🧠 Phase 8: Enriching ALL {len(exa_companies)} companies with Playwright intelligence...")
            enricher = CompanyIntelligence()
            
            companies_for_enrichment = []
            for company in exa_companies:
                companies_for_enrichment.append({
                    "company_name": company["name"],
                    "company_website": company.get("company_url", "https://www." + company["name"].lower().replace(" ", "") + ".com"),
                    "careers_url": company.get("careers_url", ""),
                    "company_description": company.get("description", ""),
                    "employee_count": company.get("employee_count", 0)
                })
            
            try:
                enriched_companies = enricher.enrich_companies(companies_for_enrichment)
                print(f"✅ Enriched {len(enriched_companies)} companies with deep intelligence")
                
                # Map enrichment back to exa_companies and add relevance scores
                for i, company in enumerate(exa_companies):
                    if i < len(enriched_companies):
                        company["enrichment"] = enriched_companies[i]
                        company["relevance_score"] = enriched_companies[i].get("relevance_score", 0)
                    else:
                        company["enrichment"] = {}
                        company["relevance_score"] = 0
                
                # NOW select top 4 based on enrichment relevance scores
                exa_companies_sorted = sorted(exa_companies, key=lambda x: x.get("relevance_score", 0), reverse=True)
                top_companies = exa_companies_sorted[:4]
                print(f"✅ Selected top {len(top_companies)} companies based on enrichment scores")
                
                # Use enriched data for rest of pipeline
                enriched_companies = [c["enrichment"] for c in top_companies]
                
            except Exception as e:
                print(f"⚠️ Company enrichment failed: {e}")
                # Fallback: take first 4 without enrichment
                top_companies = exa_companies[:4]
                enriched_companies = companies_for_enrichment[:4]
            
            self.stats["data_source"] = "exa_direct"
            self.stats["final_companies_selected"] = len(top_companies)
            
            # Store verified companies
            self.verified_companies = top_companies
            
            # Format companies for email
            verified_companies = []
            for company_data in enriched_companies:
                verified_companies.append({
                    "company_name": company_data["company_name"],
                    "company_website": company_data["company_website"],
                    "company_description": company_data.get("company_description", ""),
                    "company_intel": company_data.get("insider_intelligence", {}),
                    "relevance_score": company_data.get("relevance_score", 0)
                })
            
            # Phase 9: Generate Outreach Email
            print("📧 Phase 9: Generating personalized outreach email...")
            email_generator = EmailGenerator(run_id=self.run_id)
            
            # Format companies for email generator (Exa companies have no jobs, use empty list)
            companies_for_email = []
            for company_data in enriched_companies:
                companies_for_email.append({
                    "company_name": company_data["company_name"],
                    "company_website": company_data["company_website"],
                    "company_description": company_data.get("company_description", ""),
                    "employee_count": company_data.get("employee_count", 50),
                    "roles_hiring": []  # Exa mode has no specific job listings
                })
            
            self.outreach_email = email_generator.generate_email_content(
                companies=companies_for_email,
                decision_makers=[],  # No decision makers in Exa flow
                recruiter_data=validated
            )
            
            print(f"✅ Generated outreach email ({len(self.outreach_email)} characters)")
            
            # Phase 10: Send Response
            print("📤 Phase 10: Sending response...")
            
            final_output = {
                "run_metadata": {
                    "run_id": self.run_id,
                    "status": "success",
                    "pipeline_version": "exa-direct-mode",
                    "data_source": "exa_direct"
                },
                "input": self.validated_input,
                "recruiter_icp": self.recruiter_icp,
                "stats": self.stats,
                "verified_companies": verified_companies,
                "outreach_email": self.outreach_email
            }
            
            webhook_url = validated.get("callback_webhook_url")
            if webhook_url:
                send_webhook(webhook_url, final_output)
                print(f"✅ Sent response to webhook: {webhook_url}")
            
            if self.logger and self.run_id:
                self.logger.mark_completed(self.run_id, final_output)
            
            print("\n🎉 EXA-DIRECT PIPELINE COMPLETE!")
            return final_output
            
        except Exception as e:
            print(f"❌ Exa-direct pipeline failed: {str(e)}")
            import traceback
            traceback.print_exc()
            
            error_result = {
                "run_metadata": {
                    "run_id": self.run_id,
                    "status": "failed",
                    "error": str(e),
                    "pipeline_version": "exa-direct-mode"
                },
                "input": self.validated_input,
                "recruiter_icp": self.recruiter_icp,
                "stats": self.stats,
                "verified_companies": [],
                "outreach_email": ""
            }
            
            if self.logger and self.run_id:
                self.logger.mark_failed(self.run_id, str(e), "exa-direct-pipeline")
            
            return error_result


