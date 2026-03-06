"""
Unified API caller for the data generation pipeline
Follows the pattern in IHEval/src/utils/call_api.py
"""

import os
import random
import time
from typing import List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment from the root .env file
DOTENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../.env")
if os.path.exists(DOTENV_PATH):
    from dotenv import load_dotenv
    load_dotenv(DOTENV_PATH, override=True)
    print(f"Loaded environment from {DOTENV_PATH}")
else:
    print(f"Warning: {DOTENV_PATH} not found")

# Debug: check if variables are loaded
if not os.environ.get("OPENAI_API_KEY"):
    print("WARNING: OPENAI_API_KEY is not set in environment!")
else:
    print(f"OPENAI_API_KEY is set (starts with {os.environ.get('OPENAI_API_KEY')[:10]}...)")
if os.environ.get("OPENAI_BASE_URL"):
    print(f"OPENAI_BASE_URL is set to {os.environ.get('OPENAI_BASE_URL')}")

def get_api_client():
    raw_keys = os.environ.get("OPENAI_API_KEY", "")
    api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
    if not api_keys:
        raise ValueError(f"OPENAI_API_KEY not found in {DOTENV_PATH}")
    
    api_key = random.choice(api_keys)
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    return OpenAI(api_key=api_key, base_url=base_url)

def call_model(model: str, messages: List[Dict], temperature: float = 1.0, max_tokens: int = 16384, max_retries: int = 5) -> str:
    client = get_api_client()
    
    retries = 0
    while retries < max_retries:
        try:
            chat_completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = chat_completion.choices[0].message.content
            if content is None:
                print(f"Warning: Model {model} returned None content. Full response: {chat_completion}")
                return ""
            return content
        except Exception as e:
            retries += 1
            print(f"!!! Error calling model '{model}' (Attempt {retries}): {type(e).__name__}: {str(e)}")
            if hasattr(e, 'response'):
                print(f"!!! Response details: {e.response.text if hasattr(e.response, 'text') else e.response}")
            
            if retries == max_retries:
                print(f"!!! Max retries reached for model '{model}'. Returning empty response.")
                return ""
            time.sleep(2 * retries)

    return ""
