"""
Test company grouping for email generation
"""
from config.ai_prompts import format_email_prompt

# Simulate Tim's data with VentureMed appearing 3 times
companies_data = [
    {
        "company_name": "VentureMed Group",
        "company_website": "https://www.venturemedgroup.com",
        "company_description": "VentureMed develops innovative vascular medical devices to improve patient outcomes.",
        "employee_count": 50,
        "roles_hiring": [
            {
                "job_title": "Marketing Program Manager",
                "job_url": "https://jobs.medicalalley.org/job/1915504-marketing-program-manager-venturemed",
                "posted_at": "2025-11-28"
            }
        ]
    },
    {
        "company_name": "VentureMed Group",
        "company_website": "https://www.venturemedgroup.com",
        "company_description": "VentureMed develops innovative vascular medical devices to improve patient outcomes.",
        "employee_count": 50,
        "roles_hiring": [
            {
                "job_title": "Senior Manager, Regulatory Affairs / Quality Assurance",
                "job_url": "https://jobs.medicalalley.org/j/_d1yEwF01",
                "posted_at": "2025-11-25"
            }
        ]
    },
    {
        "company_name": "VentureMed Group",
        "company_website": "https://www.venturemedgroup.com",
        "company_description": "VentureMed develops innovative vascular medical devices to improve patient outcomes.",
        "employee_count": 50,
        "roles_hiring": [
            {
                "job_title": "Quality Specialist",
                "job_url": "https://jobs.medicalalley.org/j/yPUFDvi8SY",
                "posted_at": "2025-11-27"
            }
        ]
    },
    {
        "company_name": "Certus Critical Care",
        "company_website": "https://www.certuscriticalcare.com",
        "company_description": "Certus is an early-stage MedTech company focused on critical care technology.",
        "employee_count": 20,
        "roles_hiring": [
            {
                "job_title": "Embedded Software Engineer",
                "job_url": "https://jobs.medicalalley.org/j/xyz123",
                "posted_at": "2025-11-26"
            }
        ]
    }
]

# Generate prompt
prompt = format_email_prompt(
    recruiter_name="Tim",
    companies_data=companies_data,
    sender_name="Test Sender",
    sender_email="test@example.com"
)

print("="*80)
print("GENERATED PROMPT:")
print("="*80)
print(prompt)
print("\n" + "="*80)
print("KEY OBSERVATIONS:")
print("="*80)

# Check if VentureMed appears only once
ventured_count = prompt.count("VentureMed Group")
print(f"✓ VentureMed Group appears {ventured_count} time(s) in prompt (should be 1)")

# Check if all 3 roles are listed
marketing_count = prompt.count("Marketing Program Manager")
regulatory_count = prompt.count("Senior Manager, Regulatory Affairs")
quality_count = prompt.count("Quality Specialist")
print(f"✓ Marketing Program Manager: {marketing_count} time(s)")
print(f"✓ Senior Manager, Regulatory Affairs: {regulatory_count} time(s)")
print(f"✓ Quality Specialist: {quality_count} time(s)")

# Check role count
if "Open Roles (3 total)" in prompt:
    print("✅ Correctly shows '3 total' roles for VentureMed Group")
else:
    print("❌ Does not show correct role count")

# Check Certus appears once
certus_count = prompt.count("Certus Critical Care")
print(f"✓ Certus Critical Care appears {certus_count} time(s) (should be 1)")
