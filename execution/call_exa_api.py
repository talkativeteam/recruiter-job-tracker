"""
Exa API Caller - Alternative Company Discovery
Used as fallback when LinkedIn returns insufficient results
Uses simple search_and_contents (no websets) for reliable results
"""

import os
import json
from typing import Dict, List, Any, Optional
from exa_py import Exa
from config.config import EXA_API_KEY


class ExaCompanyFinder:
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id
        self.exa_client = Exa(api_key=EXA_API_KEY) if EXA_API_KEY else None
        self.search_count = 0
        self.total_results = 0
        
    def find_companies(self, icp_data: Dict[str, Any], max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Use Exa to find companies hiring for roles matching the ICP
        
        Args:
            icp_data: Recruiter ICP containing industries, roles, skills
            max_results: Maximum number of companies to find
            
        Returns:
            List of company dictionaries with name, website, description
        """
        if not self.exa_client:
            print("❌ Exa API key not configured")
            return []
        
        try:
            # Build structured Exa search criteria
            search_query = self._build_exa_criteria(icp_data)
            print(f"🔍 Exa search criteria: {search_query}")
            
            # Search for companies with career pages
            results = self.exa_client.search_and_contents(
                query=search_query,
                num_results=max_results,
                text={"max_characters": 2000}
            )
            
            # Track usage for cost calculation
            self.search_count += 1
            self.total_results += len(results.results)
            
            # Parse results into company format with deduplication
            companies = []
            seen_domains = set()
            
            for result in results.results:
                company = self._parse_exa_result(result)
                if company:
                    # Deduplicate by domain
                    domain = company["company_url"]
                    if domain not in seen_domains:
                        companies.append(company)
                        seen_domains.add(domain)
            
            print(f"✅ Exa found {len(companies)} unique companies")
            cost = self.get_cost_estimate()
            print(f"💰 Exa API cost: ${cost:.4f} ({self.search_count} searches, {self.total_results} results)")
            return companies
            
        except Exception as e:
            print(f"❌ Exa API error: {e}")
            return []
    
    def get_cost_estimate(self) -> float:
        """
        Calculate Exa API cost
        
        Exa Pricing (search_and_contents):
        - Search: 1 credit per search
        - Contents: 1 credit per result with text extraction
        - Rate: $5 per 1000 credits
        
        So for 20 results with contents:
        - 1 search = 1 credit
        - 20 results × 1 credit each = 20 credits
        - Total: 21 credits per search = $0.105
        
        Reference: https://docs.exa.ai/reference/pricing
        """
        # Each search with contents costs: 1 search + num_results contents
        # We fetch 20 results per search, so: 1 + 20 = 21 credits per search
        credits_per_search = 21  # 1 for search + 20 for content extraction
        cost_per_credit = 0.005  # $5 per 1000 credits
        return self.search_count * credits_per_search * cost_per_credit
    
    def _build_exa_criteria(self, icp_data: Dict[str, Any]) -> str:
        """
        Build structured Exa search criteria from ICP data
        Format: Natural language that Exa can interpret as filters
        
        Target: Companies under ~200 employees, posted about hiring in last 14 days (broader by ~30%)
        """
        from datetime import datetime, timedelta
        
        roles = icp_data.get("roles_filled", icp_data.get("roles", []))
        industries = icp_data.get("industries", [])
        
        # Calculate date range (last 14 days)
        today = datetime.now()
        fourteen_days_ago = today - timedelta(days=14)
        date_start = fourteen_days_ago.strftime("%B %d, %Y").lower()
        date_end = today.strftime("%B %d, %Y").lower()
        
        # Build criteria components
        criteria_parts = []
        
        # CRITICAL: Industry criteria FIRST and SPECIFIC
        # Industries should be company types (e.g., "Digital Agency", "SaaS Company")
        if industries:
            # Be more specific about company type matching
            industry_descriptors = []
            for industry in industries[:3]:
                industry_lower = industry.lower()
                # Add specific descriptors based on industry type
                if "agency" in industry_lower or "agencies" in industry_lower:
                    industry_descriptors.append(f"is a {industry_lower}")
                elif "saas" in industry_lower or "software" in industry_lower:
                    industry_descriptors.append(f"is a {industry_lower}")
                else:
                    industry_descriptors.append(f"operates in {industry_lower}")
            
            industry_clause = " or ".join(industry_descriptors)
            criteria_parts.append(f"company {industry_clause}")
        
        # Role/hiring criteria (secondary filter)
        if roles:
            role_list = " or ".join(roles[:3]).lower()
            criteria_parts.append(f"hiring for {role_list}")
        else:
            criteria_parts.append("actively hiring")
        
        # Size criteria (broadened)
        criteria_parts.append("company has under 200 employees")
        
        # Timing criteria
        criteria_parts.append(f"posted about hiring between {date_start} and {date_end}")
        
        # Exclusions
        criteria_parts.append("company is not a recruitment or staffing firm")
        
        # Combine into natural language query
        query = ", ".join(criteria_parts)
        
        return query
    
    def _parse_exa_result(self, result: Any) -> Optional[Dict[str, Any]]:
        """
        Parse Exa search result into company format
        Filter out large companies and job aggregators
        """
        try:
            # Extract company name from domain
            url = result.url
            domain = url.split("//")[-1].split("/")[0]
            
            # Filter out job boards and large company aggregators
            job_board_domains = [
                "linkedin", "indeed", "glassdoor", "monster", "ziprecruiter",
                "careers.google", "jobs.apple", "careers.microsoft", 
                "careers.amazon", "jobs.netflix", "greenhouse.io",
                "lever.co", "workday", "icims", "taleo", "jobvite"
            ]
            
            if any(board in domain.lower() for board in job_board_domains):
                return None
            
            # Extract company name (better parsing)
            company_name = domain.replace("www.", "").replace("careers.", "").split(".")[0]
            # Capitalize properly
            company_name = " ".join(word.capitalize() for word in company_name.split("-"))
            
            # Check if this is actually a career page
            if not self._is_career_page(url, result.text):
                return None
            
            return {
                "name": company_name,
                "company_url": self._get_main_domain(url),
                "careers_url": url,
                "description": result.text[:500] if result.text else "",
                "jobs": [],  # Will be populated by job extraction
                "source": "exa"
            }
            
        except Exception as e:
            print(f"⚠️ Failed to parse Exa result: {e}")
            return None
    
    def _is_career_page(self, url: str, text: str) -> bool:
        """
        Check if URL/content is actually a career/jobs page
        """
        career_indicators = ["career", "jobs", "hiring", "opportunities", "join", "team"]
        
        # Check URL
        url_lower = url.lower()
        if any(indicator in url_lower for indicator in career_indicators):
            return True
        
        # Check content (if available)
        if text:
            text_lower = text.lower()
            career_mentions = sum(1 for indicator in career_indicators if indicator in text_lower)
            if career_mentions >= 2:  # At least 2 career-related words
                return True
        
        return False
    
    def _get_main_domain(self, url: str) -> str:
        """
        Extract main domain from career page URL
        """
        # Remove path, keep only domain
        parts = url.split("//")
        if len(parts) > 1:
            domain = parts[1].split("/")[0]
            return f"https://{domain}"
        return url
    
    def find_companies_with_boolean(self, boolean_search: str, country_code: str = "US", max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Alternative method: Use boolean search terms to find companies via Exa
        
        Args:
            boolean_search: LinkedIn boolean search string
            country_code: Country code for targeting
            max_results: Maximum companies to find
            
        Returns:
            List of companies
        """
        if not self.exa_client:
            print("❌ Exa API key not configured")
            return []
        
        try:
            # Convert boolean search to natural language for Exa
            # Remove LinkedIn-specific syntax
            query = boolean_search.replace('"', '').replace('AND', '').replace('OR', 'or')
            query = f"companies hiring for: {query} - careers page"
            
            print(f"🔍 Exa fallback query: {query}")
            
            results = self.exa_client.search_and_contents(
                query=query,
                num_results=max_results,
                text={"max_characters": 2000},
                category="company"
            )
            
            companies = []
            for result in results.results:
                company = self._parse_exa_result(result)
                if company:
                    companies.append(company)
            
            print(f"✅ Exa fallback found {len(companies)} companies")
            return companies
            
        except Exception as e:
            print(f"❌ Exa fallback error: {e}")
            return []
