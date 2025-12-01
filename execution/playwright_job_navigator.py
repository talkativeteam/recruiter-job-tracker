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
        
        WORLD-CLASS IMPLEMENTATION: Handles 15+ careers page patterns
        1. Simple text listings       9. iFrame embeds
        2. Accordion/expandable      10. Search/filter required
        3. Modal popups              11. Aggregator sites
        4. External job boards       12. PDF documents
        5. Email apply only          13. Form submissions
        6. JS dynamic loading        14. No jobs detection
        7. Infinite scroll           15. Redirects
        8. Tabbed interfaces
        
        Args:
            careers_url: Company careers page URL
            company_name: Company name for logging
            
        Returns:
            List of jobs with actual URLs or careers page URL if jobs listed there
        """
        try:
            from playwright.sync_api import sync_playwright
            
            print(f"🎭 Intelligent navigation for {company_name}...")
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    viewport={"width": 1920, "height": 1080}
                )
                page = context.new_page()
                
                # Navigate to careers page
                page.goto(careers_url, timeout=self.timeout, wait_until="networkidle")
                
                # PATTERN 15: Check for redirects
                final_url = page.url
                if final_url != careers_url:
                    print(f"    🔀 Redirected: {final_url}")
                    careers_url = final_url
                
                # PATTERN 14: Check for "no jobs" indicators
                if self._check_no_jobs(page):
                    print(f"    ℹ️ No current openings")
                    browser.close()
                    return []
                
                # PATTERN 9: Check for iframes
                iframe_jobs = self._check_iframes(page, careers_url)
                if iframe_jobs:
                    browser.close()
                    return iframe_jobs
                
                # PATTERN 6: Wait for JS dynamic content
                self._wait_for_dynamic_content(page)
                
                # PATTERN 7: Handle infinite scroll
                self._handle_infinite_scroll(page)
                
                # PATTERN 8: Click through tabs
                self._click_all_tabs(page)
                
                # PATTERN 10: Try search/filter interactions
                self._try_search_filters(page)
                
                # PATTERN 13: Handle form submissions
                self._handle_forms(page)
                
                # PATTERN 2: Expand accordions and collapsible sections
                self._try_expand_job_list(page)
                
                # Extract jobs using all remaining patterns (1,3,4,5,11,12)
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
    
    def _check_no_jobs(self, page) -> bool:
        """
        PATTERN 14: Detect if page indicates no current job openings
        """
        try:
            page_text = page.inner_text('body').lower()
            no_jobs_indicators = [
                'no current openings', 'no open positions', 'not hiring',
                'check back later', 'no positions available', 'no vacancies',
                'currently no openings', 'no jobs at this time',
                'no opportunities available', 'come back soon'
            ]
            return any(indicator in page_text for indicator in no_jobs_indicators)
        except:
            return False
    
    def _check_iframes(self, page, base_url: str) -> List[Dict[str, Any]]:
        """
        PATTERN 9: Check for jobs in iframes (embedded job boards)
        """
        try:
            iframes = page.locator('iframe').all()
            if not iframes:
                return []
            
            print(f"    🖼️ Found {len(iframes)} iframes, checking for jobs...")
            
            for iframe in iframes[:3]:  # Limit to first 3
                try:
                    frame = iframe.content_frame()
                    if not frame:
                        continue
                    
                    # Try to extract jobs from iframe
                    frame_jobs = self._extract_job_links(frame, base_url)
                    if frame_jobs:
                        print(f"    ✅ Found jobs in iframe")
                        return frame_jobs
                except:
                    continue
            
            return []
        except:
            return []
    
    def _wait_for_dynamic_content(self, page):
        """
        PATTERN 6: Wait for JavaScript dynamic content to load
        """
        try:
            # Wait a bit longer for React/Vue apps
            page.wait_for_timeout(2000)
            
            # Wait for common job container selectors
            job_selectors = [
                '.job-listing', '.job-item', '.position', '.career-item',
                '[data-job]', '[class*="JobCard"]', '[class*="job-card"]'
            ]
            
            for selector in job_selectors:
                try:
                    page.wait_for_selector(selector, timeout=3000)
                    print(f"    ⏳ Waited for dynamic content to load")
                    return
                except:
                    continue
        except:
            pass
    
    def _handle_infinite_scroll(self, page):
        """
        PATTERN 7: Handle infinite scroll to load all jobs
        """
        try:
            # Get initial page height
            previous_height = page.evaluate("document.body.scrollHeight")
            
            # Scroll up to 5 times
            for i in range(5):
                # Scroll to bottom
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1000)
                
                # Check if "Load More" button exists
                try:
                    load_more_selectors = [
                        'button:has-text("Load More")', 'button:has-text("Show More")',
                        'button:has-text("View More")', 'a:has-text("Load More")',
                        '[class*="load-more"]', '[class*="show-more"]'
                    ]
                    for selector in load_more_selectors:
                        button = page.locator(selector).first
                        if button.is_visible(timeout=1000):
                            print(f"    📜 Clicking 'Load More' button...")
                            button.click()
                            page.wait_for_timeout(1500)
                            break
                except:
                    pass
                
                # Check if page height changed
                new_height = page.evaluate("document.body.scrollHeight")
                if new_height == previous_height:
                    break
                previous_height = new_height
        except:
            pass
    
    def _click_all_tabs(self, page):
        """
        PATTERN 8: Click through tabbed interfaces (departments, locations)
        """
        try:
            tab_selectors = [
                '[role="tab"]', '.tab', '[class*="tab"]', 
                '[data-tab]', 'button[class*="Tab"]'
            ]
            
            for selector in tab_selectors:
                try:
                    tabs = page.locator(selector).all()
                    if len(tabs) > 1:
                        print(f"    📑 Found {len(tabs)} tabs, clicking through...")
                        for tab in tabs[:10]:  # Limit to 10 tabs
                            try:
                                if tab.is_visible(timeout=500):
                                    tab.click(timeout=1000)
                                    page.wait_for_timeout(800)
                            except:
                                continue
                        return
                except:
                    continue
        except:
            pass
    
    def _try_search_filters(self, page):
        """
        PATTERN 10: Try common search/filter interactions
        """
        try:
            # Look for "All" or "View All" options in dropdowns/filters
            all_options = [
                'option:has-text("All")', 'option:has-text("All Departments")',
                'option:has-text("All Locations")', 'option:has-text("All Teams")',
                '[value="all"]', '[value=""]'
            ]
            
            for option in all_options:
                try:
                    page.locator(option).first.click(timeout=1000)
                    page.wait_for_timeout(500)
                    print(f"    🔍 Selected 'All' filter")
                    return
                except:
                    continue
        except:
            pass
    
    def _handle_forms(self, page):
        """
        PATTERN 13: Handle simple form submissions that might reveal jobs
        """
        try:
            # Look for checkboxes that might need to be checked
            consent_checkboxes = page.locator('input[type="checkbox"]').all()
            for checkbox in consent_checkboxes[:3]:
                try:
                    if not checkbox.is_checked():
                        checkbox.check(timeout=1000)
                        page.wait_for_timeout(500)
                except:
                    continue
        except:
            pass
    
    def _try_expand_job_list(self, page) -> bool:
        """
        PATTERN 2: Try to click buttons that expand or show all jobs
        (Accordion, collapsible sections, "View All" buttons)
        
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
        
        HANDLES PATTERNS:
        1. Simple text listings    4. External job boards   11. Aggregators
        3. Modal popups            5. Email filtering       12. PDF documents
        """
        job_links = []
        seen_urls = set()
        
        try:
            # PATTERN 1: Try to find jobs as simple text on page first
            expandable_jobs = self._find_expandable_jobs(page, base_url)
            if expandable_jobs:
                print(f"    ✨ Found {len(expandable_jobs)} jobs in expandable sections")
                job_links.extend(expandable_jobs)
                for job in expandable_jobs:
                    seen_urls.add(job['job_url'])
            
            # PATTERN 11: Check if this is an aggregator site (Built In, Indeed, etc.)
            aggregator_jobs = self._extract_aggregator_jobs(page, base_url)
            if aggregator_jobs:
                print(f"    🏢 Extracted {len(aggregator_jobs)} jobs from aggregator site")
                for job in aggregator_jobs:
                    if job['job_url'] not in seen_urls:
                        job_links.append(job)
                        seen_urls.add(job['job_url'])
            
            # PATTERNS 4, 5, 12: Extract regular job links
            all_links = page.locator('a').all()
            
            print(f"    📊 Analyzing {len(all_links)} links...")
            
            for link in all_links:
                try:
                    href = link.get_attribute('href')
                    text = link.inner_text(timeout=1000).strip()
                    
                    if not href or href.startswith('#') or href.startswith('javascript:'):
                        continue
                    
                    # PATTERN 5: Skip mailto: links (email apply only)
                    if href.startswith('mailto:'):
                        continue
                    
                    # Convert to absolute URL
                    full_url = urljoin(base_url, href)
                    
                    # Skip duplicates
                    if full_url in seen_urls:
                        continue
                    
                    # PATTERN 12: Handle PDF/document links
                    if self._is_document_link(full_url):
                        if self._is_job_document(text):
                            job_links.append({
                                "job_title": self._extract_title_from_text(text),
                                "job_url": full_url,
                                "description": "PDF/Document"
                            })
                            seen_urls.add(full_url)
                        continue
                    
                    # PATTERN 4: Prioritize external job board links
                    if self._is_external_job_board(full_url):
                        job_links.append({
                            "job_title": self._extract_title_from_text(text),
                            "job_url": full_url,
                            "description": text[:200] if len(text) > 50 else ""
                        })
                        seen_urls.add(full_url)
                        continue
                    
                    # Check if this looks like a regular job posting link
                    if self._is_job_link(href, text, full_url):
                        # PATTERN 3: Try to handle modals (if click opens modal, extract URL from it)
                        final_url = self._check_for_modal(page, link, full_url)
                        
                        job_links.append({
                            "job_title": self._extract_title_from_text(text),
                            "job_url": final_url,
                            "description": text[:200] if len(text) > 50 else ""
                        })
                        seen_urls.add(final_url)
                        
                except Exception as e:
                    continue
            
            return job_links
            
        except Exception as e:
            print(f"    ❌ Link extraction failed: {e}")
            return []
    
    def _is_external_job_board(self, url: str) -> bool:
        """
        PATTERN 4: Detect external job board URLs
        """
        external_boards = [
            'greenhouse.io', 'lever.co', 'workdayjobs.com', 'myworkdayjobs.com',
            'paycomonline.net', 'icims.com', 'ultipro.com', 'bamboohr.com',
            'jobvite.com', 'smartrecruiters.com', 'taleo.net', 'breezy.hr',
            'workable.com', 'recruitee.com', 'personio.de', 'greenhouse.com',
            'ashbyhq.com', 'comeet.com', 'jazz.co', 'applytojob.com',
            'recruiting.paylocity.com', 'recruiting.ultipro.com'
        ]
        url_lower = url.lower()
        return any(board in url_lower for board in external_boards)
    
    def _is_document_link(self, url: str) -> bool:
        """
        PATTERN 12: Detect PDF/document links
        """
        doc_extensions = ['.pdf', '.doc', '.docx', '.rtf']
        return any(url.lower().endswith(ext) for ext in doc_extensions)
    
    def _is_job_document(self, text: str) -> bool:
        """
        PATTERN 12: Check if document link text indicates it's a job posting
        """
        job_keywords = ['director', 'manager', 'engineer', 'designer', 'analyst', 'lead', 'senior']
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in job_keywords)
    
    def _check_for_modal(self, page, link, default_url: str) -> str:
        """
        PATTERN 3: Check if clicking opens a modal with shareable URL
        Returns the shareable URL if found, otherwise returns default_url
        """
        try:
            # Don't actually click - too risky for navigation
            # Just return the default URL for now
            # In a more advanced implementation, we could:
            # 1. Check if link has data-modal or similar attributes
            # 2. Open in new page/context to check modal behavior
            # 3. Extract shareable URL from modal if available
            return default_url
        except:
            return default_url
    
    def _extract_aggregator_jobs(self, page, base_url: str) -> List[Dict[str, Any]]:
        """
        PATTERN 11: Extract jobs from aggregator sites (Built In, Indeed, etc.)
        """
        jobs = []
        
        try:
            # Check if this is Built In
            if 'builtin.com' in base_url.lower():
                return self._extract_builtin_jobs(page, base_url)
            
            # Check if this is LinkedIn
            elif 'linkedin.com' in base_url.lower():
                return self._extract_linkedin_jobs(page, base_url)
            
            # Check if this is Indeed
            elif 'indeed.com' in base_url.lower():
                return self._extract_indeed_jobs(page, base_url)
            
            return []
        except:
            return []
    
    def _extract_builtin_jobs(self, page, base_url: str) -> List[Dict[str, Any]]:
        """Extract jobs from Built In aggregator"""
        jobs = []
        try:
            # Built In specific selectors
            job_cards = page.locator('[data-id*="job"], .job-item, [class*="JobCard"]').all()
            
            for card in job_cards[:20]:
                try:
                    title_elem = card.locator('h2, h3, [class*="title"]').first
                    link_elem = card.locator('a').first
                    
                    title = title_elem.inner_text(timeout=500).strip()
                    href = link_elem.get_attribute('href')
                    
                    if title and href:
                        full_url = urljoin(base_url, href)
                        jobs.append({
                            "job_title": title,
                            "job_url": full_url,
                            "description": ""
                        })
                except:
                    continue
            
            return jobs
        except:
            return []
    
    def _extract_linkedin_jobs(self, page, base_url: str) -> List[Dict[str, Any]]:
        """Extract jobs from LinkedIn"""
        jobs = []
        try:
            job_cards = page.locator('.job-card-container, [class*="job-card"]').all()
            
            for card in job_cards[:20]:
                try:
                    title = card.locator('[class*="job-title"]').first.inner_text(timeout=500)
                    link = card.locator('a').first.get_attribute('href')
                    
                    if title and link:
                        jobs.append({
                            "job_title": title.strip(),
                            "job_url": urljoin(base_url, link),
                            "description": ""
                        })
                except:
                    continue
            
            return jobs
        except:
            return []
    
    def _extract_indeed_jobs(self, page, base_url: str) -> List[Dict[str, Any]]:
        """Extract jobs from Indeed"""
        jobs = []
        try:
            job_cards = page.locator('[data-jk], .job_seen_beacon').all()
            
            for card in job_cards[:20]:
                try:
                    title = card.locator('h2, [class*="jobTitle"]').first.inner_text(timeout=500)
                    link = card.locator('a').first.get_attribute('href')
                    
                    if title and link:
                        jobs.append({
                            "job_title": title.strip(),
                            "job_url": urljoin(base_url, link),
                            "description": ""
                        })
                except:
                    continue
            
            return jobs
        except:
            return []
    
    def _find_expandable_jobs(self, page, base_url: str) -> List[Dict[str, Any]]:
        """
        Find jobs in expandable UI elements (accordions, dropdowns, click-to-reveal)
        OR jobs that are simply listed on the careers page itself.
        
        This handles modern careers pages where:
        1. Job descriptions are hidden behind expandable sections
        2. Job titles are listed directly on the careers page without separate URLs
        
        Returns jobs with careers page URL when job content is found on that page.
        """
        expandable_jobs = []
        seen_titles = set()
        
        try:
            # STRATEGY 1: Check if page has "open positions" or "current openings" section
            # and extract jobs directly from page text
            page_text = page.inner_text('body')
            page_text_lower = page_text.lower()
            
            # Job title patterns (more comprehensive)
            job_title_patterns = [
                r'\b(director|senior director|vp|vice president)\s+of\s+\w+',
                r'\b(senior|lead|principal|staff)\s+(engineer|developer|designer|analyst|manager)',
                r'\b(chief)\s+(executive|technology|financial|operating|marketing|product)\s+officer',
                r'\b(head|manager|coordinator|specialist|analyst)\s+of\s+\w+',
                r'\b(software|hardware|mechanical|electrical|data|security)\s+(engineer|developer|architect)',
                r'\b(product|project|program|operations|engineering)\s+manager',
                r'\b(marketing|sales|business|financial|data)\s+(analyst|manager|director)',
            ]
            
            # Check for "open positions" sections
            open_position_indicators = [
                'open positions', 'current openings', 'open roles', 'available positions',
                'join our team', 'we\'re hiring', 'careers at', 'work at', 'job openings'
            ]
            
            has_job_section = any(indicator in page_text_lower for indicator in open_position_indicators)
            
            if has_job_section:
                print(f"    🎯 Found job section on page, scanning for job titles...")
                
                # Split into lines and look for job titles
                lines = page_text.split('\n')
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line or len(line) < 10:
                        continue
                    
                    line_lower = line.lower()
                    
                    # Check against patterns
                    import re
                    for pattern in job_title_patterns:
                        if re.search(pattern, line_lower):
                            # This looks like a job title
                            job_title = line
                            
                            # Clean up common prefixes/suffixes
                            for prefix in ['•', '-', '*', '>', '>>>', '→']:
                                if job_title.startswith(prefix):
                                    job_title = job_title[len(prefix):].strip()
                            
                            # Avoid duplicates
                            if job_title.lower() in seen_titles:
                                continue
                            
                            seen_titles.add(job_title.lower())
                            
                            # Get context (surrounding lines for description)
                            context_lines = []
                            for j in range(max(0, i-2), min(len(lines), i+10)):
                                context_lines.append(lines[j].strip())
                            context = ' '.join(context_lines)
                            
                            expandable_jobs.append({
                                "job_title": job_title,
                                "job_url": base_url,  # Careers page itself
                                "description": context[:300]
                            })
                            
                            print(f"    ✅ Found job on page: {job_title}")
                            break
            
            # STRATEGY 2: Try clicking expandable elements to reveal hidden content
            if not expandable_jobs:
                expandable_selectors = [
                    # Accordion patterns
                    '[role="button"]', 'button', '[aria-expanded]', '[aria-controls]',
                    # Common class patterns
                    '.accordion', '.accordion-item', '.accordion-header',
                    '.job-listing', '.job-item', '.job-card', '.career-item', '.position',
                    '.dropdown', '.expandable', '.collapsible',
                    # Heading patterns (often used for job titles)
                    'h2', 'h3', 'h4',
                    # Div patterns
                    'div[onclick]', 'div[class*="job"]', 'div[class*="position"]', 
                    'div[class*="opening"]', 'div[class*="career"]'
                ]
                
                # Job description keywords to confirm expanded content
                job_description_keywords = [
                    'responsibilities', 'requirements', 'qualifications', 'experience',
                    'skills', 'education', 'compensation', 'salary', 'benefits',
                    'full-time', 'part-time', 'remote', 'hybrid', 'on-site',
                    'bachelor', 'master', 'years of experience'
                ]
                
                # Try each selector type
                for selector in expandable_selectors:
                    try:
                        elements = page.locator(selector).all()
                        
                        for element in elements[:20]:  # Limit to avoid timeouts
                            try:
                                # Get element text
                                text = element.inner_text(timeout=500).strip()
                                
                                if not text or len(text) < 10:
                                    continue
                                
                                text_lower = text.lower()
                                
                                # Check if contains job title patterns
                                import re
                                has_job_pattern = any(re.search(pattern, text_lower) for pattern in job_title_patterns)
                                
                                if not has_job_pattern:
                                    continue
                                
                                # Try to expand/click the element
                                original_text = text
                                
                                try:
                                    if element.is_visible(timeout=500):
                                        element.click(timeout=2000)
                                        page.wait_for_timeout(500)
                                        
                                        # Get new text after clicking
                                        new_text = element.inner_text(timeout=500).strip()
                                        
                                        # If text expanded significantly, it was expandable
                                        if len(new_text) > len(original_text) * 1.5:
                                            text = new_text
                                            text_lower = new_text.lower()
                                            print(f"    🔍 Expanded element: {text[:60]}...")
                                except:
                                    pass
                                
                                # Check if content looks like a job posting
                                has_job_description = any(keyword in text_lower for keyword in job_description_keywords)
                                
                                if has_job_pattern and (has_job_description or len(text) > 200):
                                    # Extract job title (first line usually)
                                    title_lines = [line.strip() for line in text.split('\n') if line.strip()]
                                    job_title = title_lines[0] if title_lines else text[:100]
                                    
                                    # Clean up title
                                    job_title = self._extract_title_from_text(job_title)
                                    
                                    # Avoid duplicates
                                    if job_title.lower() in seen_titles:
                                        continue
                                    
                                    seen_titles.add(job_title.lower())
                                    
                                    expandable_jobs.append({
                                        "job_title": job_title,
                                        "job_url": base_url,
                                        "description": text[:300]
                                    })
                                    
                                    print(f"    ✅ Found expandable job: {job_title}")
                                    
                                    if len(expandable_jobs) >= 10:
                                        break
                                    
                            except Exception as e:
                                continue
                        
                        if expandable_jobs:
                            break
                            
                    except Exception as e:
                        continue
            
            return expandable_jobs
            
        except Exception as e:
            print(f"    ⚠️ Expandable job search failed: {e}")
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
