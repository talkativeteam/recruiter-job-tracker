"""
Input Validation
Validates JSON input schema and saves validated data
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any
from urllib.parse import urlparse

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.config import TMP_DIR
from execution.supabase_logger import SupabaseLogger

class InputValidator:
    def __init__(self):
        self.required_fields = ["client_name", "client_email", "client_website", "max_jobs_to_scrape"]
        self.optional_fields = ["email_sender_name", "email_sender_address", "callback_webhook_url", "email_thread", "recruiter_timezone", "linkedin_plus_exa"]
    
    def normalize_url(self, url: str) -> str:
        """Add https:// if URL missing scheme"""
        url = url.strip()
        if not url.startswith(("http://", "https://", "ftp://")):
            url = "https://" + url
        return url
    
    def validate_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            url = self.normalize_url(url)
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def validate_email(self, email: str) -> bool:
        """Basic email validation"""
        return "@" in email and "." in email.split("@")[1]
    
    def validate_input(self, input_data: Dict[str, Any]) -> tuple[bool, str, Dict[str, Any]]:
        """
        Validate input JSON
        Returns: (is_valid, error_message, validated_data)
        """
        # Check required fields
        missing_fields = [field for field in self.required_fields if field not in input_data]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}", {}
        
        # Validate client_email
        if not self.validate_email(input_data["client_email"]):
            return False, f"Invalid email format: {input_data['client_email']}", {}
        
        # Validate email_sender_address (optional)
        email_sender_address = input_data.get("email_sender_address", "")
        if email_sender_address and not self.validate_email(email_sender_address):
            return False, f"Invalid sender email format: {email_sender_address}", {}
        
        # Validate client_website
        if not self.validate_url(input_data["client_website"]):
            return False, f"Invalid URL format: {input_data['client_website']}", {}
        
        # Validate max_jobs_to_scrape (if provided)
        max_jobs = input_data.get("max_jobs_to_scrape", 150)
        # Convert string to int if needed
        if isinstance(max_jobs, str):
            try:
                max_jobs = int(max_jobs)
            except ValueError:
                return False, f"max_jobs_to_scrape must be a number, got: {max_jobs}", {}
        
        if not isinstance(max_jobs, int) or max_jobs < 100 or max_jobs > 400:
            return False, f"max_jobs_to_scrape must be between 100 and 400, got: {max_jobs}", {}
        
        # Validate callback_webhook_url (if provided)
        callback_url = input_data.get("callback_webhook_url")
        if callback_url and not self.validate_url(callback_url):
            return False, f"Invalid callback webhook URL: {callback_url}", {}
        
        # Build validated data
        validated_data = {
            "client_name": input_data["client_name"].strip(),
            "client_email": input_data["client_email"].strip().lower(),
            "client_website": self.normalize_url(input_data["client_website"]),
            "email_sender_name": input_data.get("email_sender_name", "Sid Kennedy").strip(),
            "email_sender_address": input_data.get("email_sender_address", "kenne.s@talkativecrew.com").strip().lower(),
            "email_thread": input_data.get("email_thread", "").strip(),
            "max_jobs_to_scrape": max_jobs,
            "callback_webhook_url": self.normalize_url(callback_url) if callback_url else None,
            "recruiter_timezone": input_data.get("recruiter_timezone", "UTC"),
            "linkedin_plus_exa": input_data.get("linkedin_plus_exa", True)  # Default: use LinkedIn + Exa fallback
        }
        
        return True, "", validated_data

def main():
    parser = argparse.ArgumentParser(description="Validate input JSON")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", default=str(TMP_DIR / "validated_input.json"), help="Output path")
    args = parser.parse_args()
    
    # Load input
    try:
        with open(args.input, 'r') as f:
            input_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Input file not found: {args.input}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        sys.exit(1)
    
    # Validate
    validator = InputValidator()
    is_valid, error_message, validated_data = validator.validate_input(input_data)
    
    if not is_valid:
        print(f"❌ Validation failed: {error_message}")
        sys.exit(1)
    
    # Create Supabase log entry
    logger = SupabaseLogger()
    run_id = logger.create_run(
        client_name=validated_data["client_name"],
        client_email=validated_data["client_email"],
        client_website=validated_data["client_website"]
    )
    
    # Add run_id to validated data
    validated_data["run_id"] = run_id
    
    # Save validated data
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(validated_data, f, indent=2)
    
    print(f"✅ Input validated successfully")
    print(f"✅ Run ID: {run_id}")
    print(f"✅ Saved to: {output_path}")
    
    # Print validated data
    print("\nValidated data:")
    print(json.dumps(validated_data, indent=2))

if __name__ == "__main__":
    main()
