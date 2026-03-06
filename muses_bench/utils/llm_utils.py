import os
import time
from litellm import completion
from openai import OpenAI

# Import vLLM helper
try:
    from muses_bench.utils.vllm_helper import generate_vllm_helper
except ImportError:
    pass # Will be imported if needed, or handled inside the function

def call_llm_with_retry(model: str, provider: str, messages: list, temperature: float, max_retries: int = 3, retry_delay: float = 1.0, llm_client=None, lora_request=None):
    """
    Call LLM API with retry mechanism and exponential backoff.
    
    Args:
        model: Model name
        provider: Provider name (e.g., openai, anthropic, vllm)
        messages: Conversation messages
        temperature: Temperature setting
        max_retries: Maximum number of retries
        retry_delay: Initial retry delay in seconds
        llm_client: Optional vLLM client instance
        lora_request: Optional LoRARequest instance
    
    Returns:
        API response object (Mock object for vLLM to match OpenAI structure)
    """
    
    # helper class to mock OpenAI response structure for vLLM
    class MockResponse:
        def __init__(self, content):
            self.choices = [type('Choice', (), {'message': type('Message', (), {'content': content})()})()]

    if provider == "vllm":
        if llm_client is None:
            raise ValueError("llm_client must be provided for vllm provider")
        
        # Lazy import to avoid circular dependencies if any
        from muses_bench.utils.vllm_client import generate_vllm_response
        
        try:
            response_text = generate_vllm_response(
                llm_client, 
                lora_request, 
                messages, 
                temperature=temperature
            )
            return MockResponse(response_text)
        except Exception as e:
             print(f"[ERROR] vLLM generation failed: {e}")
             raise e

    api_base = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE")
    api_key = os.environ.get("OPENAI_API_KEY")
    
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            if api_base:
                # Use OpenAI library directly for proxy APIs
                client = OpenAI(
                    api_key=api_key,
                    base_url=api_base
                )
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature
                )
                
                # Check if response has error
                if hasattr(response, 'error') and response.error:
                    raise Exception(f"API returned error: {response.error}")
                
                # Check if response has choices
                if not response.choices or len(response.choices) == 0:
                    raise Exception("API response has no choices")
                
                # Check if message content exists
                if not response.choices[0].message or not response.choices[0].message.content:
                    raise Exception("API response has no message content")
                
                return response
            else:
                # Use litellm for standard providers
                model_name = f"{provider}/{model}"
                completion_kwargs = {
                    "model": model_name,
                    "messages": messages,
                    "temperature": temperature
                }
                response = completion(**completion_kwargs)
                
                if not response.choices or len(response.choices) == 0:
                    raise Exception("API response has no choices")
                
                if not response.choices[0].message or not response.choices[0].message.content:
                    raise Exception("API response has no message content")
                
                return response
                
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                print(f"[WARNING] API call failed (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"[INFO] Retrying in {wait_time:.1f} seconds...")
                time.sleep(wait_time)
            else:
                print(f"[ERROR] API call failed after {max_retries} attempts: {e}")
                raise
    
    # Should not reach here, but just in case
    raise last_exception if last_exception else Exception("Unknown error in API call")

