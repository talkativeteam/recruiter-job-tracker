#!/usr/bin/env python3
"""
Analyze different careers page patterns to build world-class Playwright detection.

This script tests various real-world scenarios we encounter:
1. Simple job listings (text on page, no links)
2. Accordion/expandable sections
3. Modal popups on click
4. External job boards (Greenhouse, Lever, Workday, etc.)
5. "Apply via email" patterns
6. JavaScript-heavy dynamic loading
7. Infinite scroll job lists
8. Tabbed interfaces (departments, locations)
9. iFrame embedded job boards
10. Search/filter required to see jobs
"""

CAREERS_PAGE_PATTERNS = {
    # PATTERN 1: Simple text listing (Lungpacer style)
    "simple_text": {
        "examples": [
            "https://lungpacer.com/careers/",
            "Small company sites with just job titles listed"
        ],
        "detection": "Job titles in plain text under 'Open Positions' section",
        "strategy": "Extract job titles from page text using regex patterns",
        "return_url": "Careers page URL itself"
    },
    
    # PATTERN 2: Accordion/collapsible sections
    "accordion": {
        "examples": [
            "Sites with expandable job descriptions",
            "Click to reveal more details"
        ],
        "detection": "[aria-expanded], .accordion, role='button'",
        "strategy": "Click each accordion item, extract expanded content",
        "return_url": "Careers page URL + #job-id anchor if available"
    },
    
    # PATTERN 3: Modal/popup on click
    "modal_popup": {
        "examples": [
            "Job title is a button that opens modal with description"
        ],
        "detection": "Clicking triggers modal/overlay",
        "strategy": "Click job title, wait for modal, extract content from modal",
        "return_url": "Careers page URL or deep link if modal has shareable URL"
    },
    
    # PATTERN 4: External job boards (most common)
    "external_board": {
        "examples": [
            "greenhouse.io",
            "lever.co",
            "workdayjobs.com",
            "myworkdayjobs.com",
            "paycomonline.net",
            "icims.com",
            "ultipro.com",
            "bamboohr.com",
            "jobvite.com",
            "smartrecruiters.com",
            "taleo.net"
        ],
        "detection": "Links point to external domain",
        "strategy": "Extract all links pointing to job board domains",
        "return_url": "Full external URL to specific job posting"
    },
    
    # PATTERN 5: Apply via email (no separate URLs)
    "email_apply": {
        "examples": [
            "mailto: links",
            "Send resume to jobs@company.com"
        ],
        "detection": "mailto: links or 'email your resume' text",
        "strategy": "Extract job titles from page, return careers URL",
        "return_url": "Careers page URL (not mailto:)"
    },
    
    # PATTERN 6: JavaScript dynamic loading
    "js_dynamic": {
        "examples": [
            "Jobs load after page initialization",
            "React/Vue apps with client-side rendering"
        ],
        "detection": "Page content changes after wait",
        "strategy": "Wait for network idle, wait for job elements to appear",
        "return_url": "Depends on whether jobs have individual URLs"
    },
    
    # PATTERN 7: Infinite scroll
    "infinite_scroll": {
        "examples": [
            "Jobs load as you scroll down",
            "Load more button"
        ],
        "detection": "More jobs appear after scroll",
        "strategy": "Scroll to bottom multiple times, click 'Load more' if present",
        "return_url": "Individual job URLs or careers page"
    },
    
    # PATTERN 8: Tabbed interface
    "tabbed": {
        "examples": [
            "Departments: Engineering | Sales | Marketing",
            "Locations: NYC | SF | Remote"
        ],
        "detection": "Tab elements, multiple job containers",
        "strategy": "Click each tab, extract jobs from each section",
        "return_url": "Individual job URLs with tab/filter in URL"
    },
    
    # PATTERN 9: iFrame embedded
    "iframe": {
        "examples": [
            "Job board in iframe",
            "Third-party widget"
        ],
        "detection": "iframe element present",
        "strategy": "Switch to iframe context, extract jobs from there",
        "return_url": "iframe src URL or parent URL"
    },
    
    # PATTERN 10: Search/filter required
    "search_required": {
        "examples": [
            "Must select department to see jobs",
            "Search box is mandatory"
        ],
        "detection": "Empty job list, search/filter inputs present",
        "strategy": "Try common searches, select 'All' options",
        "return_url": "Filtered URL or individual job URLs"
    },
    
    # PATTERN 11: Job board aggregators (Built In, Indeed, LinkedIn)
    "aggregator": {
        "examples": [
            "builtin.com/companies/*/jobs",
            "indeed.com",
            "linkedin.com/jobs"
        ],
        "detection": "URL contains known aggregator domain",
        "strategy": "Extract all job cards with specific selectors for that platform",
        "return_url": "Aggregator's job URL (not company site)"
    },
    
    # PATTERN 12: PDF/document listings
    "document_listing": {
        "examples": [
            "Links to PDF job descriptions",
            "Download JD button"
        ],
        "detection": "Links end in .pdf, .doc, .docx",
        "strategy": "Extract job titles from link text, return PDF URLs",
        "return_url": "Direct link to PDF document"
    },
    
    # PATTERN 13: Form submission required
    "form_required": {
        "examples": [
            "Select 'Job Type' dropdown to reveal listings",
            "Must check 'I agree to terms' before jobs appear"
        ],
        "detection": "Form elements blocking content",
        "strategy": "Fill out minimal form fields, submit",
        "return_url": "Post-submission URL"
    },
    
    # PATTERN 14: No jobs currently
    "no_jobs": {
        "examples": [
            "We're not hiring right now",
            "Check back later",
            "No open positions"
        ],
        "detection": "Keywords: 'no current openings', 'not hiring', 'check back'",
        "strategy": "Return empty list",
        "return_url": None
    },
    
    # PATTERN 15: Redirect to LinkedIn/external
    "redirect": {
        "examples": [
            "Careers page redirects to LinkedIn Jobs",
            "See our jobs on Indeed"
        ],
        "detection": "Page redirects to different domain",
        "strategy": "Follow redirect, apply appropriate pattern for destination",
        "return_url": "Final destination URL"
    }
}

def print_pattern_summary():
    """Print comprehensive pattern analysis"""
    print("=" * 100)
    print("CAREERS PAGE PATTERNS - COMPREHENSIVE ANALYSIS")
    print("=" * 100)
    
    for i, (pattern_id, details) in enumerate(CAREERS_PAGE_PATTERNS.items(), 1):
        print(f"\n{i}. {pattern_id.upper().replace('_', ' ')}")
        print(f"   Examples: {details['examples']}")
        print(f"   Detection: {details['detection']}")
        print(f"   Strategy: {details['strategy']}")
        print(f"   Return URL: {details['return_url']}")
        print("-" * 100)

if __name__ == "__main__":
    print_pattern_summary()
    print(f"\n\nTotal patterns identified: {len(CAREERS_PAGE_PATTERNS)}")
    print("\nThese patterns will be implemented in the world-class Playwright navigator.")
