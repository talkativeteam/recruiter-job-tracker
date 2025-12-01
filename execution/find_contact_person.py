"""
Decision Maker Finder
Finds decision-makers for companies using Exa API
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
import re

try:
    from exa_py import Exa
except ImportError:
    print("⚠️ exa_py not installed. Install with: pip install exa_py")
    Exa = None

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))
from execution.call_openai import OpenAICaller
from execution.supabase_logger import SupabaseLogger

class DecisionMakerFinder:
    def __init__(self, run_id: str = None):
        self.run_id = run_id
        self.logger = SupabaseLogger() if run_id else None
        self.openai_caller = OpenAICaller(run_id=run_id)
        
        if Exa:
            self.exa = Exa(api_key=os.getenv("EXA_API_KEY"))
        else:
            self.exa = None
        
        self.search_count = 0
    
    def determine_target_role(self, company_size: int, job_titles: List[str]) -> tuple[str, List[str]]:
        """
        Determine target decision-maker role based on company size and jobs
        """
        # Analyze job seniority
        senior_keywords = ["senior", "principal", "lead", "architect", "director", "vp", "head"]
        is_senior_role = any(any(keyword in title.lower() for keyword in senior_keywords) 
                             for title in job_titles)
        
        # Determine role type
        if any("engineer" in title.lower() for title in job_titles):
            role_type = "Engineering"
        elif any("security" in title.lower() or "cyber" in title.lower() for title in job_titles):
            role_type = "Security"
        elif any("it " in title.lower() or "help desk" in title.lower() or "system admin" in title.lower() for title in job_titles):
            role_type = "IT"
        else:
            role_type = "Technology"
        
        # Apply targeting rules
        if company_size < 20:
            return "CEO", ["Founder", "Co-Founder", "Chief Executive Officer"]
        elif company_size < 50:
            if is_senior_role:
                return "CTO", ["VP Engineering", "Head of Engineering", "VP Technology"]
            else:
                return "Engineering Manager", ["Head of IT", "IT Manager", "Engineering Lead"]
        else:  # 50-100 employees
            if is_senior_role:
                return f"VP {role_type}", [f"Director of {role_type}", "CTO", f"Head of {role_type}"]
            else:
                return f"{role_type} Manager", [f"Head of {role_type}", f"{role_type} Lead"]
    
    def search_decision_maker(self, company_name: str, target_role: str, 
                              alternative_roles: List[str]) -> Optional[Dict[str, str]]:
        """
        Search for decision-maker using Exa API
        """
        if not self.exa:
            print("❌ Exa API not available")
            return None
        
        # Try primary role first
        all_roles = [target_role] + alternative_roles
        
        for role in all_roles:
            try:
                # Add UK location filtering to search
                query = f'"{company_name}" "{role}" "United Kingdom" OR "UK" site:linkedin.com/in'
                print(f"🔍 Searching: {query}")
                
                result = self.exa.search(
                    query,
                    num_results=5  # Get more results to find valid profiles
                )
                
                self.search_count += 1
                
                if result.results:
                    # Try all results until we find a valid one
                    for top_result in result.results:
                        linkedin_url = top_result.url
                        
                        # Extract name from title (usually "Name - Title at Company")
                        title = top_result.title
                        name_match = re.match(r"([^-|]+)", title)
                        name = name_match.group(1).strip() if name_match else title
                        
                        # Validate result
                        if self._is_valid_result(name, company_name, linkedin_url):
                            print(f"✅ Found: {name} ({role})")
                            return {
                                "name": name,
                                "title": role,
                                "linkedin_url": linkedin_url
                            }
                    
                    print(f"⚠️ No valid personal profile found for {role}, trying next...")
                    continue
            
            except Exception as e:
                print(f"❌ Exa search failed for {role}: {e}")
                continue
        
        print(f"❌ No decision-maker found for {company_name}")
        return None
    
    def _is_valid_result(self, name: str, company_name: str, linkedin_url: str) -> bool:
        """Validate search result"""
        # Name should not be the company name
        if company_name.lower() in name.lower():
            return False
        
        # LinkedIn URL should be a personal profile (not posts or company pages)
        if "/posts/" in linkedin_url or "/company/" in linkedin_url:
            return False
        
        # Accept both www.linkedin.com and country-specific domains (uk.linkedin.com, nz.linkedin.com, etc.)
        if "/in/" not in linkedin_url or "linkedin.com" not in linkedin_url:
            return False
        
        return True
    
    def find_decision_makers(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find decision-makers for list of companies
        """
        print(f"🔍 Finding decision-makers for {len(companies)} companies...")
        
        results = []
        
        for company in companies:
            company_name = company["company_name"]
            employee_count = company.get("employee_count", 50)
            job_titles = [job["job_title"] for job in company.get("jobs", [])]
            
            # Determine target role
            target_role, alternative_roles = self.determine_target_role(employee_count, job_titles)
            
            print(f"\n📊 {company_name} ({employee_count} employees)")
            print(f"🎯 Target role: {target_role}")
            
            # Search for decision-maker
            decision_maker = self.search_decision_maker(company_name, target_role, alternative_roles)
            
            results.append({
                "company_name": company_name,
                "decision_maker": decision_maker,
                "target_role_attempted": target_role,
                "search_confidence": "high" if decision_maker else "none"
            })
        
        # Calculate cost
        cost = self.search_count * 0.001  # $0.001 per search
        print(f"\n💰 Exa API cost: ${cost:.4f} ({self.search_count} searches)")
        
        # Update Supabase
        if self.logger and self.run_id:
            self.logger.update_phase(
                run_id=self.run_id,
                phase="finding_decision_makers",
                cost_of_run=f"${self.openai_caller.get_cost_estimate():.3f} OpenAI, ${cost:.3f} Exa"
            )
        
        return results

def main():
    parser = argparse.ArgumentParser(description="Find decision-makers for companies")
    parser.add_argument("--companies", required=True, help="Path to companies JSON")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--run-id", help="Run ID for logging")
    args = parser.parse_args()
    
    # Load companies
    with open(args.companies, 'r') as f:
        companies = json.load(f)
    
    # Find decision-makers
    finder = DecisionMakerFinder(run_id=args.run_id)
    results = finder.find_decision_makers(companies)
    
    # Save output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    found_count = sum(1 for r in results if r["decision_maker"])
    print(f"\n✅ Found {found_count}/{len(results)} decision-makers")
    print(f"✅ Saved to {output_path}")

if __name__ == "__main__":
    main()
