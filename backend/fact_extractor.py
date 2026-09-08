"""
Fact Extractor — uses Google Gemini to extract structured facts from a page chunk.

Design:
  - Each call sends ONE page chunk to the LLM (keeps context small and costs low).
  - The LLM is instructed to return JSON; we parse it and validate minimally.
  - Malformed responses are logged and skipped — we never crash silently.
"""

import json
import logging
import os
import re
from typing import Any

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from pdf_parser import PageChunk

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  Gemini client setup
# --------------------------------------------------------------------------- #

_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# --------------------------------------------------------------------------- #
#  Extraction prompt (generic — no document-specific assumptions)
# --------------------------------------------------------------------------- #

EXTRACTION_SYSTEM_PROMPT = """You are a precise fact-extraction engine.
Your task: read the provided text from ONE PAGE of a document and extract every discrete, verifiable factual claim.

Return ONLY valid JSON — no markdown fences, no prose — in this exact format:
{
  "facts": [
    {
      "claim": "<concise plain-language statement of the fact>",
      "entities": ["<entity1>", "<entity2>"],
      "numbers": [{"value": <number_or_null>, "unit": "<unit string or empty>", "context": "<brief context>"}],
      "time_period": "<date, year, quarter, or range this fact refers to, or null>",
      "source_quote": "<exact verbatim text span from the input that best supports this fact>",
      "attributes": {"<any_extra_key>": "<value>"}
    }
  ]
}

Rules:
- Extract ONLY facts explicitly stated in the text; do NOT infer or hallucinate.
- If a number has a unit (%, ₹ crore, USD million, bps, etc.), always include it.
- `source_quote` must be a substring that actually appears in the input text.
- If no facts are present, return {"facts": []}.
- Do not emit any key not listed above.
- `entities` should include named organisations, countries, people, or identifiers.
- One fact per atomic claim (do not merge multiple claims into one).
"""

# --------------------------------------------------------------------------- #
#  Public API
# --------------------------------------------------------------------------- #

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def extract_facts_from_chunk(
    chunk: PageChunk,
    document_id: int,
) -> list[dict[str, Any]]:
    """
    Call the LLM on a single page chunk and return a list of extracted fact dicts
    (not yet persisted to DB — just raw dicts).

    Each dict matches the Fact model fields (without id/embedding/created_at).
    """
    if not chunk["text"].strip():
        logger.debug("Skipping empty page %d", chunk["page_number"])
        return []

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Please add it to backend/.env"
        )
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name=_MODEL_NAME,
        system_instruction=EXTRACTION_SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(
            temperature=0.0,
            response_mime_type="application/json",
        ),
    )

    user_message = (
        f"[Document ID: {document_id} | Page: {chunk['page_number']}]\n\n"
        f"{chunk['text']}"
    )

    response = await model.generate_content_async(user_message)
    raw_text = response.text.strip()

    facts = _parse_llm_response(raw_text, document_id, chunk["page_number"])
    logger.info(
        "Page %d → %d fact(s) extracted", chunk["page_number"], len(facts)
    )
    return facts


# --------------------------------------------------------------------------- #
#  Internal helpers
# --------------------------------------------------------------------------- #

def _parse_llm_response(
    raw_text: str,
    document_id: int,
    page_number: int,
) -> list[dict[str, Any]]:
    """Parse and validate the LLM JSON response into a list of fact dicts."""
    # Strip accidental markdown code fences
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
    raw_text = re.sub(r"```\s*$", "", raw_text, flags=re.MULTILINE)

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error(
            "JSON parse error on page %d: %s\nRaw response (first 500 chars): %s",
            page_number,
            exc,
            raw_text[:500],
        )
        return []

    raw_facts = payload.get("facts", [])
    if not isinstance(raw_facts, list):
        logger.error("LLM returned non-list 'facts' on page %d", page_number)
        return []

    results: list[dict[str, Any]] = []
    for raw in raw_facts:
        if not isinstance(raw, dict):
            continue
        claim = str(raw.get("claim", "")).strip()
        if not claim:
            continue  # Skip empty claims

        fact: dict[str, Any] = {
            "document_id": document_id,
            "page_number": page_number,
            "claim": claim,
            "entities": _coerce_string_list(raw.get("entities")),
            "numbers": _coerce_numbers(raw.get("numbers")),
            "time_period": str(raw.get("time_period") or "").strip() or None,
            "source_quote": str(raw.get("source_quote") or "").strip() or None,
            "attributes": raw.get("attributes") if isinstance(raw.get("attributes"), dict) else {},
        }
        results.append(fact)

    return results


def _coerce_string_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return None


def _coerce_numbers(value: Any) -> list[dict] | None:
    if value is None:
        return None
    if isinstance(value, list):
        cleaned = []
        for item in value:
            if isinstance(item, dict):
                cleaned.append({
                    "value": item.get("value"),
                    "unit": str(item.get("unit", "")),
                    "context": str(item.get("context", "")),
                })
        return cleaned or None
    return None
