#!/usr/bin/env python3
"""
Debug script to understand Lungpacer careers page structure
"""

from playwright.sync_api import sync_playwright

def analyze_lungpacer():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Headless mode
        page = browser.new_page()
        
        print("🔍 Loading Lungpacer careers page...")
        page.goto("https://lungpacer.com/careers/", timeout=60000, wait_until="networkidle")
        
        print("\n📋 Page title:", page.title())
        
        # Get all text content
        print("\n📝 Full page text:")
        text = page.inner_text('body')
        print(text)
        
        print("\n" + "="*80)
        
        # Look for specific patterns
        print("\n🔍 Searching for 'Director of Market Access'...")
        if "Director of Market Access" in text or "director of market access" in text.lower():
            print("✅ Found job title in page text!")
            # Find the context around it
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if 'director of market access' in line.lower():
                    print(f"\nContext (5 lines before and after):")
                    start = max(0, i-5)
                    end = min(len(lines), i+6)
                    for j in range(start, end):
                        marker = ">>> " if j == i else "    "
                        print(f"{marker}{lines[j]}")
        else:
            print("❌ Job title not found in page text")
        
        # Get HTML to understand structure
        print("\n\n📄 Getting page HTML structure...")
        html = page.content()
        
        # Look for job-related divs
        if 'director of market access' in html.lower():
            print("✅ Found job title in HTML!")
            # Find the parent element
            import re
            match = re.search(r'<[^>]*director of market access[^>]*>[^<]*</[^>]*>', html, re.IGNORECASE)
            if match:
                print(f"Match: {match.group()[:200]}")
        
        browser.close()

if __name__ == "__main__":
    analyze_lungpacer()
