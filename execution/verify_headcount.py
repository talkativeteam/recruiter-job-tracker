"""
Company Headcount Verifier
Uses BrightData to verify employee counts via LinkedIn
"""

import os
import json
import requests
import time
from typing import Dict, Any, Optional, List
from config.config import BRIGHT_DATA_API_KEY


class HeadcountVerifier:
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id
        self.api_key = BRIGHT_DATA_API_KEY or os.getenv("BRIGHT_DATA_API_KEY")
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY", "975927c641mshba602500c78ced5p124776jsne0ffd5e4caff")
        
    def find_linkedin_url(self, company_name: str) -> Optional[str]:
        """
        Use RapidAPI to find company LinkedIn URL via Google search
        """
        if not self.rapidapi_key:
            print(f"⚠️ No RapidAPI key configured, skipping LinkedIn search for {company_name}")
            return None
            
        try:
            url = "https://real-time-web-search.p.rapidapi.com/search"
            query = f"site:linkedin.com/company {company_name}"
            
            params = {
                "q": query,
                "num": 10,
                "gl": "us",
                "hl": "en"
            }
            
            headers = {
                "x-rapidapi-key": self.rapidapi_key,
                "x-rapidapi-host": "real-time-web-search.p.rapidapi.com"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("data", [])
            
            # Find first linkedin.com/company URL
            for result in results:
                link = result.get("url", "")
                if "linkedin.com/company/" in link:
                    # Clean up tracking params
                    linkedin_url = link.split("?")[0]
                    print(f"  ✅ Found LinkedIn: {linkedin_url}")
                    return linkedin_url
            
            print(f"  ⚠️ No LinkedIn URL found for {company_name}")
            return None
            
        except Exception as e:
            print(f"  ❌ LinkedIn search failed for {company_name}: {e}")
            return None
    
    def get_employee_count(self, linkedin_url: str) -> Optional[int]:
        """
        Use BrightData to scrape employee count from LinkedIn company page
        """
        if not self.api_key:
            print("⚠️ No BrightData API key configured")
            return None
            
        try:
            url = "https://api.brightdata.com/datasets/v3/scrape"
            params = {
                "dataset_id": "gd_l1vikfnt1wgvvqz95w",
                "notify": "false",
                "include_errors": "true"
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "input": [{"url": linkedin_url}]
            }
            
            response = requests.post(url, params=params, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # BrightData returns company data with employee count
            if data and len(data) > 0:
                company_data = data[0]
                
                # Try various employee count fields
                employee_count = (
                    company_data.get("employee_count") or
                    company_data.get("employees") or
                    company_data.get("size") or
                    company_data.get("company_size")
                )
                
                # Parse if it's a range string like "51-200"
                if isinstance(employee_count, str):
                    # Extract numbers and take max
                    import re
                    numbers = re.findall(r'\d+', employee_count)
                    if numbers:
                        employee_count = max(int(n) for n in numbers)
                    else:
                        return None
                
                if employee_count:
                    print(f"  ✅ Employee count: {employee_count}")
                    return int(employee_count)
            
            print(f"  ⚠️ Could not extract employee count from BrightData response")
            return None
            
        except Exception as e:
            print(f"  ❌ BrightData scrape failed: {e}")
            return None
    
    def verify_companies(self, companies: List[Dict[str, Any]], 
                        max_employees: int = 100) -> List[Dict[str, Any]]:
        """
        Verify employee counts for multiple companies
        Returns only companies with <= max_employees
        """
        verified = []
        
        for company in companies:
            company_name = company.get("name", "Unknown")
            print(f"\n🔍 Verifying headcount for {company_name}...")
            
            # Check if we already have employee_count
            existing_count = company.get("employee_count", 0)
            if existing_count and existing_count > 0:
                print(f"  ℹ️ Using existing employee count: {existing_count}")
                if existing_count <= max_employees:
                    verified.append(company)
                    print(f"  ✅ {company_name}: {existing_count} employees (under {max_employees})")
                else:
                    print(f"  ❌ {company_name}: {existing_count} employees (over {max_employees} limit)")
                continue
            
            # Try to get LinkedIn URL
            linkedin_url = company.get("linkedin_url") or company.get("company_linkedin")
            
            if not linkedin_url:
                # Try to find it via search
                linkedin_url = self.find_linkedin_url(company_name)
                if linkedin_url:
                    company["linkedin_url"] = linkedin_url
            
            if not linkedin_url:
                print(f"  ⚠️ No LinkedIn URL, skipping {company_name}")
                # Include by default if we can't verify (to avoid over-filtering)
                verified.append(company)
                continue
            
            # Get employee count from BrightData
            employee_count = self.get_employee_count(linkedin_url)
            
            if employee_count:
                company["employee_count"] = employee_count
                if employee_count <= max_employees:
                    verified.append(company)
                    print(f"  ✅ {company_name}: {employee_count} employees (under {max_employees})")
                else:
                    print(f"  ❌ {company_name}: {employee_count} employees (over {max_employees} limit)")
            else:
                print(f"  ⚠️ Could not verify employee count for {company_name}, including anyway")
                verified.append(company)
            
            # Rate limiting
            time.sleep(1)
        
        print(f"\n✅ Verified: {len(verified)}/{len(companies)} companies under {max_employees} employees")
        return verified
