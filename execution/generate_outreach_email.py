"""
Outreach Email Generator
Generates personalized peer-to-peer outreach emails
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))
from execution.call_openai import OpenAICaller
from execution.supabase_logger import SupabaseLogger
from config.ai_prompts import PROMPT_GENERATE_EMAIL

class EmailGenerator:
    def __init__(self, run_id: str = None):
        self.run_id = run_id
        self.logger = SupabaseLogger() if run_id else None
        self.openai_caller = OpenAICaller(run_id=run_id)
    
    def format_company_for_email(self, company: Dict[str, Any], decision_maker: Dict[str, str] = None) -> str:
        """
        Format a single company entry for the email
        """
        company_name = company["company_name"]
        website = company.get("company_website", "")
        description = company.get("company_description", "")[:150]  # Truncate long descriptions
        
        # Get unique job titles
        job_titles = list(set([job["job_title"] for job in company.get("jobs", [])]))
        
        formatted = f"**{company_name}**"
        if website:
            formatted += f" ({website})"
        
        if description:
            formatted += f"\n{description}"
        
        if job_titles:
            formatted += f"\nHiring: {', '.join(job_titles)}"
        
        if decision_maker:
            name = decision_maker.get("name", "")
            title = decision_maker.get("title", "")
            linkedin = decision_maker.get("linkedin_url", "")
            if name:
                formatted += f"\nDecision-maker: {name}"
                if title:
                    formatted += f" ({title})"
                if linkedin:
                    formatted += f" - {linkedin}"
        
        return formatted
    
    def generate_email_content(self, companies: List[Dict[str, Any]], 
                       decision_makers: List[Dict[str, Any]],
                       recruiter_data: Dict[str, Any]) -> str:
        """
        Generate personalized outreach email
        """
        print("✉️ Generating outreach email...")
        
        # Match decision makers to companies
        dm_map = {dm["company_name"]: dm.get("decision_maker") for dm in decision_makers if dm.get("decision_maker")}
        
        # Format companies data
        companies_list = []
        for company in companies:
            dm = dm_map.get(company["company_name"])
            company_data = {
                "company_name": company["company_name"],
                "company_website": company.get("company_website", ""),
                "company_description": company.get("company_description", "")[:150],
                "roles_hiring": company.get("roles_hiring", [])  # Use 'roles_hiring' which has job_url
            }
            if dm and dm.get("name"):  # Only add if we have actual decision maker data
                company_data["decision_maker"] = {
                    "name": dm.get("name", ""),
                    "title": dm.get("title", ""),
                    "linkedin_url": dm.get("linkedin_url", "")
                }
            companies_list.append(company_data)
        
        # Use existing OpenAICaller.generate_email() method with sender info
        print("🤖 Using gpt-4-turbo-preview for premium outreach quality...")
        email = self.openai_caller.generate_email(
            recruiter_name=recruiter_data.get("client_name", "there"),
            companies_data=companies_list,
            sender_name=recruiter_data.get("email_sender_name", "Your Name"),
            sender_email=recruiter_data.get("email_sender_address", ""),
            email_thread=recruiter_data.get("email_thread"),
            recruiter_timezone=recruiter_data.get("recruiter_timezone", "GMT")
        )
        
        if not email:
            raise Exception("Failed to generate email")
        
        # Validate word count
        word_count = len(email.split())
        print(f"📝 Email generated: {word_count} words")
        
        if word_count > 300:
            print(f"⚠️ Email slightly over target (300 words), but quality is priority")
        
        return email
    
    def save_email(self, email: str, output_path: str):
        """
        Save email to file
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output, 'w') as f:
            f.write(email)
        
        print(f"✅ Saved email to {output_path}")
        
        # Update Supabase
        if self.logger and self.run_id:
            self.logger.update_phase(
                run_id=self.run_id,
                phase="email_generated",
                cost_of_run=f"${self.openai_caller.get_cost_estimate()}"
            )

def main():
    parser = argparse.ArgumentParser(description="Generate outreach email")
    parser.add_argument("--companies", required=True, help="Path to companies JSON (top_4_companies.json)")
    parser.add_argument("--decision-makers", required=True, help="Path to decision makers JSON")
    parser.add_argument("--recruiter", required=True, help="Path to recruiter info JSON (validated.json)")
    parser.add_argument("--output", required=True, help="Output path for email")
    parser.add_argument("--run-id", help="Supabase run ID")
    
    args = parser.parse_args()
    
    # Load data
    with open(args.companies, 'r') as f:
        companies = json.load(f)
    
    with open(args.decision_makers, 'r') as f:
        decision_makers = json.load(f)
    
    with open(args.recruiter, 'r') as f:
        recruiter_data = json.load(f)
    
    # Generate email
    generator = EmailGenerator(run_id=args.run_id)
    email = generator.generate_email_content(companies, decision_makers, recruiter_data)
    
    # Save
    generator.save_email(email, args.output)
    
    print(f"\n✅ Email generation complete!")

if __name__ == "__main__":
    main()
