"""
Deep ICP Extraction with Playwright
Analyzes recruiter website About page and other key pages to extract detailed ICP
"""

import sys
from pathlib import Path
from typing import Dict, Optional
import json
from urllib.parse import urljoin, urlparse

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.config import TIMEOUT_PLAYWRIGHT
from execution.call_openai import OpenAICaller
from execution.supabase_logger import SupabaseLogger

class DeepICPExtractor:
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id
        self.logger = SupabaseLogger() if run_id else None
        self.openai_caller = OpenAICaller(run_id=run_id)
    
    def extract_icp(self, base_url: str) -> Dict:
        """
        Extract ICP from recruiter website using Playwright for deeper analysis
        
        Args:
            base_url: Recruiter's website URL
            
        Returns:
            Dict with ICP data including industries, roles, geographies, etc.
        """
        print(f"🎯 Deep ICP extraction for {base_url}...")
        
        # Step 1: Find relevant pages (About, Services, Sectors, etc.)
        relevant_pages = self._find_relevant_pages(base_url)
        
        # Step 2: Scrape all relevant pages with Playwright
        page_contents = self._scrape_pages(relevant_pages)
        
        # Step 3: Extract ICP with AI using combined content
        icp_data = self._extract_icp_with_ai(page_contents, base_url)
        
        return icp_data
    
    def _find_relevant_pages(self, base_url: str) -> Dict[str, str]:
        """
        Find About, Services, Sectors pages using Playwright
        
        Returns:
            Dict of {page_type: url}
        """
        try:
            from playwright.sync_api import sync_playwright
            
            pages = {"homepage": base_url}
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(base_url, timeout=TIMEOUT_PLAYWRIGHT * 1000)
                page.wait_for_load_state("networkidle", timeout=TIMEOUT_PLAYWRIGHT * 1000)
                
                # Find links to About, Services, Sectors, etc.
                links = page.query_selector_all("a")
                
                target_keywords = {
                    "about": ["about", "about-us", "about us", "who-we-are", "our-story"],
                    "services": ["services", "what-we-do", "solutions", "offerings"],
                    "sectors": ["sectors", "industries", "specialisms", "expertise"],
                    "team": ["team", "our-team", "people", "leadership"]
                }
                
                for link in links:
                    try:
                        href = link.get_attribute("href")
                        text = link.inner_text().lower().strip()
                        
                        if not href:
                            continue
                        
                        # Convert to absolute URL
                        full_url = urljoin(base_url, href)
                        
                        # Check if URL or text matches any target keyword
                        for page_type, keywords in target_keywords.items():
                            if page_type not in pages:
                                for keyword in keywords:
                                    if keyword in full_url.lower() or keyword == text.replace(" ", "-"):
                                        pages[page_type] = full_url
                                        print(f"  ✅ Found {page_type} page: {full_url}")
                                        break
                    except Exception as e:
                        continue
                
                browser.close()
            
            print(f"  📄 Found {len(pages)} relevant pages")
            return pages
            
        except ImportError:
            print("  ⚠️ Playwright not available, using homepage only")
            return {"homepage": base_url}
        except Exception as e:
            print(f"  ⚠️ Error finding pages: {e}")
            return {"homepage": base_url}
    
    def _scrape_pages(self, pages: Dict[str, str]) -> Dict[str, str]:
        """
        Scrape all pages with Playwright, fallback to HTTP if needed
        
        Returns:
            Dict of {page_type: markdown_content}
        """
        # Try Playwright first
        try:
            from playwright.sync_api import sync_playwright
            from bs4 import BeautifulSoup
            from markdownify import markdownify as md
            
            contents = {}
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                
                for page_type, url in pages.items():
                    try:
                        print(f"  🎭 Scraping {page_type}: {url}")
                        page = browser.new_page()
                        page.goto(url, timeout=TIMEOUT_PLAYWRIGHT * 1000)
                        page.wait_for_load_state("networkidle", timeout=TIMEOUT_PLAYWRIGHT * 1000)
                        
                        # Get HTML content
                        html_content = page.content()
                        
                        # Parse and clean with BeautifulSoup
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # Remove script, style, nav, footer
                        for tag in soup(["script", "style", "nav", "footer", "header"]):
                            tag.decompose()
                        
                        # Convert to markdown
                        markdown_content = md(str(soup))
                        
                        contents[page_type] = markdown_content
                        print(f"    ✅ Scraped {len(markdown_content)} characters")
                        
                        page.close()
                        
                    except Exception as e:
                        print(f"    ❌ Error scraping {page_type}: {e}")
                        continue
                
                browser.close()
            
            return contents
            
        except (ImportError, Exception) as e:
            # Fallback to HTTP scraping for ANY failure (ImportError, browser not installed, timeout, etc.)
            print(f"  ⚠️ Playwright failed ({type(e).__name__}), falling back to HTTP")
            from execution.scrape_website import WebsiteScraper
            scraper = WebsiteScraper(run_id=self.run_id)
            contents = {}
            for page_type, url in pages.items():
                try:
                    success, content, _ = scraper.scrape_http(url)
                    if success:
                        contents[page_type] = content
                        print(f"    ✅ HTTP scraped {page_type}: {len(content)} characters")
                except Exception as http_error:
                    print(f"    ❌ HTTP failed for {page_type}: {http_error}")
                    continue
            
            if not contents:
                print(f"  ❌ Both Playwright and HTTP failed - no content extracted")
            
            return contents
    
    def _extract_icp_with_ai(self, page_contents: Dict[str, str], base_url: str) -> Dict:
        """
        Extract ICP from combined page contents using AI
        
        Returns:
            Dict with ICP data
        """
        # Combine all page contents
        combined_content = ""
        for page_type, content in page_contents.items():
            combined_content += f"\n\n--- {page_type.upper()} PAGE ---\n\n{content[:5000]}"  # Limit each page to 5000 chars
        
        # Truncate if too long
        if len(combined_content) > 20000:
            combined_content = combined_content[:20000] + "\n\n[Content truncated...]"
        
        # Extract domain for geography hints
        domain = urlparse(base_url).netloc
        
        prompt = f"""You are an expert at analyzing recruiter websites to extract their Ideal Client Profile (ICP) and the specific roles they fill.

Your task is to analyze the recruiter's website content from multiple pages and extract:
1. Industries they serve (e.g., "Biotech", "Pharmaceutical", "Healthcare Technology")
2. Company sizes they target (e.g., "10-100 employees", "100-500 employees")
3. Geographies they operate in (countries, states, cities)
4. Specific roles they fill (be PRECISE - e.g., "Sales Director", "Marketing Manager", NOT just "Sales")
5. Keywords for Boolean search (variations of role names)
6. Primary country for LinkedIn search
7. LinkedIn geoId for that country

CRITICAL Rules for Geography:
- Look for ANY location indicators: address, phone numbers, currency symbols (£=UK, $=US, €=EU), domain extensions (.co.uk, .com, .ca)
- If geographies are listed in order (e.g., "UK, EMEA, APAC, US"), the FIRST one is the primary market
- Look for "based in", "located in", "operating from" phrases to identify headquarters
- Email domains can indicate location (.co.uk = UK, .ca = Canada)
- The primary country is where the recruiter is BASED, not just where they recruit

Role Extraction Rules:
- Be SPECIFIC about roles (e.g., "Sales Director", "Marketing Manager", "Business Development Manager")
- Include role variations and levels (e.g., "Sales Manager", "VP Sales", "Head of Sales")
- Extract company size ranges if mentioned
- Identify ALL geographies mentioned
- Pay special attention to "About", "Services", "Sectors" pages for detailed ICP info

LinkedIn geoId Reference:
- United Kingdom: 101165590
- United States: 103644278
- Canada: 101174742
- Germany: 101282230
- Australia: 101452733
- Singapore: 102454443

Domain: {domain}

Website Content from Multiple Pages:
{combined_content}

Output (JSON only, no explanation):
{{
  "industries": ["Industry 1", "Industry 2"],
  "company_sizes": ["10-100 employees"],
  "geographies": ["United States", "California"],
  "roles_filled": [
    "Specific Role Title 1",
    "Specific Role Title 2"
  ],
  "boolean_keywords": [
    "Role Keyword 1",
    "Role Keyword 2 Variation"
  ],
  "primary_country": "United States",
  "linkedin_geo_id": "103644278"
}}"""

        # Call OpenAI
        response = self.openai_caller.call_with_retry(
            prompt=prompt,
            model="gpt-4o-mini",
            response_format="json"
        )
        
        try:
            icp_data = json.loads(response)
            
            # Log extraction
            if self.logger and self.run_id:
                self.logger.update_phase(
                    run_id=self.run_id,
                    phase="deep_icp_extracted",
                    icp_data=icp_data
                )
            
            print(f"  ✅ Deep ICP extracted:")
            print(f"    Industries: {', '.join(icp_data.get('industries', []))}")
            print(f"    Roles: {', '.join(icp_data.get('roles_filled', [])[:3])}...")
            print(f"    Geographies: {', '.join(icp_data.get('geographies', []))}")
            
            return icp_data
            
        except json.JSONDecodeError as e:
            print(f"  ❌ Error parsing ICP JSON: {e}")
            if self.logger and self.run_id:
                self.logger.update_phase(
                    run_id=self.run_id,
                    phase="deep_icp_extraction_failed"
                )
            raise Exception(f"Failed to parse ICP data: {e}")


def main():
    """Test the deep ICP extractor"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract ICP from recruiter website")
    parser.add_argument("url", help="Recruiter website URL")
    args = parser.parse_args()
    
    extractor = DeepICPExtractor()
    icp = extractor.extract_icp(args.url)
    
    print("\n" + "="*60)
    print("EXTRACTED ICP:")
    print("="*60)
    print(json.dumps(icp, indent=2))


if __name__ == "__main__":
    main()
