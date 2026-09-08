"""
Fact Comparator — uses Gemini to classify the relationship between two facts.

Categories:
  corroboration       — same underlying fact confirmed across documents
  contradiction       — genuine conflict not explained by context
  context_explained   — apparent conflict reconciled by time period, data vintage,
                        scope, units, or other context

The comparator is only called AFTER embedding-based candidate retrieval filters
the search space down to plausible pairs (see embeddings.py).
"""

import json
import logging
import os
import re
from typing import Any

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

VALID_CATEGORIES = {"corroboration", "contradiction", "context_explained"}

# --------------------------------------------------------------------------- #
#  Comparison prompt
# --------------------------------------------------------------------------- #

COMPARISON_SYSTEM_PROMPT = """You are a precise fact-comparison engine.
You will be given TWO factual claims extracted from different documents, along with their metadata.
Your task: classify the relationship between them.

Return ONLY valid JSON with exactly these keys:
{
  "category": "<corroboration | contradiction | context_explained>",
  "explanation": "<clear natural-language explanation of why you chose this category, max 3 sentences>"
}

Definitions:
  corroboration     — Both facts make the same assertion (possibly with minor wording differences, rounding,
                      or unit conversion). They are mutually consistent and reinforce each other.
  contradiction     — The facts make conflicting assertions about the same subject that cannot be reconciled
                      by context (different time periods, data vintage, scope, or units).
  context_explained — The facts appear to conflict but the difference is fully explained by context:
                      different reporting periods, preliminary vs revised data, different geographic scope,
                      different unit scales, or other stated caveats. There is no genuine factual conflict.

Be conservative: classify as context_explained if there is a plausible reconciling context,
even if that context is not explicitly stated in the provided text.
Classify as contradiction only when there is a clear, irreconcilable conflict.
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
async def compare_facts(
    fact_a: dict[str, Any],
    fact_b: dict[str, Any],
    similarity_score: float,
) -> dict[str, Any] | None:
    """
    Ask the LLM to classify the relationship between fact_a and fact_b.

    Returns a dict with keys: category, explanation, similarity_score.
    Returns None on unrecoverable parse failure (logged; caller skips this pair).
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=_MODEL_NAME,
        system_instruction=COMPARISON_SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(
            temperature=0.0,
            response_mime_type="application/json",
        ),
    )

    user_message = _build_comparison_prompt(fact_a, fact_b, similarity_score)
    response = await model.generate_content_async(user_message)
    raw_text = response.text.strip()

    result = _parse_comparison_response(raw_text, fact_a["id"], fact_b["id"])
    if result:
        result["similarity_score"] = similarity_score
    return result


# --------------------------------------------------------------------------- #
#  Internal helpers
# --------------------------------------------------------------------------- #

def _build_comparison_prompt(
    fact_a: dict[str, Any],
    fact_b: dict[str, Any],
    similarity_score: float,
) -> str:
    def _fmt(fact: dict[str, Any]) -> str:
        lines = [
            f"  Claim       : {fact.get('claim', '')}",
            f"  Entities    : {', '.join(fact.get('entities') or []) or 'N/A'}",
            f"  Time Period : {fact.get('time_period') or 'N/A'}",
            f"  Numbers     : {_fmt_numbers(fact.get('numbers'))}",
            f"  Source Quote: {(fact.get('source_quote') or '')[:300]}",
            f"  Document    : {fact.get('document_original_name') or fact.get('document_id', '')}",
            f"  Page        : {fact.get('page_number') or 'N/A'}",
        ]
        return "\n".join(lines)

    return (
        f"Embedding similarity score: {similarity_score:.3f}\n\n"
        f"FACT A:\n{_fmt(fact_a)}\n\n"
        f"FACT B:\n{_fmt(fact_b)}\n\n"
        "Classify the relationship between Fact A and Fact B."
    )


def _fmt_numbers(numbers: list[dict] | None) -> str:
    if not numbers:
        return "N/A"
    parts = []
    for n in numbers:
        val = n.get("value")
        unit = n.get("unit", "")
        ctx = n.get("context", "")
        parts.append(f"{val}{' ' + unit if unit else ''}{' (' + ctx + ')' if ctx else ''}")
    return "; ".join(parts) if parts else "N/A"


def _parse_comparison_response(
    raw_text: str,
    fact_a_id: int,
    fact_b_id: int,
) -> dict[str, Any] | None:
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
    raw_text = re.sub(r"```\s*$", "", raw_text, flags=re.MULTILINE)

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error(
            "JSON parse error comparing facts %d vs %d: %s\nResponse: %s",
            fact_a_id, fact_b_id, exc, raw_text[:500],
        )
        return None

    category = str(payload.get("category", "")).strip().lower()
    if category not in VALID_CATEGORIES:
        logger.warning(
            "Unknown category '%s' for facts %d vs %d; skipping pair.",
            category, fact_a_id, fact_b_id,
        )
        return None

    explanation = str(payload.get("explanation", "")).strip()
    if not explanation:
        logger.warning("Empty explanation for facts %d vs %d", fact_a_id, fact_b_id)
        explanation = "No explanation provided."

    return {"category": category, "explanation": explanation}
