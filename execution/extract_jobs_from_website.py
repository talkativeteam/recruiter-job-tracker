"""
Job Extraction from Company Websites
Scrapes career pages and extracts job listings using AI
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from execution.scrape_website import WebsiteScraper
from execution.call_openai import OpenAICaller
from execution.playwright_job_navigator import PlaywrightJobNavigator
from config import ai_prompts


class JobExtractor:
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id
        self.website_scraper = WebsiteScraper(run_id=run_id)
        self.openai_caller = OpenAICaller(run_id=run_id)
        self.job_navigator = PlaywrightJobNavigator(run_id=run_id)
    
    def extract_jobs_from_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract job listings from company career pages
        
        Args:
            companies: List of companies with careers_url
            
        Returns:
            List of companies with jobs populated
        """
        enriched_companies = []
        
        for company in companies:
            print(f"🔍 Extracting jobs from {company['name']}...")
            
            # Try careers_url first, then company_url
            careers_url = company.get("careers_url") or company.get("company_url")
            
            if not careers_url:
                print(f"⚠️ No URL for {company['name']}, skipping")
                continue
            
            # STRATEGY 1: Try Playwright intelligent navigation to get actual job URLs
            print(f"  🎭 Attempting Playwright navigation for job URLs...")
            jobs = self.job_navigator.find_job_urls(careers_url, company['name'])
            
            # If Playwright navigation found jobs with URLs, use them
            if jobs and len(jobs) > 0:
                print(f"  ✅ Found {len(jobs)} jobs with URLs via Playwright navigation")
                # Verify jobs have actual URLs (not mailto: or empty)
                valid_jobs = [j for j in jobs if j.get('job_url') and not j['job_url'].startswith('mailto:')]
                if len(valid_jobs) < len(jobs):
                    print(f"  ⚠️ {len(jobs) - len(valid_jobs)} jobs had invalid URLs (mailto: or empty)")
                jobs = valid_jobs
                if len(valid_jobs) > 0:
                    # We have valid job URLs, skip AI extraction
                    pass
                else:
                    # No valid URLs, need to fallback
                    jobs = []
            
            if not jobs or len(jobs) == 0:
                # STRATEGY 2: Fallback to scraping + AI extraction (no URLs)
                print(f"  ⚠️ Playwright navigation found no valid URLs, falling back to scraping + AI...")
                
                # Scrape the career page with full fallback chain (HTTP → Playwright)
                success, content, method = self.website_scraper.scrape_http(careers_url)
                
                # If HTTP fails, try Playwright
                if not success or not content:
                    print(f"⚠️ HTTP failed, trying Playwright for {company['name']}...")
                    success, content, method = self.website_scraper.scrape_playwright(careers_url)
                
                if not success or not content:
                    print(f"❌ Failed to scrape {company['name']} (tried HTTP + Playwright)")
                    continue
                
                # Extract jobs using AI (will have job titles but may not have URLs)
                jobs = self._extract_jobs_with_ai(content, company['name'])
            
            if jobs and len(jobs) > 0:
                company['jobs'] = jobs
                company['job_count'] = len(jobs)
                enriched_companies.append(company)
                print(f"✅ Found {len(jobs)} jobs at {company['name']}")
            else:
                print(f"⚠️ No jobs found at {company['name']}")
        
        return enriched_companies
    
    def _extract_jobs_with_ai(self, website_content: str, company_name: str) -> List[Dict[str, Any]]:
        """
        Use AI to extract job listings from website content
        """
        prompt = f"""You are analyzing the careers/jobs page of {company_name}.

Extract all job listings from the following content. For each job, extract:
- job_title: The job title/position name
- description: Brief description (2-3 sentences)
- job_url: Link to apply or view details (if available)
- location: Job location (if mentioned)

Return a JSON array of jobs. If no jobs are found, return an empty array.

Website Content:
{website_content[:8000]}

Return format:
{{
  "jobs": [
    {{
      "job_title": "Senior Software Engineer",
      "description": "Build scalable systems...",
      "job_url": "https://...",
      "location": "Remote"
    }}
  ]
}}
"""
        
        try:
            response = self.openai_caller.call_with_retry(
                prompt=prompt,
                model="gpt-4o-mini",
                response_format="json"
            )
            
            result = json.loads(response)
            jobs = result.get("jobs", [])
            
            # Filter out invalid jobs - ONLY keep jobs with valid URLs
            valid_jobs = []
            for job in jobs:
                if job.get("job_title") and len(job.get("job_title", "")) > 3:
                    job_url = job.get("job_url", "")
                    # Skip jobs with mailto: URLs or no URL at all
                    if not job_url or job_url.startswith("mailto:") or not job_url.startswith("http"):
                        continue  # Don't include this job
                    valid_jobs.append(job)
            
            return valid_jobs
            
        except Exception as e:
            print(f"❌ AI extraction failed: {e}")
            return []
    
    def validate_hiring_activity(self, companies: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Separate companies into those actively hiring vs not hiring
        
        Args:
            companies: Companies with job data
            
        Returns:
            Tuple of (companies_hiring, companies_not_hiring)
        """
        companies_hiring = []
        companies_not_hiring = []
        
        for company in companies:
            jobs = company.get("jobs", [])
            
            # Company is actively hiring if:
            # 1. Has at least 1 job
            # 2. Jobs have actual titles (not placeholder)
            if len(jobs) > 0:
                # Verify jobs are real
                real_jobs = [j for j in jobs if len(j.get("job_title", "")) > 5]
                if len(real_jobs) > 0:
                    company["jobs"] = real_jobs
                    company["job_count"] = len(real_jobs)
                    companies_hiring.append(company)
                else:
                    companies_not_hiring.append(company)
            else:
                companies_not_hiring.append(company)
        
        print(f"✅ Validated: {len(companies_hiring)} hiring, {len(companies_not_hiring)} not hiring")
        return companies_hiring, companies_not_hiring
    
    def extract_jobs_from_single_company(self, company_url: str, company_name: str) -> Dict[str, Any]:
        """
        Extract jobs from a single company (utility method)
        """
        companies = [{
            "name": company_name,
            "company_url": company_url,
            "careers_url": company_url
        }]
        
        enriched = self.extract_jobs_from_companies(companies)
        
        if enriched:
            return enriched[0]
        else:
            return {
                "name": company_name,
                "company_url": company_url,
                "jobs": [],
                "job_count": 0
            }
