# src/gemini_client.py

import os
import json
import time
import requests
from typing import List, Dict, Any

# Default model; adjust if you want a different Gemini model
MODEL_NAME = "gemini-2.5-flash-preview-09-2025"

# Base URL using v1beta endpoint
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Pre-build the URL for generateContent
API_URL = f"{BASE_URL}/models/{MODEL_NAME}:generateContent"

# Max tokens for output text
MAX_OUTPUT_TOKENS = 4096


def get_api_key() -> str:
    """
    Get the Gemini API key from environment variables.
    Tries GEMINI_API_KEY first, then API_KEY.
    """
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("API_KEY", "")


def safe_json_snippet(obj: Any, length: int = 500) -> str:
    try:
        return json.dumps(obj)[:length]
    except Exception:
        return str(obj)[:length]


def call_gemini_api(
    system_prompt: str,
    contents: List[Dict[str, Any]],
    retries: int = 3,
    timeout: int = 60,
) -> str:
    """
    Low-level Gemini HTTP client.
    - Uses v1beta generateContent endpoint
    - Retries on transient errors
    - Returns the concatenated text output, or an error string starting with 'Error' / 'FATAL ERROR'
    """

    key = get_api_key()
    if not key:
        return "FATAL ERROR: API Key is missing. Please set the 'GEMINI_API_KEY' environment variable."

    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": contents if contents else [{"role": "user", "parts": [{"text": "Start."}]}],
        "generationConfig": {"maxOutputTokens": MAX_OUTPUT_TOKENS},
    }

    headers = {"Content-Type": "application/json"}

    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(
                API_URL,
                params={"key": key},
                headers=headers,
                data=json.dumps(payload),
                timeout=timeout,
            )
        except requests.exceptions.RequestException as e:
            if attempt == retries:
                return f"Error connecting to the model after {retries} attempts: {e}"
            time.sleep(2 ** (attempt - 1))
            continue

        # Common HTTP error handling
        if resp.status_code == 400:
            return f"API Error (HTTP 400 Bad Request): {resp.text[:300]}"
        if resp.status_code == 404:
            return f"API Error (HTTP 404 Not Found): Model '{MODEL_NAME}' unavailable at endpoint."

        try:
            result = resp.json()
        except ValueError:
            return f"API Error: Non-JSON response: {resp.text[:500]}"

        try:
            candidates = result.get("candidates", [])
            if candidates:
                extracted_texts = []
                for cand in candidates:
                    content = cand.get("content", {})
                    parts = content.get("parts") or []
                    for p in parts:
                        if isinstance(p, dict) and "text" in p and p["text"]:
                            extracted_texts.append(p["text"])
                    if not parts and isinstance(content, dict) and "text" in content and content["text"]:
                        extracted_texts.append(content["text"])

                if extracted_texts:
                    return "\n\n".join(extracted_texts)

            # Fallback patterns if response format is slightly different
            if "outputText" in result and result["outputText"]:
                return result["outputText"]

            if isinstance(result, dict) and "text" in result and result["text"]:
                return result["text"]

            return (
                "Error: Could not extract content from the API response. "
                f"Raw response snippet: {safe_json_snippet(result)}"
            )

        except Exception as e:
            return (
                f"Error extracting model output: {e}. "
                f"Raw response snippet: {safe_json_snippet(result)}"
            )

    return "API call failed after retries."
