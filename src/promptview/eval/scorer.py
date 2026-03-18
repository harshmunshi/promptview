"""Scoring functions for eval results."""
import difflib
import json
from typing import Optional, Tuple, List


def exact_match(actual: str, expected: str) -> bool:
    """Case-insensitive exact match after stripping whitespace."""
    return actual.strip().lower() == expected.strip().lower()


def similarity_score(actual: str, expected: str) -> float:
    """SequenceMatcher similarity between 0.0 and 1.0."""
    return difflib.SequenceMatcher(None, actual.strip(), expected.strip()).ratio()


def llm_judge(
    actual: str,
    criteria: Optional[List[str]],
    llm_client,  # LLMClient instance
    expected: Optional[str] = None,
) -> Tuple[float, str]:
    """
    Ask an LLM to score the output on a 1-5 scale.
    Returns (score_0_to_1, reasoning_text).
    """
    criteria_text = ', '.join(criteria) if criteria else 'relevance, coherence, accuracy'
    expected_section = f"\nExpected output:\n{expected}" if expected else ""

    system = (
        "You are an expert evaluator. Score LLM outputs on a 1-5 scale based on the given criteria. "
        "Respond ONLY with valid JSON: {\"score\": <1-5>, \"reasoning\": \"<one sentence>\"}"
    )
    user = (
        f"Criteria: {criteria_text}\n"
        f"Actual output:\n{actual}"
        f"{expected_section}\n\n"
        "Respond with JSON only."
    )

    try:
        response = llm_client.complete(system, user)
        # Strip markdown code fences if present
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        data = json.loads(response.strip())
        raw_score = float(data.get("score", 3))
        reasoning = str(data.get("reasoning", ""))
        # Normalise to 0.0-1.0
        score = max(0.0, min(1.0, (raw_score - 1) / 4))
        return score, reasoning
    except Exception as e:
        return 0.5, f"Judge error: {e}"
