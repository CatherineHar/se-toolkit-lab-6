#!/usr/bin/env python3
"""
Agent that calls OpenRouter API using only requests library.
No openai package needed.
"""

import os
import sys
import json
import argparse
import requests
from dotenv import load_dotenv

# Load environment variables from .env.agent.secret
load_dotenv('.env.agent.secret')

def log_debug(message):
    """Print debug messages to stderr."""
    print(f"[DEBUG] {message}", file=sys.stderr)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Ask a question to LLM via OpenRouter')
    parser.add_argument('question', type=str, help='The question to ask')
    args = parser.parse_args()
    
    # Get configuration from environment
    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE', 'https://openrouter.ai/api/v1')
    model = os.getenv('LLM_MODEL', 'deepseek/deepseek-chat-v3-0324:free')
    
    if not api_key:
        log_debug("Missing LLM_API_KEY in .env.agent.secret")
        print(json.dumps({"answer": "Error: No API key found", "tool_calls": []}))
        sys.exit(1)
    
    try:
        log_debug(f"Sending request to OpenRouter using model: {model}")
        
        # Prepare the request
        url = f"{api_base}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant. Provide concise answers."},
                {"role": "user", "content": args.question}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        # Make the API call
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        answer = result['choices'][0]['message']['content']
        
        # Prepare output
        output = {
            "answer": answer,
            "tool_calls": []  # Empty for task 1
        }
        
        # Print only JSON to stdout
        print(json.dumps(output, ensure_ascii=False))
        
    except requests.exceptions.RequestException as e:
        log_debug(f"Error calling OpenRouter: {str(e)}")
        print(json.dumps({"answer": f"Error: {str(e)}", "tool_calls": []}))
        sys.exit(1)
    except Exception as e:
        log_debug(f"Unexpected error: {str(e)}")
        print(json.dumps({"answer": f"Error: {str(e)}", "tool_calls": []}))
        sys.exit(1)

if __name__ == "__main__":
    main()