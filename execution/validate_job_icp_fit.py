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
        print(f"  Recruiter ICP: {recruiter_icp.get('recruiter_summary', 'N/A')}")
        
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
                    # Store validation reason with job for email context
                    job_with_reason = job.copy()
                    job_with_reason["validation_reason"] = reason
                    valid_jobs.append(job_with_reason)
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
        
        # Call OpenAI with upgraded model for stricter validation
        response = self.openai_caller.call_with_retry(
            prompt=prompt,
            model="gpt-4.1-mini",
            temperature=0.05,  # Ultra-low temperature for strictest validation
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
        
        recruiter_summary = recruiter_icp.get('recruiter_summary', 'No summary available')
        
        return f"""Does this job match what the recruiter does?

CRITICAL: The recruiter finds people to fill jobs AT companies. They do NOT work at these companies.

RECRUITER:
{recruiter_summary}

JOB:
Company: {company_name}
Description: {company_description}
Title: {job_title}
Job Details: {job_description}

VALIDATION RULES (STRICT):
1. **REJECT if company is a recruiting/staffing/consulting agency** - The recruiter doesn't place roles AT other recruiting firms
   - INSTANT REJECT keywords: "recruitment", "staffing", "talent", "headhunting", "executive search", "our client", "client company"
   - INSTANT REJECT if company description is vague/generic: "Empowering Businesses", "Scalable Solutions", "Innovative Technology", "Unmatched Productivity", "Career Development", "Resume Writing", "ATS-friendly" with NO specific product/service
   - INSTANT REJECT if job description says "our client" or "client is" - this means consulting/recruiting firm placing for someone else

2. **REJECT if company is wrong industry vertical OR has no real product**
   - Example: If recruiter serves "molecular diagnostics", REJECT "vending machines", "hospitality", "retail", "food service", "luxury amenities", "consumer goods"
   - REJECT lead gen companies, course sellers, coaching platforms, career services, resume builders
   - REJECT if company description mentions "courses", "coaching", "training", "learning platform", "career development", "job placement", "staffing solutions"
   - ONLY accept if company has REAL product/service and directly serves the recruiter's buyer type (e.g., health systems, labs, physicians, diagnostic companies)

3. **Deeply understand the recruiter's ACTUAL role type** - Read the recruiter summary carefully
   - If recruiter says "clinical trial execution" or "clinical research associates", understand they mean PATIENT-FACING, SITE-BASED, TRIAL MANAGEMENT roles
   - NOT bench science, NOT lab work, NOT supply chain/logistics, NOT manufacturing QA
   - Example: A recruiter who fills "Clinical Research Associates" wants CRAs who monitor trial sites, NOT scientists doing lab research
   - Example: "Regulatory Affairs" for a clinical recruiter means FDA submissions, protocol design - NOT supply chain compliance or logistics
   - Look at the ACTUAL job description details - is it about trial execution, patients, sites, protocols? Or is it about shipping, logistics, warehouse, distribution?

4. **Match the ROLE TYPE** - Is this the kind of role the recruiter fills?
   - Example: If recruiter fills "clinical sales", accept "Territory Manager - Diagnostics", reject "VP Sales - Vending"
   - Read the job description carefully to understand what the role actually DOES day-to-day, not just the title

5. **Match SENIORITY** - Is this the right level?
   - Be flexible with this: "Director" can work for exec search, but NOT if industry is mismatched

Output JSON:
{{
  "is_match": true/false,
  "confidence": "high/medium/low",
  "reason": "Why it matches or doesn't - be specific about company type",
  "industry_match": true/false,
  "role_match": true/false,
  "seniority_match": true/false
}}"""


def main():
    """Test job validation"""
    import sys
    from pathlib import Path
    
    # Mock data for testing
    recruiter_icp = {
        "recruiter_summary": "Recruiter specializing in CPG and food manufacturing, filling VP Operations, Director Supply Chain, and VP Sales roles in the United States."
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
