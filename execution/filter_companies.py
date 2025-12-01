"""
Company Filter
Filters direct hirers and removes large companies (>100 employees)
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.config import MAX_COMPANY_SIZE
from execution.call_openai import OpenAICaller
from execution.supabase_logger import SupabaseLogger

class CompanyFilter:
    def __init__(self, run_id: str = None):
        self.run_id = run_id
        self.logger = SupabaseLogger() if run_id else None
        self.openai_caller = OpenAICaller(run_id=run_id)
    
    def filter_by_size(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out companies with >MAX_COMPANY_SIZE employees"""
        filtered = []
        
        for job in jobs:
            company_info = job.get("companyInfo", {})
            employee_count = company_info.get("employeeCount", 0)
            
            # Handle string employee counts (e.g., "10-50 employees")
            if isinstance(employee_count, str):
                # Extract max number from range
                numbers = [int(s) for s in employee_count.split() if s.isdigit()]
                employee_count = max(numbers) if numbers else 0
            
            if employee_count <= MAX_COMPANY_SIZE:
                filtered.append(job)
            else:
                print(f"⚠️ Filtered out {job.get('company')} ({employee_count} employees)")
        
        print(f"✅ Size filter: {len(jobs)} → {len(filtered)} jobs")
        return filtered
    
    def is_obvious_recruiter(self, company_name: str, company_industry: str) -> bool:
        """
        Deterministic check for obvious recruiters (saves OpenAI calls)
        """
        recruiter_keywords = [
            "staffing", "recruiting", "talent", "personnel", 
            "workforce", "employment", "headhunter", "placement"
        ]
        
        # Check company name
        name_lower = company_name.lower()
        if any(keyword in name_lower for keyword in recruiter_keywords):
            return True
        
        # Check industry
        if company_industry:
            industry_lower = company_industry.lower()
            if "staffing" in industry_lower or "recruiting" in industry_lower:
                return True
        
        return False
    
    def validate_direct_hirer(self, job: Dict[str, Any]) -> bool:
        """
        Validate if company is a direct hirer (NOT recruiter)
        """
        company_name = job.get("company", "")
        company_info = job.get("companyInfo", {})
        company_description = company_info.get("description", "")
        company_industry = company_info.get("industry", "")
        job_description = job.get("description", "")
        
        # Deterministic check first (FREE)
        if self.is_obvious_recruiter(company_name, company_industry):
            print(f"❌ {company_name} - Obvious recruiter (deterministic)")
            return False
        
        # Use OpenAI for borderline cases
        result = self.openai_caller.validate_direct_hirer(
            company_name, company_description, company_industry, job_description
        )
        
        if not result:
            print(f"⚠️ {company_name} - Validation failed, skipping")
            return False
        
        is_direct_hirer = result.get("is_direct_hirer", False)
        confidence = result.get("confidence", "unknown")
        reason = result.get("reason", "")
        
        if is_direct_hirer:
            print(f"✅ {company_name} - Direct hirer ({confidence} confidence)")
        else:
            print(f"❌ {company_name} - Recruiter/Staffing ({reason})")
        
        return is_direct_hirer
    
    def group_by_company(self, jobs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group jobs by company"""
        companies = {}
        
        for job in jobs:
            company_name = job.get("company", "Unknown")
            if company_name not in companies:
                companies[company_name] = []
            companies[company_name].append(job)
        
        return companies
    
    def deduplicate_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate job postings"""
        seen = set()
        unique_jobs = []
        
        for job in jobs:
            job_id = (job.get("title"), job.get("company"), job.get("location"))
            if job_id not in seen:
                seen.add(job_id)
                unique_jobs.append(job)
        
        return unique_jobs
    
    def normalize_job_data(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize job data from Apify format to expected format"""
        return {
            "company": job.get("companyName", "Unknown"),
            "title": job.get("title", ""),
            "location": job.get("location", ""),
            "description": job.get("descriptionText", ""),
            "employeeCount": job.get("companyEmployeesCount", 0),  # Keep as number
            "companyInfo": {
                "description": job.get("companyDescription", ""),
                "industry": job.get("industries", ""),
                "website": job.get("companyWebsite", "")
            },
            "url": job.get("link", ""),
            "postedAt": job.get("postedAt", "")
        }
    
    def filter(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Main filtering method
        """
        print(f"📊 Starting filtering: {len(jobs)} jobs")
        
        # Step 0: Normalize data from Apify format
        jobs = [self.normalize_job_data(job) for job in jobs]
        
        # Step 1: Filter by size
        jobs = self.filter_by_size(jobs)
        
        # Step 2: Group by company
        companies = self.group_by_company(jobs)
        print(f"✅ Found {len(companies)} unique companies")
        
        # Step 3: Validate each company (one job per company for validation)
        validated_companies = []
        
        for company_name, company_jobs in companies.items():
            # Take first job for validation (representative)
            sample_job = company_jobs[0]
            
            if self.validate_direct_hirer(sample_job):
                # All jobs from this company are valid
                validated_companies.extend(company_jobs)
        
        print(f"✅ Validated {len(validated_companies)} jobs from direct hirers")
        
        # Step 4: Deduplicate
        validated_companies = self.deduplicate_jobs(validated_companies)
        print(f"✅ After deduplication: {len(validated_companies)} jobs")
        
        # Update Supabase
        if self.logger and self.run_id:
            unique_validated_companies = len(set(job.get("company") for job in validated_companies))
            self.logger.update_phase(
                run_id=self.run_id,
                phase="filtering_direct_hirers",
                companies_validated=unique_validated_companies,
                cost_of_run=f"${self.openai_caller.get_cost_estimate():.3f} OpenAI"
            )
        
        return validated_companies

def main():
    parser = argparse.ArgumentParser(description="Filter companies (remove recruiters, large companies)")
    parser.add_argument("--input", required=True, help="Path to raw jobs JSON")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--max-employees", type=int, default=MAX_COMPANY_SIZE, help="Max employee count")
    parser.add_argument("--run-id", help="Run ID for logging")
    args = parser.parse_args()
    
    # Load jobs
    with open(args.input, 'r') as f:
        jobs = json.load(f)
    
    # Filter
    filter_engine = CompanyFilter(run_id=args.run_id)
    filtered_jobs = filter_engine.filter(jobs)
    
    if not filtered_jobs:
        print("❌ No companies passed filtering")
        sys.exit(1)
    
    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(filtered_jobs, f, indent=2)
    
    print(f"✅ Saved {len(filtered_jobs)} filtered jobs to {output_path}")

if __name__ == "__main__":
    main()
