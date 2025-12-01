"""
Job-ICP Fit Validator
CRITICAL: Validates that jobs actually match recruiter's ICP BEFORE including in email
Prevents mismatches like "biotech scientist" for "CPG operations recruiter"
"""

import json
from typing import Dict, List, Any, Optional
from execution.call_openai import OpenAICaller


class JobICPValidator:
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id
        self.openai_caller = OpenAICaller(run_id=run_id)
        self.validation_count = 0
        self.passed_count = 0
        self.failed_count = 0
    
    def validate_jobs_for_companies(self, companies: List[Dict[str, Any]], 
                                   recruiter_icp: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Validate that each company's jobs actually match the recruiter's ICP
        CRITICAL: This prevents sending irrelevant jobs to recruiters
        
        Args:
            companies: List of companies with jobs
            recruiter_icp: Recruiter's ideal client profile
            
        Returns:
            List of companies with only validated jobs (companies with 0 valid jobs are removed)
        """
        print(f"\n🔍 CRITICAL VALIDATION: Checking job-ICP fit for {len(companies)} companies...")
        print(f"  Recruiter ICP:")
        print(f"    Industries: {', '.join(recruiter_icp.get('industries', []))}")
        print(f"    Roles: {', '.join(recruiter_icp.get('roles_filled', [])[:5])}...")
        print(f"    Seniority: {self._infer_seniority_level(recruiter_icp)}")
        
        validated_companies = []
        
        for company in companies:
            company_name = company.get("name") or company.get("company_name", "Unknown")
            jobs = company.get("jobs", [])
            
            if not jobs:
                print(f"  ⚠️ {company_name}: No jobs to validate, skipping")
                continue
            
            print(f"\n  📋 Validating {len(jobs)} jobs for {company_name}...")
            
            valid_jobs = []
            for job in jobs:
                is_valid, reason = self._validate_single_job(job, company, recruiter_icp)
                
                if is_valid:
                    valid_jobs.append(job)
                    self.passed_count += 1
                    job_title = job.get("title") or job.get("job_title", "Unknown")
                    print(f"    ✅ {job_title}")
                else:
                    self.failed_count += 1
                    job_title = job.get("title") or job.get("job_title", "Unknown")
                    print(f"    ❌ {job_title}: {reason}")
                
                self.validation_count += 1
            
            # Only include company if it has at least 1 valid job
            if valid_jobs:
                company_copy = company.copy()
                company_copy["jobs"] = valid_jobs
                validated_companies.append(company_copy)
                print(f"  ✅ {company_name}: {len(valid_jobs)}/{len(jobs)} jobs passed validation")
            else:
                print(f"  ❌ {company_name}: 0/{len(jobs)} jobs passed validation - REMOVED")
        
        print(f"\n✅ Validation Complete:")
        print(f"  Total jobs validated: {self.validation_count}")
        print(f"  Passed: {self.passed_count} ({(self.passed_count/self.validation_count*100) if self.validation_count > 0 else 0:.1f}%)")
        print(f"  Failed: {self.failed_count} ({(self.failed_count/self.validation_count*100) if self.validation_count > 0 else 0:.1f}%)")
        print(f"  Companies with valid jobs: {len(validated_companies)}/{len(companies)}")
        
        return validated_companies
    
    def _validate_single_job(self, job: Dict[str, Any], company: Dict[str, Any], 
                            recruiter_icp: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate a single job against recruiter ICP
        Returns: (is_valid, reason)
        """
        job_title = job.get("title") or job.get("job_title", "Unknown")
        job_description = job.get("description") or job.get("descriptionText", "")
        company_name = company.get("name") or company.get("company_name", "Unknown")
        company_description = company.get("description") or company.get("company_description", "")
        
        # Build validation prompt
        prompt = self._build_validation_prompt(
            job_title=job_title,
            job_description=job_description[:1000],  # Limit to first 1000 chars
            company_name=company_name,
            company_description=company_description[:500],
            recruiter_icp=recruiter_icp
        )
        
        # Call OpenAI for validation
        response = self.openai_caller.call_with_retry(
            prompt=prompt,
            model="gpt-4o-mini",
            temperature=0.1,  # Very low temperature for consistent validation
            response_format="json"
        )
        
        if not response:
            return False, "Validation API call failed"
        
        try:
            result = json.loads(response)
            is_match = result.get("is_match", False)
            reason = result.get("reason", "No reason provided")
            confidence = result.get("confidence", "unknown")
            
            # Require high confidence for matches
            if is_match and confidence == "low":
                return False, f"Low confidence match: {reason}"
            
            return is_match, reason
            
        except json.JSONDecodeError:
            return False, "Failed to parse validation response"
    
    def _build_validation_prompt(self, job_title: str, job_description: str,
                                company_name: str, company_description: str,
                                recruiter_icp: Dict[str, Any]) -> str:
        """Build prompt for job-ICP validation"""
        
        seniority_level = self._infer_seniority_level(recruiter_icp)
        
        return f"""You are a recruiter matching expert. Determine if this job is a STRONG MATCH for the recruiter's ICP.

CRITICAL: This must be a PRECISE match. The recruiter specializes in specific industries, roles, and seniority levels.

RECRUITER'S ICP:
Industries: {', '.join(recruiter_icp.get('industries', []))}
Roles They Fill: {', '.join(recruiter_icp.get('roles_filled', []))}
Inferred Seniority Level: {seniority_level}
Geography: {', '.join(recruiter_icp.get('geographies', []))}

JOB TO VALIDATE:
Company: {company_name}
Company Description: {company_description}
Job Title: {job_title}
Job Description: {job_description}

VALIDATION RULES:
1. **Industry Match is MANDATORY**
   - Company must be in one of the recruiter's target industries
   - Example: If recruiter serves "CPG", company must be in food/beverage/consumer products
   - REJECT if wrong industry (e.g., "Biotech" when recruiter serves "CPG")

2. **Role Type Match is MANDATORY**
   - Job title must match recruiter's role specialization
   - Example: If recruiter fills "VP Operations", reject "Accounts Payable Clerk"
   - Be flexible with similar roles (e.g., "Head of Supply Chain" matches "VP Supply Chain")

3. **Seniority Level Match is MANDATORY**
   - Inferred seniority: {seniority_level}
   - Executive search → VP, Director, Head of, SVP, C-Suite only
   - Mid-level search → Manager, Senior Manager, Team Lead
   - Entry-level search → Associate, Coordinator, Junior
   - REJECT if seniority doesn't match

4. **Geography** - Important but flexible
   - Prefer matches in recruiter's geography
   - Can be flexible for remote roles

SCORING:
- is_match = true ONLY if ALL mandatory criteria match
- confidence = "high" if perfect match, "medium" if close, "low" if borderline

Output (JSON only):
{{
  "is_match": true/false,
  "confidence": "high/medium/low",
  "reason": "Brief explanation of match/mismatch",
  "industry_match": true/false,
  "role_match": true/false,
  "seniority_match": true/false
}}"""
    
    def _infer_seniority_level(self, recruiter_icp: Dict[str, Any]) -> str:
        """Infer seniority level from roles and industries"""
        roles = recruiter_icp.get("roles_filled", [])
        industries = recruiter_icp.get("industries", [])
        
        # Check for executive indicators
        executive_keywords = ["VP", "Vice President", "Director", "Head of", "Chief", "SVP", "C-Suite", "Executive", "GM", "General Manager"]
        for role in roles:
            if any(keyword.lower() in role.lower() for keyword in executive_keywords):
                return "Executive/Senior Leadership ($150k-$500k+)"
        
        # Check for mid-level indicators
        mid_keywords = ["Manager", "Senior", "Lead", "Sr."]
        for role in roles:
            if any(keyword.lower() in role.lower() for keyword in mid_keywords):
                if not any(ex.lower() in role.lower() for ex in ["VP", "Director", "Head"]):
                    return "Mid-Level Management ($80k-$150k)"
        
        # Check for entry-level indicators
        entry_keywords = ["Associate", "Coordinator", "Junior", "Assistant", "Analyst"]
        for role in roles:
            if any(keyword.lower() in role.lower() for keyword in entry_keywords):
                return "Entry-Level/Individual Contributor ($40k-$80k)"
        
        # Default to mid-senior if unclear
        return "Mid-Senior Level ($80k-$200k)"


def main():
    """Test job validation"""
    import sys
    from pathlib import Path
    
    # Mock data for testing
    recruiter_icp = {
        "industries": ["Consumer Packaged Goods", "Food & Beverage", "Manufacturing"],
        "roles_filled": ["VP Operations", "Director Supply Chain", "Head of Procurement", "VP Sales"],
        "geographies": ["United States"]
    }
    
    companies = [
        {
            "name": "Biotech Inc",
            "description": "Clinical stage biotech company developing therapies",
            "jobs": [
                {"title": "Statistical Programmer", "description": "SAS programming for clinical trials"}
            ]
        },
        {
            "name": "Premium Foods Co",
            "description": "National food manufacturing company",
            "jobs": [
                {"title": "VP Operations", "description": "Lead multi-site manufacturing operations for beverage division"}
            ]
        }
    ]
    
    validator = JobICPValidator()
    validated = validator.validate_jobs_for_companies(companies, recruiter_icp)
    
    print(f"\n\nFinal validated companies: {len(validated)}")
    for company in validated:
        print(f"  - {company['name']}: {len(company['jobs'])} jobs")


if __name__ == "__main__":
    main()
