"""
Website Scraper
Tries HTTP → Playwright → Bright Data (in order of cost)
"""

import sys
import argparse
import time
from pathlib import Path
from typing import Optional, Tuple
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.config import TIMEOUT_HTTP, TIMEOUT_PLAYWRIGHT
from execution.supabase_logger import SupabaseLogger

class WebsiteScraper:
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id
        self.logger = SupabaseLogger() if run_id else None
    
    def scrape_http(self, url: str) -> Tuple[bool, Optional[str], str]:
        """
        Try plain HTTP request (FREE)
        Returns: (success, content, method)
        """
        try:
            print(f"🔍 Trying HTTP request for {url}...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=TIMEOUT_HTTP, headers=headers)
            response.raise_for_status()
            
            # Parse HTML and convert to Markdown
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer"]):
                script.decompose()
            
            # Get text content
            html_content = str(soup)
            markdown_content = md(html_content)
            
            if len(markdown_content) < 500:
                return False, None, "http"
            
            print(f"✅ HTTP request successful ({len(markdown_content)} characters)")
            return True, markdown_content, "http"
        
        except requests.exceptions.Timeout:
            print(f"⏱️ HTTP request timeout after {TIMEOUT_HTTP}s")
            return False, None, "http"
        except requests.exceptions.RequestException as e:
            print(f"❌ HTTP request failed: {e}")
            return False, None, "http"
    
    def scrape_playwright(self, url: str) -> Tuple[bool, Optional[str], str]:
        """
        Try Playwright (FREE, but requires installation)
        Returns: (success, content, method)
        """
        try:
            print(f"🎭 Trying Playwright for {url}...")
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=TIMEOUT_PLAYWRIGHT * 1000)
                
                # Wait for page load
                page.wait_for_load_state("networkidle", timeout=TIMEOUT_PLAYWRIGHT * 1000)
                
                # Get HTML content
                html_content = page.content()
                
                # Parse and convert to Markdown
                soup = BeautifulSoup(html_content, 'html.parser')
                for script in soup(["script", "style", "nav", "footer"]):
                    script.decompose()
                
                markdown_content = md(str(soup))
                
                browser.close()
                
                if len(markdown_content) < 500:
                    return False, None, "playwright"
                
                print(f"✅ Playwright successful ({len(markdown_content)} characters)")
                return True, markdown_content, "playwright"
        
        except ImportError:
            print("❌ Playwright not installed. Install with: pip install playwright && playwright install")
            return False, None, "playwright"
        except Exception as e:
            print(f"❌ Playwright failed: {e}")
            return False, None, "playwright"
    
    def scrape_bright_data(self, url: str) -> Tuple[bool, Optional[str], str]:
        """
        Try Bright Data Web Scraping API (PAID - Last Resort)
        Returns: (success, content, method)
        """
        print(f"💰 Trying Bright Data for {url} (PAID METHOD)...")
        print("⚠️ Bright Data integration requires MCP tool or API. Not implemented in basic script.")
        print("⚠️ This should be integrated via Bright Data's scrape_as_markdown MCP tool.")
        return False, None, "bright_data"
    
    def scrape(self, url: str, output_path: str) -> bool:
        """
        Main scraping method - tries all methods in order
        Returns: True if successful, False otherwise
        """
        start_time = time.time()
        
        # Try HTTP first (FREE)
        success, content, method = self.scrape_http(url)
        if success and content:
            elapsed = time.time() - start_time
            self._save_content(content, output_path, method, elapsed)
            return True
        
        # Try Playwright (FREE)
        success, content, method = self.scrape_playwright(url)
        if success and content:
            elapsed = time.time() - start_time
            self._save_content(content, output_path, method, elapsed)
            return True
        
        # Try Bright Data (PAID - Last Resort)
        success, content, method = self.scrape_bright_data(url)
        if success and content:
            elapsed = time.time() - start_time
            self._save_content(content, output_path, method, elapsed)
            return True
        
        print(f"❌ All scraping methods failed for {url}")
        return False
    
    def _save_content(self, content: str, output_path: str, method: str, elapsed: float):
        """Save scraped content to file"""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Saved {len(content)} characters to {output_path}")
        print(f"✅ Method: {method}, Time: {elapsed:.2f}s")

def main():
    parser = argparse.ArgumentParser(description="Scrape website content")
    parser.add_argument("--url", required=True, help="URL to scrape")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--run-id", help="Run ID for logging")
    args = parser.parse_args()
    
    scraper = WebsiteScraper(run_id=args.run_id)
    
    success = scraper.scrape(args.url, args.output)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
