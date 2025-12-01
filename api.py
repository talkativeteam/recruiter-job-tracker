"""
Flask API Server
Main entry point for HTTP requests
"""

import os
import json
import uuid
import requests
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from execution.orchestrator import Orchestrator
from execution.supabase_logger import SupabaseLogger
from config.config import TMP_DIR

app = Flask(__name__)

# Configuration
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://n8n.srv1125040.hstgr.cloud/webhook/2")
PORT = int(os.getenv("PORT", 5000))

def send_to_webhook(data: dict):
    """Send results to webhook"""
    try:
        response = requests.post(WEBHOOK_URL, json=data, timeout=30)
        print(f"✅ Webhook sent successfully (status: {response.status_code})")
        return True
    except Exception as e:
        print(f"❌ Webhook failed: {e}")
        return False

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route("/process", methods=["POST"])
def process_job():
    """
    Main processing endpoint
    Accepts JSON input and starts the recruitment pipeline
    """
    try:
        # Get input
        input_data = request.get_json()
        if not input_data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Generate run ID
        run_id = str(uuid.uuid4())
        print(f"\n🚀 Starting run: {run_id}")
        print(f"📋 Input: {json.dumps(input_data, indent=2)}")
        
        # Initialize orchestrator
        orchestrator = Orchestrator(run_id=run_id)
        
        # Run the full pipeline
        print(f"\n⏱️ Pipeline starting...")
        start_time = datetime.utcnow()
        
        result = orchestrator.run_full_pipeline(input_data)
        
        end_time = datetime.utcnow()
        runtime_seconds = (end_time - start_time).total_seconds()
        
        # Build webhook payload
        webhook_payload = {
            "run_metadata": {
                "run_id": run_id,
                "run_status": result.get("status", "completed"),
                "timestamp": end_time.isoformat() + "Z",
                "total_runtime_seconds": int(runtime_seconds),
                "cost_of_run": result.get("cost_estimate", "$0.00"),
            },
            "input": {
                "client_name": input_data.get("client_name"),
                "client_email": input_data.get("client_email"),
                "client_website": input_data.get("client_website"),
                "email_sender_name": input_data.get("email_sender_name"),
                "email_sender_address": input_data.get("email_sender_address"),
                "max_jobs_to_scrape": input_data.get("max_jobs_to_scrape", 100),
                "recruiter_timezone": input_data.get("recruiter_timezone", "GMT"),
            },
            "recruiter_icp": result.get("recruiter_icp"),
            "stats": result.get("stats"),
            "verified_companies": result.get("verified_companies"),
            "outreach_email": {
                "subject": f"Re: {input_data.get('email_subject', 'Recruitment Opportunities')}",
                "from": f"{input_data.get('email_sender_name')} <{input_data.get('email_sender_address')}>",
                "to": f"{input_data.get('client_name')} <{input_data.get('client_email')}>",
                "body": result.get("outreach_email", ""),
            }
        }
        
        # Send to webhook
        webhook_sent = send_to_webhook(webhook_payload)
        
        # Prepare response
        response = {
            "status": "success",
            "run_id": run_id,
            "runtime_seconds": int(runtime_seconds),
            "webhook_sent": webhook_sent,
            "data": webhook_payload if not webhook_sent else None,
        }
        
        print(f"\n✅ Run completed in {runtime_seconds:.1f}s")
        return jsonify(response), 200
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def root():
    """Root endpoint"""
    return jsonify({
        "name": "Recruiter Job Tracker",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "process": "POST /process",
        }
    }), 200

if __name__ == "__main__":
    print(f"🚀 Starting API server on port {PORT}")
    print(f"📡 Webhook URL: {WEBHOOK_URL}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
