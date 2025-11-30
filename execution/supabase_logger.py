"""
Supabase Logger
Real-time logging to Supabase for agent runs
"""

import os
import uuid
from datetime import datetime
from typing import Optional
from supabase import create_client, Client

class SupabaseLogger:
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        self.table_name = "agent_logs"
    
    def create_run(self, client_name: str, client_email: str, client_website: str = None, 
                   run_id: Optional[str] = None) -> str:
        """Create a new run entry in Supabase"""
        if not run_id:
            run_id = str(uuid.uuid4())
        
        data = {
            "run_id": run_id,
            "agent_name": "recruiter-job-tracker",
            "run_status": "started",
            "cost_of_run": "$0.00",
            "client_name": client_name,
            "client_email": client_email,
            "client_website": client_website,
            "job_identified_by": "LinkedIn Jobs Scraper",
            "phase": "initialization",
            "companies_found": 0,
            "companies_validated": 0,
            "final_companies_selected": 0,
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            self.supabase.table(self.table_name).insert(data).execute()
            print(f"✅ Created Supabase log entry for run {run_id}")
            return run_id
        except Exception as e:
            print(f"❌ Failed to create Supabase log: {e}")
            return run_id
    
    def update_phase(self, run_id: str, phase: str, cost_of_run: Optional[str] = None,
                     companies_found: Optional[int] = None,
                     companies_validated: Optional[int] = None,
                     final_companies_selected: Optional[int] = None,
                     icp_data: Optional[dict] = None,
                     job_posting_links: Optional[list] = None,
                     job_posting_date: Optional[str] = None,
                     exa_webset: Optional[str] = None):
        """Update the current phase and metrics"""
        update_data = {
            "phase": phase,
            "run_status": "running"
        }
        
        if cost_of_run:
            update_data["cost_of_run"] = cost_of_run
        
        if companies_found is not None:
            update_data["companies_found"] = companies_found
        
        if companies_validated is not None:
            update_data["companies_validated"] = companies_validated
        
        if final_companies_selected is not None:
            update_data["final_companies_selected"] = final_companies_selected
        
        if icp_data:
            import json
            update_data["icp"] = json.dumps(icp_data)
        
        if job_posting_links:
            update_data["job_posting_links"] = job_posting_links
        
        if job_posting_date:
            update_data["job_posting_date"] = job_posting_date
        
        if exa_webset:
            update_data["exa_webset"] = exa_webset
        
        try:
            self.supabase.table(self.table_name).update(update_data).eq("run_id", run_id).execute()
            print(f"✅ Updated Supabase: phase={phase}")
        except Exception as e:
            print(f"❌ Failed to update Supabase: {e}")
    
    def mark_completed(self, run_id: str, cost_of_run: str):
        """Mark run as completed"""
        try:
            self.supabase.table(self.table_name).update({
                "run_status": "completed",
                "phase": "completed",
                "cost_of_run": cost_of_run
            }).eq("run_id", run_id).execute()
            print(f"✅ Marked run {run_id} as completed")
        except Exception as e:
            print(f"❌ Failed to mark run as completed: {e}")
    
    def mark_failed(self, run_id: str, error_message: str, phase: str):
        """Mark run as failed"""
        try:
            self.supabase.table(self.table_name).update({
                "run_status": "failed",
                "phase": f"{phase} (failed)",
                "error_message": error_message
            }).eq("run_id", run_id).execute()
            print(f"❌ Marked run {run_id} as failed: {error_message}")
        except Exception as e:
            print(f"❌ Failed to mark run as failed: {e}")

# Example usage
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    logger = SupabaseLogger()
    
    # Create new run
    run_id = logger.create_run(
        client_name="John Doe",
        client_email="john@example.com"
    )
    
    # Update phase
    logger.update_phase(
        run_id=run_id,
        phase="scraping_recruiter_website",
        cost_of_run="$0.00 HTTP (1 request)"
    )
    
    # Mark completed
    logger.mark_completed(
        run_id=run_id,
        cost_of_run="$0.25 OpenAI (30 calls), $0.05 Apify (1 run)"
    )
