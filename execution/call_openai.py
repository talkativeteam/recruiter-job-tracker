"""
OpenAI API Caller
Handles all OpenAI API calls with retry logic
"""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import Optional, Dict, Any
from openai import OpenAI

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))
from config.config import MODEL_CHEAP, MODEL_PREMIUM, MAX_RETRIES, RETRY_DELAY
from config import ai_prompts
from execution.supabase_logger import SupabaseLogger

class OpenAICaller:
    def __init__(self, run_id: Optional[str] = None):
        self.client = OpenAI()
        self.run_id = run_id
        self.logger = SupabaseLogger() if run_id else None
        self.total_tokens = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0
        self.model_usage = {}  # Track usage per model
    
    def call_with_retry(self, prompt: str, model: str = MODEL_CHEAP, 
                        temperature: float = 0.3, max_tokens: int = 1000,
                        response_format: str = "json") -> Optional[str]:
        """
        Call OpenAI API with exponential backoff retry
        """
        for attempt in range(MAX_RETRIES):
            try:
                print(f"🤖 Calling OpenAI ({model}, attempt {attempt + 1}/{MAX_RETRIES})...")
                
                if response_format == "json":
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that responds in JSON format."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format={"type": "json_object"}
                    )
                else:
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                
                content = response.choices[0].message.content
                tokens = response.usage.total_tokens
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                
                self.total_tokens += tokens
                self.total_input_tokens += input_tokens
                self.total_output_tokens += output_tokens
                self.call_count += 1
                
                # Track per-model usage
                if model not in self.model_usage:
                    self.model_usage[model] = {"calls": 0, "input_tokens": 0, "output_tokens": 0}
                self.model_usage[model]["calls"] += 1
                self.model_usage[model]["input_tokens"] += input_tokens
                self.model_usage[model]["output_tokens"] += output_tokens
                
                # Calculate cost for this call
                call_cost = self._calculate_call_cost(model, input_tokens, output_tokens)
                
                print(f"✅ OpenAI call successful ({tokens} tokens: {input_tokens} in + {output_tokens} out, ${call_cost:.4f}, total: ${self.get_cost_estimate():.4f})")
                
                return content
            
            except Exception as e:
                print(f"❌ OpenAI call failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY ** (attempt + 1)
                    print(f"⏳ Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    print(f"❌ All retries exhausted")
                    return None
        
        return None
    
    def identify_icp(self, website_content: str) -> Optional[Dict[str, Any]]:
        """Phase 2: Identify recruiter ICP"""
        prompt = ai_prompts.format_icp_prompt(website_content)
        response = self.call_with_retry(prompt, model=MODEL_CHEAP, temperature=0.3)
        
        if not response:
            return None
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON response: {e}")
            return None
    
    def generate_boolean_search(self, icp_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Phase 3: Generate Boolean search"""
        prompt = ai_prompts.format_boolean_search_prompt(icp_data)
        response = self.call_with_retry(prompt, model=MODEL_CHEAP, temperature=0.3)
        
        if not response:
            return None
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON response: {e}")
            return None
    
    def validate_direct_hirer(self, company_name: str, company_description: str,
                              company_industry: str, job_description: str) -> Optional[Dict[str, Any]]:
        """Phase 5: Validate if company is a direct hirer"""
        prompt = ai_prompts.format_direct_hirer_prompt(
            company_name, company_description, company_industry, job_description
        )
        response = self.call_with_retry(prompt, model=MODEL_CHEAP, temperature=0.1)
        
        if not response:
            return None
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON response: {e}")
            return None
    
    def validate_icp_fit(self, recruiter_icp: Dict[str, Any], company_name: str,
                         company_description: str, company_industry: str,
                         employee_count: int, location: str, roles_hiring: list) -> Optional[Dict[str, Any]]:
        """Phase 7: Validate ICP fit"""
        prompt = ai_prompts.format_icp_fit_prompt(
            recruiter_icp, company_name, company_description, company_industry,
            employee_count, location, roles_hiring
        )
        response = self.call_with_retry(prompt, model=MODEL_CHEAP, temperature=0.1)
        
        if not response:
            return None
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON response: {e}")
            return None
    
    def determine_decision_maker(self, company_size: int, role_title: str,
                                  role_seniority: str, role_type: str) -> Optional[Dict[str, Any]]:
        """Phase 8: Determine decision maker role"""
        prompt = ai_prompts.format_decision_maker_prompt(
            company_size, role_title, role_seniority, role_type
        )
        response = self.call_with_retry(prompt, model=MODEL_CHEAP, temperature=0.1)
        
        if not response:
            return None
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON response: {e}")
            return None
    
    def generate_email(self, recruiter_name: str, companies_data: list, 
                       sender_name: str = None, sender_email: str = None, 
                       email_thread: str = None, recruiter_timezone: str = None) -> Optional[str]:
        """Phase 9: Generate outreach email"""
        prompt = ai_prompts.format_email_prompt(
            recruiter_name, companies_data, sender_name, sender_email, email_thread, recruiter_timezone
        )
        
        # Use premium model for client-facing content
        response = self.call_with_retry(
            prompt, 
            model=MODEL_PREMIUM, 
            temperature=0.7, 
            max_tokens=800,
            response_format="text"
        )
        
        return response
    
    def get_cost_estimate(self) -> float:
        """Get estimated cost of all OpenAI calls (returns numeric value)"""
        # Accurate pricing per model (as of Dec 2024)
        # gpt-4o-mini: $0.150 per 1M input tokens, $0.600 per 1M output tokens
        # gpt-4-turbo-preview: $10 per 1M input, $30 per 1M output
        
        total_cost = 0.0
        for model, usage in self.model_usage.items():
            input_tokens = usage["input_tokens"]
            output_tokens = usage["output_tokens"]
            total_cost += self._calculate_call_cost(model, input_tokens, output_tokens)
        
        return total_cost
    
    def _calculate_call_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a single API call based on model and token usage"""
        if "gpt-4o-mini" in model:
            # $0.150 per 1M input, $0.600 per 1M output
            input_cost = (input_tokens / 1_000_000) * 0.150
            output_cost = (output_tokens / 1_000_000) * 0.600
        elif "gpt-4-turbo" in model or "gpt-4" in model:
            # $10 per 1M input, $30 per 1M output
            input_cost = (input_tokens / 1_000_000) * 10.0
            output_cost = (output_tokens / 1_000_000) * 30.0
        else:
            # Default fallback
            input_cost = (input_tokens / 1_000_000) * 0.150
            output_cost = (output_tokens / 1_000_000) * 0.600
        
        return input_cost + output_cost
    
    def get_cost_estimate_str(self) -> str:
        """Get formatted cost string"""
        return f"${self.get_cost_estimate():.2f} OpenAI"

def main():
    parser = argparse.ArgumentParser(description="Call OpenAI API")
    parser.add_argument("--prompt-type", required=True, 
                        choices=["identify_icp", "generate_boolean", "validate_direct_hirer",
                                "validate_icp_fit", "determine_decision_maker", "generate_email"])
    parser.add_argument("--input", help="Input file path")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--model", default=MODEL_CHEAP, help="OpenAI model")
    parser.add_argument("--run-id", help="Run ID for logging")
    args = parser.parse_args()
    
    caller = OpenAICaller(run_id=args.run_id)
    
    # Load input if provided
    input_data = None
    if args.input:
        with open(args.input, 'r') as f:
            if args.input.endswith('.json'):
                input_data = json.load(f)
            else:
                input_data = f.read()
    
    # Call appropriate method based on prompt type
    result = None
    if args.prompt_type == "identify_icp":
        # Handle both string content and JSON with 'content' field
        if isinstance(input_data, dict) and 'content' in input_data:
            result = caller.identify_icp(input_data['content'])
        elif isinstance(input_data, str):
            result = caller.identify_icp(input_data)
    elif args.prompt_type == "generate_boolean" and isinstance(input_data, dict):
        result = caller.generate_boolean_search(input_data)
    # Add other prompt types as needed
    
    if result:
        # Save output
        with open(args.output, 'w') as f:
            if isinstance(result, dict):
                json.dump(result, f, indent=2)
            else:
                f.write(result)
        
        print(f"✅ Saved output to {args.output}")
        print(f"\n💰 Cost: {caller.get_cost_estimate_str()}")
    else:
        print("❌ OpenAI call failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
