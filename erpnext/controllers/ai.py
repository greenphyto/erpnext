import frappe, requests

def chat_completion(system_prompt, user_text, model=None, temperature=0):
    """
    Call OpenAI-compatible chat completion API.
    
    Reads model & token from site config:
      - ai_model (default: "gpt-4o-mini")
      - ai_token (required)
      - ai_endpoint (default: "https://api.openai.com/v1/chat/completions")
    
    Args:
        system_prompt (str): System-level instruction.
        user_text (str): User message content.
        model (str, optional): Override model name.
        temperature (float): Model temperature (default 0 for deterministic).
    
    Returns:
        str: Response content text, or empty string on failure.
    """
    token = frappe.local.conf.get("ai_token")
    if not token:
        frappe.throw("Missing 'ai_token' in site config")

    model = model or frappe.local.conf.get("ai_model") or "gpt-4o-mini"
    endpoint = frappe.local.conf.get("ai_endpoint") or "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "temperature": temperature,
    }

    resp = requests.post(endpoint, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()

    data = resp.json()
    choices = data.get("choices", [])
    if choices:
        return choices[0].get("message", {}).get("content", "")
    
    return ""
