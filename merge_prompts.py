# Read the NEW simplified prompts
with open('config/ai_prompts_NEW.py', 'r') as f:
    new_content = f.read()

# Read the OLD backup to get the prompts we want to keep  
with open('config/ai_prompts_OLD_BACKUP.py', 'r') as f:
    old_content = f.read()

# Extract the prompts we need from old file
import re

# Find PROMPT_VALIDATE_DIRECT_HIRER
direct_match = re.search(r'(# Phase 5: Validate Direct Hirer.*?""")', old_content, re.DOTALL)
direct_hirer = direct_match.group(1) if direct_match else ""

# Find PROMPT_VALIDATE_ICP_FIT  
icp_match = re.search(r'(# Phase 7: Validate ICP Fit.*?""")', old_content, re.DOTALL)
icp_fit = icp_match.group(1) if icp_match else ""

# Find PROMPT_DETERMINE_DECISION_MAKER
dm_match = re.search(r'(# Phase 8: Determine Decision Maker.*?""")', old_content, re.DOTALL)
decision_maker = dm_match.group(1) if dm_match else ""

# Find PROMPT_GENERATE_EMAIL
email_match = re.search(r'(# Phase 9: Generate Outreach Email.*?Generate ONLY the companies section.*?""")', old_content, re.DOTALL)
email_prompt = email_match.group(1) if email_match else ""

# Find PROMPT_GENERATE_EMAIL_NO_ROLES
email_no_roles_match = re.search(r'(# Fallback prompt when no explicit job postings.*?Generate ONLY the companies section.*?""")', old_content, re.DOTALL)
email_no_roles = email_no_roles_match.group(1) if email_no_roles_match else ""

# Find PROMPT_HUMANIZE_EMAIL
humanize_match = re.search(r'(# Phase 10: Humanize Email.*?""")', old_content, re.DOTALL)
humanize_email = humanize_match.group(1) if humanize_match else ""

# Find all the helper functions
helpers_match = re.search(r'(# Prompt helper functions.*)', old_content, re.DOTALL)
helpers = helpers_match.group(1) if helpers_match else ""

print("Extracted prompts successfully")
print(f"Direct Hirer: {len(direct_hirer)} chars")
print(f"ICP Fit: {len(icp_fit)} chars")
print(f"Decision Maker: {len(decision_maker)} chars")
print(f"Email: {len(email_prompt)} chars")
print(f"Email No Roles: {len(email_no_roles)} chars")
print(f"Humanize: {len(humanize_email)} chars")
print(f"Helpers: {len(helpers)} chars")
