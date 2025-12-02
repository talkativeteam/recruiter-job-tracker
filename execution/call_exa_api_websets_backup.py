"""
Exa API client using official SDK with websets.
Generates criteria from ICP data using AI, then creates webset.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional
from exa_py import Exa
from exa_py.websets.types import CreateWebsetParameters, CreateCriterionParameters
from config.config import EXA_API_KEY
from execution.call_openai import OpenAICaller


class ExaCompanyFinder:
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id
        self.exa_client = Exa(api_key=EXA_API_KEY) if EXA_API_KEY else None
        self.openai_caller = OpenAICaller(run_id=run_id) if run_id else OpenAICaller()
        
    def find_companies(self, icp_data: Dict[str, Any], max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Use Exa websets to find companies hiring for roles matching the ICP
        Uses AI-generated structured criteria for better filtering
        
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
            # Generate criteria using AI
            print(f"📝 Generating Exa search criteria from ICP...")
            criteria_strings = self._generate_criteria_with_ai(icp_data, max_company_size=100)
            
            print(f"📋 Generated {len(criteria_strings)} criteria:")
            for i, c in enumerate(criteria_strings, 1):
                print(f"  {i}. {c}")
            
            # Build search query
            search_query = self._build_search_query_from_icp(icp_data)
            print(f"🔍 Exa search query: {search_query}")
            
            # Convert criteria strings to Exa format
            try:
                criteria_objects = [CreateCriterionParameters(description=c) for c in criteria_strings]
            except:
                # Fallback if websets not available - use simple dict
                criteria_objects = [{"description": c} for c in criteria_strings]
            
            # Create webset
            print(f"🌐 Creating Exa webset...")
            try:
                webset = self.exa_client.websets.create(
                    params=CreateWebsetParameters(
                        search={
                            "query": search_query,
                            "criteria": criteria_objects,
                            "count": max_results
                        },
                        enrichments=[]
                    )
                )
                
                webset_id = webset.id
                print(f"✅ Webset created: {webset_id}, polling for completion...")
                
                # Poll until complete
                companies = self._poll_webset(webset_id)
                
            except AttributeError:
                # Fallback: websets API not available, use simple search
                print(f"⚠️ Websets API not available, falling back to simple search")
                return self._simple_search_fallback(search_query, max_results)
            
            print(f"✅ Exa found {len(companies)} unique companies")
            return companies
            
        except Exception as e:
            print(f"❌ Exa API error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _generate_criteria_with_ai(self, icp_data: Dict[str, Any], max_company_size: int = 200) -> List[str]:
        """
        Generate Exa search criteria from ICP data using AI
        Returns list of atomic criteria statements
        """
        from datetime import datetime, timedelta
        from config import ai_prompts
        
        roles = icp_data.get("roles_filled", icp_data.get("roles", []))
        industries = icp_data.get("industries", [])
        
        # Calculate date range (last 14 days)
        today = datetime.now()
        fourteen_days_ago = today - timedelta(days=14)
        date_start = fourteen_days_ago.strftime("%B %d, %Y").lower()
        date_end = today.strftime("%B %d, %Y").lower()
        
        # Build search query for AI prompt
        role_str = ", ".join(roles[:3]) if roles else "any role"
        industry_str = ", ".join(industries[:2]) if industries else "any industry"
        search_query = f"companies in {industry_str} hiring for {role_str}"
        
        # Use AI to generate criteria with proper prompt template
        try:
            prompt = ai_prompts.format_exa_criteria_prompt(
                icp_data=icp_data,
                max_company_size=max_company_size,
                jobs_posted_timeframe="last 14 days"
            )
            
            response = self.openai_caller.call_with_retry(
                prompt=prompt,
                model="gpt-4o-mini",
                response_format="json"
            )
            
            criteria = json.loads(response)
            if isinstance(criteria, list):
                return criteria
            elif isinstance(criteria, dict) and "criteria" in criteria:
                return criteria["criteria"]
        except Exception as e:
            print(f"⚠️ AI criteria generation failed: {e}, using fallback")
        
        # Fallback criteria
        criteria_parts = []
        
        if industries:
            industry_list = " or ".join(industries[:3]).lower()
            criteria_parts.append(f"company is in {industry_list} sector")
        
        if roles:
            role_list = " or ".join(roles[:3]).lower()
            criteria_parts.append(f"company is hiring for {role_list}")
        else:
            criteria_parts.append("company is actively hiring")
        
        criteria_parts.append(f"company has under {max_company_size} employees")
        criteria_parts.append(f"company posted about hiring between {date_start} and {date_end}")
        criteria_parts.append("company is not a recruitment or staffing firm")
        
        return criteria_parts
    
    def _build_search_query_from_icp(self, icp_data: Dict[str, Any]) -> str:
        """
        Build natural language search query from ICP
        """
        roles = icp_data.get("roles_filled", icp_data.get("roles", []))
        industries = icp_data.get("industries", [])
        
        query_parts = []
        
        if industries:
            query_parts.append(industries[0])
        
        if roles:
            query_parts.append(f"hiring {roles[0]}")
        else:
            query_parts.append("hiring now")
        
        query_parts.append("careers")
        
        return " ".join(query_parts)
    
    def _poll_webset(self, webset_id: str, max_wait: int = 600) -> List[Dict[str, Any]]:
        """
        Poll Exa webset until complete and extract companies
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                webset_data = self.exa_client.websets.get(webset_id, expand=["items"])
                
                status = webset_data.status
                searches = webset_data.searches if hasattr(webset_data, 'searches') else []
                
                # Check if all searches are complete
                if searches:
                    search_statuses = [s.status for s in searches]
                    all_complete = all(s in ["complete", "completed"] for s in search_statuses)
                    
                    if all_complete:
                        elapsed = int(time.time() - start_time)
                        print(f"✅ Webset complete after {elapsed}s")
                        return self._parse_webset_data(webset_data)
                    
                    elif "failed" in search_statuses:
                        raise RuntimeError(f"Exa search failed")
                
                print(f"⏳ Polling... ({int(time.time() - start_time)}s)")
                time.sleep(3)
                
            except Exception as e:
                print(f"⚠️ Polling error: {e}")
                time.sleep(3)
        
        raise TimeoutError(f"Exa webset did not complete within {max_wait}s")
    
    def _parse_webset_data(self, webset_data: Any) -> List[Dict[str, Any]]:
        """
        Parse webset data into company format
        """
        data = webset_data.model_dump() if hasattr(webset_data, 'model_dump') else webset_data
        items = data.get("items", [])
        
        companies = []
        seen_domains = set()
        
        for item in items:
            try:
                properties = item.get("properties", {})
                
                if properties.get("type") == "company":
                    company_data = properties.get("company", {})
                    url = properties.get("url", "")
                    url_str = str(url) if url else ""
                    domain = url_str.replace("https://", "").replace("http://", "").split("/")[0]
                    
                    if domain not in seen_domains:
                        seen_domains.add(domain)
                        
                        # Extract company name
                        company_name = company_data.get("name") or domain.replace("www.", "").replace("careers.", "").split(".")[0]
                        company_name = " ".join(word.capitalize() for word in company_name.split("-"))
                        
                        companies.append({
                            "name": company_name,
                            "company_url": f"https://{domain}" if not url_str.startswith("http") else url_str,
                            "careers_url": url_str,
                            "description": properties.get("description", "")[:500],
                            "jobs": [],
                            "source": "exa"
                        })
            except Exception as e:
                print(f"⚠️ Failed to parse item: {e}")
                continue
        
        return companies
    
    def _simple_search_fallback(self, search_query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Fallback to simple search if websets not available
        """
        try:
            results = self.exa_client.search_and_contents(
                query=search_query,
                num_results=max_results,
                text={"max_characters": 2000}
            )
            
            companies = []
            seen_domains = set()
            
            for result in results.results:
                company = self._parse_exa_result(result)
                if company:
                    domain = company["company_url"]
                    if domain not in seen_domains:
                        companies.append(company)
                        seen_domains.add(domain)
            
            return companies
            
        except Exception as e:
            print(f"❌ Fallback search failed: {e}")
            return []
    
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
