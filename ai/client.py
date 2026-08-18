# Blender AI Agent - NVIDIA API Client
import json
import urllib.request
import urllib.error
import os
from typing import Dict, Any, Optional

from .prompts import SYSTEM_PROMPT


class NVIDIAAPIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _get_api_key(preferences) -> str:
    """Get API key from preferences or environment variable."""
    # Try preferences first
    if preferences and preferences.api_key:
        return preferences.api_key
    # Fallback to environment variable
    return os.environ.get("NVIDIA_API_KEY", "")


def _build_messages(user_command: str) -> list:
    """Build messages array for the API request."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_command},
    ]


def send_command(
    user_command: str,
    preferences,
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    Send a command to NVIDIA Nemotron API and return parsed JSON response.
    
    Args:
        user_command: Natural language command from user
        preferences: Blender addon preferences with API config
        timeout: Request timeout in seconds
    
    Returns:
        Parsed JSON response from the model
    
    Raises:
        NVIDIAAPIError: On API errors, network issues, or invalid responses
    """
    api_key = _get_api_key(preferences)
    if not api_key:
        raise NVIDIAAPIError(
            "API key not configured. Set it in Blender Preferences > Add-ons > Blender AI Agent "
            "or set NVIDIA_API_KEY environment variable."
        )

    endpoint = preferences.api_endpoint or "https://integrate.api.nvidia.com/v1"
    url = f"{endpoint.rstrip('/')}/chat/completions"

    payload = {
        "model": preferences.model_name or "nvidia/nemotron-3-ultra-550b-a55b",
        "messages": _build_messages(user_command),
        "max_tokens": preferences.max_tokens or 1024,
        "temperature": preferences.temperature if preferences.temperature is not None else 0.1,
        "stream": False,
    }

    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response_data = response.read().decode("utf-8")
            result = json.loads(response_data)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        raise NVIDIAAPIError(
            f"API request failed (HTTP {e.code}): {error_body}",
            status_code=e.code,
        )
    except urllib.error.URLError as e:
        raise NVIDIAAPIError(f"Network error: {e.reason}")
    except json.JSONDecodeError as e:
        raise NVIDIAAPIError(f"Invalid JSON response: {e}")
    except Exception as e:
        raise NVIDIAAPIError(f"Request failed: {e}")

    # Extract content from OpenAI-compatible response
    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise NVIDIAAPIError(f"Unexpected API response format: {e}")

    # Parse the JSON from the model's response
    try:
        # Try to find JSON in the response (model might include extra text)
        content = content.strip()
        # Find first { and last }
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = content[start:end+1]
            return json.loads(json_str)
        else:
            raise NVIDIAAPIError("No JSON object found in model response")
    except json.JSONDecodeError as e:
        raise NVIDIAAPIError(f"Model returned invalid JSON: {e}. Raw: {content[:200]}")