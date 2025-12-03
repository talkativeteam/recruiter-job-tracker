#!/usr/bin/env python3
"""
Local test runner for the recruiter job tracker
Run without Flask/Railway, directly invoking the orchestrator
"""

import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from execution.orchestrator import Orchestrator

def run_local_test(input_file=None):
    """Run test with local input"""
    
    # Load test input from file if provided, otherwise use default
    if input_file:
        print(f"📂 Loading input from: {input_file}")
        with open(input_file, 'r') as f:
            test_input = json.load(f)
    else:
        # Default test input
        test_input = {
            "client_name": "Vince Dunne",
            "client_email": "vince@dunnesearchgroup.com",
            "client_website": "https://dunnesearchgroup.com/",
            "email_sender_name": "Sid Kennedy",
            "email_sender_address": "kenne.s@talkativecrew.com",
            "max_jobs_to_scrape": 400,
            "callback_webhook_url": None,
            "recruiter_timezone": ""
        }
    
    print("=" * 80)
    print("🚀 LOCAL TEST RUN - Recruiter Job Tracker")
    print("=" * 80)
    print(f"\n📝 Input:")
    print(json.dumps({k: v if k != "email_thread" else "[email thread...]" for k, v in test_input.items()}, indent=2))
    print("\n" + "=" * 80)
    
    try:
        # Run orchestrator
        orchestrator = Orchestrator()
        result = orchestrator.run_full_pipeline(test_input)
        
        # Display results
        print("\n" + "=" * 80)
        print("✅ PROCESSING COMPLETE")
        print("=" * 80)
        
        if result:
            print(f"\n📊 Statistics:")
            stats = result.get("stats", {})
            for key, value in stats.items():
                print(f"  {key}: {value}")
            
            print(f"\n📧 Email Preview:")
            email = result.get("outreach_email", "")
            if email:
                print("-" * 80)
                print(email)
                print("-" * 80)
            
            print(f"\n💰 Total Cost: {result.get('total_cost', '$0.00')}")
            
            # Save full result to file
            output_path = Path(__file__).parent / ".tmp" / "local_test_output.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n✅ Full result saved to: {output_path}")
        
        return result
    
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ ERROR: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Check for command-line argument for input file
    import sys
    input_file = sys.argv[1] if len(sys.argv) > 1 else None
    run_local_test(input_file)
