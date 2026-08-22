# Blender AI Agent - NVIDIA API Client
import json
import urllib.request
import urllib.error
import os
import time
import socket
import uuid
from typing import Dict, Any, Optional, Tuple

from .prompts import SYSTEM_PROMPT
from .scene_context import collect_scene_context, format_scene_context_for_prompt


class NVIDIAAPIError(Exception):
    """Exception for NVIDIA API errors with detailed categorization."""
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None, 
        raw_response: str = "",
        error_type: str = "unknown",
        attempt: int = 0,
        request_id: str = ""
    ):
        self.message = message
        self.status_code = status_code
        self.raw_response = raw_response
        self.error_type = error_type
        self.attempt = attempt
        self.request_id = request_id
        super().__init__(message)


# Error type constants - granular categorization
ERROR_TYPE_TIMEOUT = "timeout"
ERROR_TYPE_HTTP_503 = "http_503"
ERROR_TYPE_HTTP_ERROR = "http_error"
ERROR_TYPE_NETWORK = "network"
ERROR_TYPE_JSON_PARSE = "json_parse"
ERROR_TYPE_API_FORMAT = "api_format"
ERROR_TYPE_VALIDATION = "validation_error"
ERROR_TYPE_UNKNOWN = "unknown"


def _get_api_key(preferences) -> str:
    """Get API key from preferences or environment variable."""
    if preferences and preferences.api_key:
        return preferences.api_key
    return os.environ.get("NVIDIA_API_KEY", "")


def _build_messages(
    user_command: str,
    scene_context: Optional[Dict[str, Any]] = None,
    is_retry: bool = False,
    attempt: int = 0,
    request_id: str = "",
) -> list:
    """Build messages array for the API request with optional scene context."""
    system_prompt = SYSTEM_PROMPT
    
    if scene_context:
        from .scene_context import format_scene_context_for_prompt
        context_str = format_scene_context_for_prompt(scene_context)
        system_prompt = f"{SYSTEM_PROMPT}\n\n{context_str}\n\n---\n"
    
    # FINAL INSTRUCTION - JSON-only output, placed LAST so it cannot be overridden
    system_prompt += (
        "\n\nSTRICT OUTPUT FORMAT REQUIREMENT:\n"
        "Your response will be parsed directly by json.loads().\n"
        "You MUST output ONLY a single valid JSON object with exactly this structure:\n"
        "{\n"
        "  \"scene\": {\"name\": \"...\", \"description\": \"...\"},\n"
        "  \"actions\": [\n"
        "    {\"action\": \"create_object\", \"object_type\": \"cube\", \"location\": [0,0,0], ...},\n"
        "    {\"action\": \"create_light\", \"light_type\": \"SUN\", \"brightness\": 5.0, ...}\n"
        "  ]\n"
        "}\n"
        "NO reasoning, NO explanation, NO analysis, NO natural language text.\n"
        "NO markdown, NO code fences, NO conversational text.\n"
        "Start with { and end with }.\n"
        "Every action object in the array MUST be separated by commas.\n"
        "Use the scene context ONLY as reference data for choosing action parameters.\n"
        "Do NOT describe, analyze, or summarize the scene in your response."
    )
    
    if is_retry:
        system_prompt += (
            f"\n\n⚠️ RETRY MODE (attempt {attempt}): Your previous response failed JSON parsing.\n"
            "This is your FINAL attempt. Output ONLY valid JSON.\n"
            "If you include ANY text before or after the JSON, the request will fail permanently."
        )
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_command},
    ]


def _extract_json(content: str) -> Dict[str, Any]:
    """
    Extract JSON from model response with multiple strategies.
    
    Returns parsed JSON dict or raises NVIDIAAPIError.
    """
    content = content.strip()
    
    # Strategy 1: Clean JSON (entire response is JSON)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Find first { and last } (handles surrounding text)
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        json_str = content[start:end+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # Strategy 3: Find first [ and last ] (array response)
    start = content.find("[")
    end = content.rfind("]")
    if start != -1 and end != -1 and end > start:
        json_str = content[start:end+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # Strategy 4: Try to fix common JSON issues
    potential = content[start:end+1] if start != -1 and end != -1 else content
    fixed = _attempt_json_fix(potential)
    if fixed is not None:
        return fixed
    
    # DIAGNOSTIC LOGGING: All strategies failed
    _log_diagnostic("JSON EXTRACTION FAILED - All strategies exhausted")
    _log_diagnostic(f"RAW MODEL RESPONSE:\n{content}")
    _log_diagnostic(f"RESPONSE LENGTH: {len(content)} chars")
    _log_diagnostic(f"RESPONSE PREVIEW (first 500 chars):\n{content[:500]}")
    
    raise NVIDIAAPIError(
        "No valid JSON object found in model response", 
        raw_response=content,
        error_type=ERROR_TYPE_JSON_PARSE
    )


def _attempt_json_fix(text: str) -> Optional[Dict[str, Any]]:
    """Attempt to fix common JSON syntax errors."""
    if not text:
        return None
    
    # Try to fix: trailing commas before } or ]
    fixed = text
    import re
    fixed = re.sub(r',\s*}', '}', fixed)
    fixed = re.sub(r',\s*\]', ']', fixed)
    
    # Try to fix: missing commas between objects in array
    # Pattern: }\s*{ -> },{
    fixed = re.sub(r'}\s*{', '},{', fixed)
    
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    
    # Try wrapping in object if it's an array
    try:
        if fixed.strip().startswith('['):
            return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    
    return None


def _log_diagnostic(message: str) -> None:
    """Log diagnostic message to Blender console."""
    print(f"[BlenderAI Diagnostic] {message}")


def _make_api_call(
    user_command: str,
    preferences,
    timeout: int,
    scene_context: Optional[Dict[str, Any]] = None,
    is_retry: bool = False,
    attempt: int = 0,
    request_id: str = "",
) -> Tuple[str, Dict[str, Any]]:
    """
    Make the actual API call and return (content, raw_response_data).
    
    Returns tuple of (extracted_content, raw_api_response)
    Raises NVIDIAAPIError on failure with proper error_type.
    """
    api_key = _get_api_key(preferences)
    if not api_key:
        raise NVIDIAAPIError(
            "API key not configured. Set it in Blender Preferences > Add-ons > Blender AI Agent "
            "or set NVIDIA_API_KEY environment variable.",
            error_type=ERROR_TYPE_UNKNOWN
        )

    endpoint = preferences.api_endpoint or "https://integrate.api.nvidia.com/v1"
    url = f"{endpoint.rstrip('/')}/chat/completions"

    # Deterministic generation settings
    max_tokens = min(preferences.max_tokens or 8192, 16384)  # Cap at 16384 for complex scenes with reasoning
    temperature = 0.0  # Deterministic output

    payload = {
        "model": preferences.model_name or "nvidia/nemotron-3-ultra-550b-a55b",
        "messages": _build_messages(user_command, scene_context, is_retry, attempt, request_id),
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
        # Request JSON response format if supported
        "response_format": {"type": "json_object"},
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

    # Use single timeout for the complete request (connect + read)
    try:
        response = urllib.request.urlopen(req, timeout=timeout)
        
        # Log HTTP response diagnostics
        status_code = response.getcode()
        content_type = response.headers.get('Content-Type', 'unknown')
        response_data = response.read().decode("utf-8")
        
        _log_diagnostic(f"HTTP Response: status={status_code}, content_type={content_type}, length={len(response_data)} chars")
        _log_diagnostic(f"RAW API RESPONSE:\n{response_data}")
        
    except socket.timeout:
        raise NVIDIAAPIError(
            f"API request timed out after {timeout}s",
            error_type=ERROR_TYPE_TIMEOUT
        )
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        error_type = ERROR_TYPE_HTTP_503 if e.code == 503 else ERROR_TYPE_HTTP_ERROR
        raise NVIDIAAPIError(
            f"API request failed (HTTP {e.code}): {error_body}",
            status_code=e.code,
            raw_response=error_body,
            error_type=error_type
        )
    except urllib.error.URLError as e:
        if isinstance(e.reason, socket.timeout) or "timeout" in str(e.reason).lower():
            raise NVIDIAAPIError(
                f"Network timeout: {e.reason}",
                error_type=ERROR_TYPE_TIMEOUT
            )
        raise NVIDIAAPIError(f"Network error: {e.reason}", error_type=ERROR_TYPE_NETWORK)
    except json.JSONDecodeError as e:
        raise NVIDIAAPIError(f"Invalid JSON response from API: {e}", error_type=ERROR_TYPE_API_FORMAT)
    except Exception as e:
        if "timeout" in str(e).lower():
            raise NVIDIAAPIError(f"Request timed out: {e}", error_type=ERROR_TYPE_TIMEOUT)
        raise NVIDIAAPIError(f"Request failed: {e}", error_type=ERROR_TYPE_UNKNOWN)

    # Parse API response
    try:
        result = json.loads(response_data)
    except json.JSONDecodeError as e:
        raise NVIDIAAPIError(
            f"API returned invalid JSON: {e}", 
            raw_response=response_data,
            error_type=ERROR_TYPE_API_FORMAT
        )

    # Extract content from OpenAI-compatible response
    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise NVIDIAAPIError(
            f"Unexpected API response format: {e}", 
            raw_response=response_data,
            error_type=ERROR_TYPE_API_FORMAT
        )

    # Extract token usage and finish_reason for diagnostics
    choice = result["choices"][0]
    finish_reason = choice.get("finish_reason", "unknown")
    usage = result.get("usage", {})
    completion_tokens = usage.get("completion_tokens", 0)
    prompt_tokens = usage.get("prompt_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)

    # Diagnostic logging
    _log_diagnostic(f"Finish reason: {finish_reason}")
    _log_diagnostic(f"Token usage: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}")
    _log_diagnostic(f"Requested max_tokens: {max_tokens}")
    _log_diagnostic(f"Extracted model content length: {len(content)} chars")
    _log_diagnostic(f"Model content preview: {content[:200]}")
    
    return content, result


def _execute_with_retry(
    user_command: str,
    preferences,
    timeout: int,
    scene_context: Optional[Dict[str, Any]],
    max_retries: int = 2,  # Max 2 retries (3 total attempts)
    base_delay: float = 1.0,
) -> str:
    """
    Execute API call with retry logic for transient errors.
    
    Returns the extracted content string on success.
    Raises NVIDIAAPIError on permanent failure or exhausted retries.
    """
    request_id = str(uuid.uuid4())[:8]
    last_error = None
    
    _log_diagnostic(f"=== Request {request_id} started ===")
    _log_diagnostic(f"Command: {user_command}")
    _log_diagnostic(f"Max retries: {max_retries}, timeout: {timeout}s")
    
    for attempt in range(max_retries + 1):  # +1 for initial attempt
        is_retry = attempt > 0
        try:
            content, _ = _make_api_call(
                user_command, preferences, timeout,
                scene_context, is_retry, attempt, request_id
            )
            _log_diagnostic(f"Request {request_id} succeeded on attempt {attempt + 1}")
            return content
            
        except NVIDIAAPIError as e:
            last_error = e
            e.attempt = attempt
            e.request_id = request_id
            
            # Determine if error is retryable
            retryable = e.error_type in (
                ERROR_TYPE_TIMEOUT,
                ERROR_TYPE_HTTP_503,
                ERROR_TYPE_NETWORK,
            )
            
            # JSON parse errors get ONE retry with repair instruction
            if e.error_type == ERROR_TYPE_JSON_PARSE and attempt == 0:
                retryable = True
            
            if not retryable or attempt >= max_retries:
                # Non-retryable or exhausted retries
                _log_diagnostic(f"Request {request_id} failed after {attempt + 1} attempt(s): {e.error_type} - {e.message}")
                raise NVIDIAAPIError(
                    f"{e.message} (after {attempt + 1} attempt(s))",
                    status_code=e.status_code,
                    raw_response=e.raw_response,
                    error_type=e.error_type,
                    attempt=attempt,
                    request_id=request_id
                )
            
            # Exponential backoff with jitter
            delay = base_delay * (2 ** attempt) + (0.1 * attempt)
            _log_diagnostic(f"Attempt {attempt + 1} failed ({e.error_type}): {e.message}. Retrying in {delay:.1f}s...")
            time.sleep(delay)
    
    # Should not reach here
    raise last_error


def send_command(
    user_command: str,
    preferences,
    timeout: int = 60,
    scene_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Send a command to NVIDIA Nemotron API and return parsed JSON response.
    
    Features:
    - Single timeout for complete request (default 60s)
    - Bounded exponential backoff retry for transient errors (timeout, 503, network) - max 2 retries
    - One JSON repair retry on parse failure
    - Strict JSON validation before returning
    - Detailed error categorization with request tracking
    - Deterministic generation settings (temperature=0, capped tokens)
    
    Args:
        user_command: Natural language command from user
        preferences: Blender addon preferences with API config
        timeout: Total request timeout in seconds (default 60)
        scene_context: Optional current scene state for context-aware planning
    
    Returns:
        Parsed JSON response from the model (validated)
    
    Raises:
        NVIDIAAPIError: On API errors, network issues, or invalid responses
    """
    # Execute with retry logic using single timeout
    content = _execute_with_retry(
        user_command, preferences, timeout,
        scene_context, max_retries=2, base_delay=1.0
    )
    
    # Parse and validate JSON - this is the FINAL validation
    # If this fails, NO actions will be executed
    result = _extract_json(content)
    
    # Final diagnostic
    _log_diagnostic(f"Final result: {result.get('scene', {}).get('name', 'unknown')} with {len(result.get('actions', []))} actions")
    
    return result