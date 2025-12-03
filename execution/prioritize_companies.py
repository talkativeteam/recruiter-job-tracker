"""
Company Prioritizer
Prioritizes companies by multi-role hiring and ICP fit
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from difflib import SequenceMatcher

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))
from execution.call_openai import OpenAICaller
from execution.supabase_logger import SupabaseLogger

class CompanyPrioritizer:
    def __init__(self, run_id: str = None):
        self.run_id = run_id
        self.logger = SupabaseLogger() if run_id else None
        self.openai_caller = OpenAICaller(run_id=run_id)
    
    def similar(self, a: str, b: str) -> float:
        """Calculate string similarity (0.0 to 1.0)"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def count_unique_roles(self, jobs: List[Dict[str, Any]]) -> int:
        """
        Count unique job titles (with fuzzy matching for duplicates)
        """
        unique_titles = []
        
        for job in jobs:
            title = job.get("title", "").strip()
            
            # Check if this title is similar to any existing title
            is_duplicate = False
            for existing_title in unique_titles:
                if self.similar(title, existing_title) > 0.85:  # 85% similarity = duplicate
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_titles.append(title)
        
        return len(unique_titles)
    
    def group_by_company(self, jobs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Group jobs by company and calculate metrics
        """
        companies = {}
        
        for job in jobs:
            company_name = job.get("company", "Unknown")
            
            if company_name not in companies:
                # Extract company info from first job
                company_info = job.get("companyInfo", {})
                companies[company_name] = {
                    "company_name": company_name,
                    "company_website": company_info.get("website", ""),
                    "company_description": company_info.get("description", ""),
                    "company_industry": company_info.get("industry", ""),
                    "employee_count": job.get("employeeCount", 0),  # At job level, not companyInfo
                    "company_linkedin": company_info.get("linkedinUrl", ""),
                    "jobs": [],
                    "unique_roles_count": 0,
                    "icp_fit_score": 0.0
                }
            
            # Add job to company
            companies[company_name]["jobs"].append({
                "job_title": job.get("title", ""),
                "job_url": job.get("url", ""),
                "job_description": job.get("description", ""),
                "posted_at": job.get("postedAt", "")
            })
        
        # Calculate unique roles count for each company
        for company_name, company_data in companies.items():
            company_data["unique_roles_count"] = self.count_unique_roles(company_data["jobs"])
        
        return companies
    
    def score_icp_fit(self, company: Dict[str, Any], icp_data: Dict[str, Any]) -> float:
        """
        Score company's fit to recruiter's ICP (0.0 to 1.0)
        Could use OpenAI, but for simplicity, using heuristic scoring
        """
        score = 0.0
        
        # Industry match (40%) - check if company industry appears in recruiter summary
        company_industry = company.get("company_industry", "").lower()
        recruiter_summary = icp_data.get("recruiter_summary", "").lower()
        if company_industry and company_industry in recruiter_summary:
            score += 0.4
        
        # Size match (20%)
        employee_count = company.get("employee_count", 0)
        if isinstance(employee_count, str):
            numbers = [int(s) for s in employee_count.split() if s.isdigit()]
            employee_count = max(numbers) if numbers else 50
        
        # Assume ICP is 10-100 employees (from requirements)
        if 10 <= employee_count <= 100:
            score += 0.2
        
        # Role alignment (40%) - check if job titles appear in recruiter summary
        recruiter_summary = icp_data.get("recruiter_summary", "").lower()
        company_roles = [job["job_title"].lower() for job in company.get("jobs", [])]
        
        # Extract key role words (manager, director, vp, etc.)
        role_keywords = ["manager", "director", "vp", "vice president", "head of", "chief", "lead", "senior"]
        matches = sum(1 for company_role in company_roles 
                     if any(keyword in company_role and keyword in recruiter_summary 
                           for keyword in role_keywords))
        
        if company_roles:
            role_match_ratio = matches / len(company_roles)
            score += 0.4 * role_match_ratio
        
        return min(score, 1.0)  # Cap at 1.0
    
    def prioritize(self, jobs: List[Dict[str, Any]], icp_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Prioritize companies by:
        1. Number of unique roles (primary)
        2. ICP fit score (secondary)
        """
        print(f"📊 Prioritizing {len(jobs)} jobs...")
        
        # Group by company
        companies = self.group_by_company(jobs)
        print(f"✅ Grouped into {len(companies)} companies")
        
        # Score each company
        for company_name, company_data in companies.items():
            icp_score = self.score_icp_fit(company_data, icp_data)
            company_data["icp_fit_score"] = icp_score
            print(f"  {company_name}: {company_data['unique_roles_count']} roles, {icp_score:.2f} fit")
        
        # Sort companies
        prioritized = sorted(
            companies.values(),
            key=lambda x: (x["unique_roles_count"], x["icp_fit_score"]),
            reverse=True
        )
        
        # Add rank
        for i, company in enumerate(prioritized, 1):
            company["rank"] = i
        
        print(f"✅ Prioritized {len(prioritized)} companies")
        
        # Update Supabase
        if self.logger and self.run_id:
            self.logger.update_phase(
                run_id=self.run_id,
                phase="prioritizing_multi_role",
                cost_of_run=f"${self.openai_caller.get_cost_estimate():.3f} OpenAI"
            )
        
        return prioritized
    
    def select_top_n_with_diversity(self, companies: List[Dict[str, Any]], n: int = 4) -> List[Dict[str, Any]]:
        """
        Select top N companies with size diversity
        Prioritizes ICP fit first, then adds size variety
        """
        print(f"🎯 Selecting top {n} companies with size diversity...")
        
        # Filter to companies <= 100 employees only
        valid_companies = [c for c in companies if c.get("employee_count", 0) > 0 and c.get("employee_count", 0) <= 100]
        
        if len(valid_companies) < n:
            print(f"⚠️ Only {len(valid_companies)} companies <= 100 employees available")
            return valid_companies[:n]
        
        # Sort by ICP fit score (primary)
        sorted_by_fit = sorted(valid_companies, key=lambda x: x.get("icp_fit_score", 0), reverse=True)
        
        # Take top companies by ICP fit, ensuring size diversity
        selected = []
        size_buckets = {"small": [], "medium": [], "large": []}  # 1-30, 31-70, 71-100
        
        for company in sorted_by_fit:
            emp_count = company.get("employee_count", 0)
            if emp_count <= 30:
                size_buckets["small"].append(company)
            elif emp_count <= 70:
                size_buckets["medium"].append(company)
            else:
                size_buckets["large"].append(company)
        
        # Pick best from each bucket for diversity
        for bucket in ["small", "medium", "large"]:
            if size_buckets[bucket] and len(selected) < n:
                selected.append(size_buckets[bucket][0])
        
        # Fill remaining slots with highest ICP fit
        for company in sorted_by_fit:
            if len(selected) >= n:
                break
            if company not in selected:
                selected.append(company)
        
        for company in selected:
            print(f"  ✅ {company['company_name']}: {company.get('employee_count', 0)} employees, {company.get('icp_fit_score', 0):.2f} ICP fit")
        
        print(f"✅ Selected {len(selected)} companies")
        
        # Update Supabase
        if self.logger and self.run_id:
            self.logger.update_phase(
                run_id=self.run_id,
                phase="selecting_top_companies",
                final_companies_selected=len(selected),
                cost_of_run=f"${self.openai_caller.get_cost_estimate():.3f} OpenAI"
            )
        
        return selected
    
    def select_top_n(self, companies: List[Dict[str, Any]], n: int = 4, 
                     validate_icp: bool = False, icp_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Select top N companies, optionally with ICP validation
        """
        print(f"🎯 Selecting top {n} companies...")
        
        selected = []
        
        for company in companies:
            if len(selected) >= n:
                break
            
            # Validate ICP fit if requested
            if validate_icp and icp_data:
                validation = self.openai_caller.validate_icp_fit(
                    recruiter_icp=icp_data,
                    company_name=company["company_name"],
                    company_description=company["company_description"],
                    company_industry=company["company_industry"],
                    employee_count=company["employee_count"],
                    location="",  # Not critical for validation
                    roles_hiring=[job["job_title"] for job in company["jobs"]]
                )
                
                if validation and validation.get("is_good_fit"):
                    company["icp_validation"] = validation
                    selected.append(company)
                    print(f"✅ {company['company_name']} - ICP fit validated")
                else:
                    print(f"❌ {company['company_name']} - Failed ICP validation")
            else:
                selected.append(company)
        
        print(f"✅ Selected {len(selected)} companies")
        
        # Update Supabase
        if self.logger and self.run_id:
            self.logger.update_phase(
                run_id=self.run_id,
                phase="selecting_top_companies",
                final_companies_selected=len(selected),
                cost_of_run=f"${self.openai_caller.get_cost_estimate():.3f} OpenAI"
            )
        
        return selected

def main():
    parser = argparse.ArgumentParser(description="Prioritize companies")
    parser.add_argument("--input", required=True, help="Path to filtered jobs JSON")
    parser.add_argument("--icp", required=True, help="Path to ICP JSON")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--count", type=int, help="Select top N companies")
    parser.add_argument("--validate-icp", action="store_true", help="Validate ICP fit")
    parser.add_argument("--run-id", help="Run ID for logging")
    args = parser.parse_args()
    
    # Load data
    with open(args.input, 'r') as f:
        jobs = json.load(f)
    
    with open(args.icp, 'r') as f:
        icp_data = json.load(f)
    
    # Prioritize
    prioritizer = CompanyPrioritizer(run_id=args.run_id)
    
    if args.count:
        # Select top N with size diversity
        companies = prioritizer.prioritize(jobs, icp_data)
        result = prioritizer.select_top_n_with_diversity(
            companies, 
            n=args.count
        )
    else:
        # Just prioritize
        result = prioritizer.prioritize(jobs, icp_data)
    
    if not result:
        print("❌ No companies selected")
        sys.exit(1)
    
    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"✅ Saved {len(result)} companies to {output_path}")

if __name__ == "__main__":
    main()
