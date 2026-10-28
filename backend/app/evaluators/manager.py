import json
import re
from typing import Dict, Any, Optional
from pydantic import BaseModel

class EvalResult(BaseModel):
    evaluator_name: str
    score: float  # 0.0 to 1.0
    passed: bool
    explanation: str

def evaluate_output(
    eval_type: str,
    actual_output: str,
    expected_output: Optional[str] = None,
    criteria_json: Optional[str] = None
) -> EvalResult:
    if not eval_type or eval_type == "none":
        return EvalResult(evaluator_name="none", score=1.0, passed=True, explanation="No evaluation criteria specified.")

    criteria = {}
    if criteria_json:
        try:
            criteria = json.loads(criteria_json)
        except Exception:
            pass

    actual = (actual_output or "").strip()
    expected = (expected_output or "").strip()

    # 1. Exact Match
    if eval_type == "exact_match":
        is_exact = actual == expected
        return EvalResult(
            evaluator_name="exact_match",
            score=1.0 if is_exact else 0.0,
            passed=is_exact,
            explanation=f"Exact match check: {'Matched perfectly' if is_exact else 'Mismatch between actual and expected'}"
        )

    # 2. Normalized Match
    if eval_type == "normalized_match":
        norm_actual = re.sub(r"[^\w\s]", "", actual.lower()).strip()
        norm_expected = re.sub(r"[^\w\s]", "", expected.lower()).strip()
        is_match = norm_actual == norm_expected or (norm_expected in norm_actual)
        return EvalResult(
            evaluator_name="normalized_match",
            score=1.0 if is_match else 0.0,
            passed=is_match,
            explanation=f"Normalized match check: {'Passed' if is_match else 'Normalized string mismatch'}"
        )

    # 3. Structured JSON Output
    if eval_type == "structured_output":
        try:
            # Locate JSON block or raw string
            json_str = actual
            match = re.search(r"```json(.*?)```", actual, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
            elif actual.startswith("```") and actual.endswith("```"):
                json_str = actual.strip("`").strip()

            parsed = json.loads(json_str)
        except Exception as err:
            return EvalResult(
                evaluator_name="structured_output",
                score=0.0,
                passed=False,
                explanation=f"JSON Parse Failure: {str(err)}"
            )

        schema = criteria.get("schema", {})
        required_keys = schema.get("required", [])
        missing_keys = [k for k in required_keys if k not in parsed]

        if missing_keys:
            return EvalResult(
                evaluator_name="structured_output",
                score=0.5,
                passed=False,
                explanation=f"Valid JSON syntax, but missing required schema fields: {', '.join(missing_keys)}"
            )

        return EvalResult(
            evaluator_name="structured_output",
            score=1.0,
            passed=True,
            explanation="Valid JSON conforming to required schema properties."
        )

    # 4. Rubric & Keyword-based Evaluator
    if eval_type == "rubric":
        required_kw = criteria.get("required_keywords", [])
        forbidden_kw = criteria.get("forbidden_keywords", [])
        max_words = criteria.get("max_word_count", None)

        words = actual.split()
        kw_missing = [kw for kw in required_kw if kw.lower() not in actual.lower()]
        kw_forbidden_found = [kw for kw in forbidden_kw if kw.lower() in actual.lower()]

        score = 1.0
        reasons = []

        if required_kw:
            found_ratio = (len(required_kw) - len(kw_missing)) / len(required_kw)
            score *= found_ratio
            if kw_missing:
                reasons.append(f"Missing keywords: {', '.join(kw_missing)}")

        if kw_forbidden_found:
            score = 0.0
            reasons.append(f"Contains forbidden keywords: {', '.join(kw_forbidden_found)}")

        if max_words and len(words) > max_words:
            score *= 0.5
            reasons.append(f"Exceeded word budget ({len(words)} > {max_words} words)")

        passed = score >= 0.8
        explanation = "; ".join(reasons) if reasons else "Satisfied all rubric criteria."
        return EvalResult(
            evaluator_name="rubric",
            score=round(score, 2),
            passed=passed,
            explanation=explanation
        )

    return EvalResult(evaluator_name=eval_type, score=1.0, passed=True, explanation="Default evaluation pass.")
