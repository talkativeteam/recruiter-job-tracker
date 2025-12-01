"""
Intelligent Playwright Job Navigator
Finds actual job posting URLs from career pages using smart navigation
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import time

sys.path.append(str(Path(__file__).parent.parent))
from config.config import TIMEOUT_PLAYWRIGHT


class PlaywrightJobNavigator:
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id
        self.max_depth = 2  # Maximum clicks from careers page
        self.timeout = TIMEOUT_PLAYWRIGHT * 1000
    
    def find_job_urls(self, careers_url: str, company_name: str) -> List[Dict[str, Any]]:
        """
        Navigate careers page to find actual job posting URLs
        
        Args:
            careers_url: Company careers page URL
            company_name: Company name for logging
            
        Returns:
            List of jobs with actual URLs:
            [
                {
                    "job_title": "Senior Engineer",
                    "job_url": "https://company.com/jobs/123",
                    "description": "Brief text from link"
                }
            ]
        """
        try:
            from playwright.sync_api import sync_playwright
            
            print(f"🎭 Intelligent navigation for {company_name}...")
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                # Navigate to careers page
                page.goto(careers_url, timeout=self.timeout, wait_until="networkidle")
                
                # Try to find and click "View all jobs" or similar buttons
                expanded_view = self._try_expand_job_list(page)
                
                # Extract job links from current page
                job_links = self._extract_job_links(page, careers_url)
                
                browser.close()
                
                if len(job_links) > 0:
                    print(f"  ✅ Found {len(job_links)} job URLs via Playwright navigation")
                    return job_links
                else:
                    print(f"  ⚠️ No job URLs found via navigation")
                    return []
                
        except ImportError:
            print(f"  ❌ Playwright not installed")
            return []
        except Exception as e:
            print(f"  ❌ Playwright navigation failed: {e}")
            return []
    
    def _try_expand_job_list(self, page) -> bool:
        """
        Try to click buttons that expand or show all jobs
        
        Returns: True if successfully expanded, False otherwise
        """
        # Common button texts that show more jobs
        expand_keywords = [
            "view all",
            "see all",
            "show all",
            "all openings",
            "all positions",
            "open positions",
            "open roles",
            "current openings",
            "view openings",
            "see openings",
            "load more",
            "show more"
        ]
        
        try:
            # Look for buttons/links with these keywords
            for keyword in expand_keywords:
                try:
                    # Try to find and click the button (case-insensitive)
                    button = page.locator(f"button:has-text('{keyword}')").first
                    if button.is_visible(timeout=2000):
                        print(f"    🔘 Clicking '{keyword}' button...")
                        button.click(timeout=5000)
                        page.wait_for_load_state("networkidle", timeout=10000)
                        return True
                except:
                    pass
                
                try:
                    # Try link version
                    link = page.locator(f"a:has-text('{keyword}')").first
                    if link.is_visible(timeout=2000):
                        print(f"    🔗 Clicking '{keyword}' link...")
                        link.click(timeout=5000)
                        page.wait_for_load_state("networkidle", timeout=10000)
                        return True
                except:
                    pass
            
            return False
            
        except Exception as e:
            print(f"    ⚠️ Expand attempt failed: {e}")
            return False
    
    def _extract_job_links(self, page, base_url: str) -> List[Dict[str, Any]]:
        """
        Extract all job posting links from current page
        
        Looks for:
        - Links containing job keywords in href or text
        - Links pointing to common job URL patterns
        - Links in job listing containers
        """
        job_links = []
        seen_urls = set()
        
        try:
            # Get all links on the page
            all_links = page.locator('a').all()
            
            print(f"    📊 Analyzing {len(all_links)} links...")
            
            for link in all_links:
                try:
                    href = link.get_attribute('href')
                    text = link.inner_text(timeout=1000).strip()
                    
                    if not href or href.startswith('#') or href.startswith('javascript:'):
                        continue
                    
                    # Convert to absolute URL
                    full_url = urljoin(base_url, href)
                    
                    # Skip duplicates
                    if full_url in seen_urls:
                        continue
                    
                    # Check if this looks like a job posting link
                    if self._is_job_link(href, text, full_url):
                        job_links.append({
                            "job_title": self._extract_title_from_text(text),
                            "job_url": full_url,
                            "description": text[:200] if len(text) > 50 else ""
                        })
                        seen_urls.add(full_url)
                        
                except Exception as e:
                    continue
            
            return job_links
            
        except Exception as e:
            print(f"    ❌ Link extraction failed: {e}")
            return []
    
    def _is_job_link(self, href: str, text: str, full_url: str) -> bool:
        """
        Determine if a link is likely a job posting
        
        Checks:
        1. URL pattern (contains /jobs/, /careers/, /positions/, etc.)
        2. Link text contains job-like keywords
        3. URL has an ID or slug suggesting individual posting
        """
        href_lower = href.lower()
        text_lower = text.lower()
        
        # Common job URL patterns
        job_url_patterns = [
            '/job/', '/jobs/', '/career/', '/careers/', '/position/', '/positions/',
            '/opening/', '/openings/', '/vacancy/', '/vacancies/', '/role/', '/roles/',
            '/opportunity/', '/opportunities/', '/hiring/', '/apply/'
        ]
        
        # Check if URL contains job pattern
        has_job_pattern = any(pattern in href_lower for pattern in job_url_patterns)
        
        # Check if URL has an ID or unique identifier (suggests individual posting)
        has_identifier = any(char.isdigit() for char in href.split('/')[-1]) or len(href.split('/')[-1]) > 10
        
        # Job title keywords in link text
        job_keywords = [
            'engineer', 'developer', 'manager', 'director', 'analyst', 'specialist',
            'coordinator', 'lead', 'senior', 'junior', 'associate', 'head of',
            'designer', 'architect', 'consultant', 'representative', 'executive',
            'scientist', 'researcher', 'technician', 'administrator', 'officer'
        ]
        
        has_job_keyword = any(keyword in text_lower for keyword in job_keywords)
        
        # Exclude navigation/category links
        exclude_keywords = [
            'home', 'about', 'contact', 'blog', 'news', 'all jobs', 'view all',
            'search', 'filter', 'category', 'department', 'location', 'apply now',
            'learn more', 'read more', 'sign up', 'register', 'login', 'logout'
        ]
        
        is_excluded = any(keyword in text_lower for keyword in exclude_keywords if len(text) < 50)
        
        # Link is likely a job if:
        # - Has job URL pattern AND has identifier
        # - OR has job keyword in text AND not excluded
        if has_job_pattern and has_identifier:
            return True
        
        if has_job_keyword and not is_excluded and len(text) > 10:
            return True
        
        return False
    
    def _extract_title_from_text(self, text: str) -> str:
        """
        Clean up link text to extract job title
        
        Removes common prefixes/suffixes like "Apply for", "View job:", etc.
        """
        # Remove common prefixes
        prefixes_to_remove = [
            'apply for', 'apply to', 'apply:', 'view', 'see', 'learn more about',
            'read more:', 'open position:', 'job:', 'role:', 'position:'
        ]
        
        title = text.strip()
        title_lower = title.lower()
        
        for prefix in prefixes_to_remove:
            if title_lower.startswith(prefix):
                title = title[len(prefix):].strip()
                break
        
        # Remove common suffixes
        suffixes_to_remove = [' - apply', ' - view', ' - learn more', ' - read more']
        for suffix in suffixes_to_remove:
            if title_lower.endswith(suffix):
                title = title[:-len(suffix)].strip()
                break
        
        # Capitalize if all lowercase or all uppercase
        if title.islower() or title.isupper():
            title = title.title()
        
        return title


def main():
    """Test the navigator"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Playwright job navigation")
    parser.add_argument("url", help="Careers page URL to test")
    parser.add_argument("--company", default="Test Company", help="Company name")
    args = parser.parse_args()
    
    navigator = PlaywrightJobNavigator()
    jobs = navigator.find_job_urls(args.url, args.company)
    
    print(f"\n{'='*60}")
    print(f"Found {len(jobs)} job URLs:")
    print(f"{'='*60}")
    
    for i, job in enumerate(jobs, 1):
        print(f"\n{i}. {job['job_title']}")
        print(f"   URL: {job['job_url']}")
        if job.get('description'):
            print(f"   Description: {job['description'][:100]}...")


if __name__ == "__main__":
    main()
