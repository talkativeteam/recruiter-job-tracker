"""
Webhook Response Sender
Sends final results to callback webhook
"""

import sys
import json
import argparse
from pathlib import Path
import requests

def send_webhook(url: str, data: dict, timeout: int = 30) -> bool:
    """
    Send POST request to webhook URL with results
    """
    try:
        print(f"📤 Sending results to webhook: {url}")
        
        response = requests.post(
            url,
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=timeout
        )
        
        response.raise_for_status()
        
        print(f"✅ Webhook delivery successful (status: {response.status_code})")
        return True
    
    except requests.exceptions.Timeout:
        print(f"❌ Webhook timeout after {timeout}s")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Webhook delivery failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Send results to webhook")
    parser.add_argument("--url", required=True, help="Webhook URL")
    parser.add_argument("--data", required=True, help="Path to results JSON file")
    args = parser.parse_args()
    
    # Load results
    with open(args.data, 'r') as f:
        data = json.load(f)
    
    # Send webhook
    success = send_webhook(args.url, data)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
