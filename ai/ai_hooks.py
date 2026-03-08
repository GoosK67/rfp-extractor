
import os

def enrich_with_ai(requirements: list[dict]) -> list[dict]:
    '''
    Placeholder AI enrichment: returns input if no Azure OpenAI env vars.
    If AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT exist and 'openai' package
    is installed, you can implement real LLM calls here.
    '''
    key = os.environ.get('AZURE_OPENAI_KEY')
    endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
    if not key or not endpoint:
        return requirements
    try:
        # Lazy import to avoid hard dependency
        from openai import OpenAI
    except Exception:
        return requirements
    # Example skeleton (disabled by default)
    # client = OpenAI(base_url=f"{endpoint}/openai/deployments", api_key=key)
    # ...
    return requirements
