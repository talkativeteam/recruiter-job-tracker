"""
Apify LinkedIn Jobs Scraper Caller
Calls Apify Actor: curious_coder/linkedin-jobs-scraper
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv
from apify_client import ApifyClient

# Load environment variables
load_dotenv()

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.config import TIMEOUT_APIFY, MAX_RETRIES
from execution.supabase_logger import SupabaseLogger

class ApifyLinkedInScraper:
    def __init__(self, run_id: str = None):
        self.client = ApifyClient(os.getenv("APIFY_API_KEY"))
        self.run_id = run_id
        self.logger = SupabaseLogger() if run_id else None
        self.actor_id = "curious_coder/linkedin-jobs-scraper"
    
    def scrape_jobs(self, linkedin_url: str, max_jobs: int = 50) -> list:
        """
        Scrape LinkedIn jobs using Apify
        CRITICAL: Must use scrapeCompany: true
        """
        run_input = {
            "count": max_jobs,
            "scrapeCompany": True,  # CRITICAL - get company data automatically
            "urls": [linkedin_url]
        }
        
        print(f"🔍 Starting Apify LinkedIn Jobs Scraper...")
        print(f"📊 Max jobs: {max_jobs}")
        print(f"🔗 Full URL: {linkedin_url}")
        print(f"⚠️ scrapeCompany: True (CRITICAL)")
        
        for attempt in range(MAX_RETRIES):
            try:
                # Start the actor run
                run = self.client.actor(self.actor_id).call(run_input=run_input, timeout_secs=TIMEOUT_APIFY)
                
                # Fetch results
                dataset_id = run.get("defaultDatasetId")
                items = list(self.client.dataset(dataset_id).iterate_items())
                
                print(f"✅ Apify scraping completed")
                print(f"✅ Jobs scraped: {len(items)}")
                
                # Count unique companies
                unique_companies = len(set(item.get("company", "") for item in items if item.get("company")))
                print(f"✅ Unique companies: {unique_companies}")
                
                # Extract job posting links and dates
                job_links = [item.get("url") for item in items if item.get("url")]
                job_dates = [item.get("postedAt") for item in items if item.get("postedAt")]
                latest_date = max(job_dates) if job_dates else None
                
                # Update Supabase
                if self.logger and self.run_id:
                    self.logger.update_phase(
                        run_id=self.run_id,
                        phase="scraping_linkedin_jobs",
                        companies_found=unique_companies,
                        cost_of_run=f"$0.05 Apify (1 run, {len(items)} jobs)",
                        job_posting_links=job_links,
                        job_posting_date=latest_date
                    )
                
                return items
            
            except Exception as e:
                print(f"❌ Apify scraping failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                
                if attempt < MAX_RETRIES - 1:
                    delay = 30  # Wait 30 seconds between retries
                    print(f"⏳ Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    print(f"❌ All Apify retries exhausted")
                    raise
        
        return []

def main():
    parser = argparse.ArgumentParser(description="Scrape LinkedIn jobs using Apify")
    parser.add_argument("--url-file", required=True, help="Path to LinkedIn URL JSON file")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--max-jobs", type=int, default=50, help="Max jobs to scrape")
    parser.add_argument("--run-id", help="Run ID for logging")
    args = parser.parse_args()
    
    # Load LinkedIn URL
    with open(args.url_file, 'r') as f:
        url_data = json.load(f)
        linkedin_url = url_data.get("linkedin_url")
    
    if not linkedin_url:
        print("❌ No linkedin_url found in input file")
        sys.exit(1)
    
    # Scrape jobs
    scraper = ApifyLinkedInScraper(run_id=args.run_id)
    
    try:
        jobs = scraper.scrape_jobs(linkedin_url, max_jobs=args.max_jobs)
        
        if not jobs:
            print("❌ No jobs scraped")
            sys.exit(1)
        
        # Save output
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(jobs, f, indent=2)
        
        print(f"✅ Saved {len(jobs)} jobs to {output_path}")
    
    except Exception as e:
        print(f"❌ Apify scraping failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
