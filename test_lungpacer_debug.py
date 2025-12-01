#!/usr/bin/env python3
"""
Debug script to understand Lungpacer careers page structure
"""

from playwright.sync_api import sync_playwright
import time

def analyze_lungpacer():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Non-headless to see what's happening
        page = browser.new_page()
        
        print("🔍 Loading Lungpacer careers page...")
        page.goto("https://lungpacer.com/careers/", timeout=60000, wait_until="networkidle")
        
        print("\n📋 Page title:", page.title())
        
        # Get all text content
        print("\n📝 Full page text (first 2000 chars):")
        text = page.inner_text('body')
        print(text[:2000])
        
        # Look for specific patterns
        print("\n\n🔍 Searching for 'Director of Market Access'...")
        if "Director of Market Access" in text or "director of market access" in text.lower():
            print("✅ Found job title in page text!")
        else:
            print("❌ Job title not found in page text")
        
        # Check for expandable elements
        print("\n🔘 Checking for buttons...")
        buttons = page.locator('button').all()
        print(f"Found {len(buttons)} buttons")
        for i, btn in enumerate(buttons[:10]):
            try:
                btn_text = btn.inner_text(timeout=500)
                print(f"  Button {i+1}: {btn_text[:100]}")
            except:
                pass
        
        # Check for divs with onclick
        print("\n🖱️ Checking for clickable divs...")
        clickable_divs = page.locator('div[onclick]').all()
        print(f"Found {len(clickable_divs)} clickable divs")
        
        # Check for accordions
        print("\n📂 Checking for accordion elements...")
        accordions = page.locator('.accordion, [role="button"], [aria-expanded]').all()
        print(f"Found {len(accordions)} accordion-like elements")
        for i, acc in enumerate(accordions[:5]):
            try:
                acc_text = acc.inner_text(timeout=500)
                print(f"  Element {i+1}: {acc_text[:100]}")
            except:
                pass
        
        # Check all headings
        print("\n📰 Checking all headings (h1-h6)...")
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            headings = page.locator(tag).all()
            if headings:
                print(f"\n{tag.upper()} tags ({len(headings)}):")
                for i, h in enumerate(headings[:5]):
                    try:
                        h_text = h.inner_text(timeout=500)
                        print(f"  {h_text[:100]}")
                    except:
                        pass
        
        # Wait to inspect
        print("\n\n⏸️ Browser will stay open for 10 seconds for manual inspection...")
        time.sleep(10)
        
        browser.close()

if __name__ == "__main__":
    analyze_lungpacer()
