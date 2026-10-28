import pytest
import json
from backend.app.evaluators.manager import evaluate_output

def test_exact_match():
    r1 = evaluate_output("exact_match", "Paris", "Paris")
    assert r1.passed is True
    assert r1.score == 1.0

    r2 = evaluate_output("exact_match", "Paris ", "Paris")
    # Exact match strips leading/trailing
    assert r2.passed is True

    r3 = evaluate_output("exact_match", "London", "Paris")
    assert r3.passed is False
    assert r3.score == 0.0

def test_normalized_match():
    r1 = evaluate_output("normalized_match", "Carbon.", "carbon")
    assert r1.passed is True
    assert r1.score == 1.0

    r2 = evaluate_output("normalized_match", "The capital is Nusantara!", "Nusantara")
    assert r2.passed is True

def test_structured_output():
    valid_json = '{"name": "Alice", "age": 28, "skills": ["Python"]}'
    criteria = json.dumps({"schema": {"required": ["name", "age", "skills"]}})

    res_valid = evaluate_output("structured_output", valid_json, criteria_json=criteria)
    assert res_valid.passed is True
    assert res_valid.score == 1.0

    missing_key = '{"name": "Alice", "age": 28}'
    res_missing = evaluate_output("structured_output", missing_key, criteria_json=criteria)
    assert res_missing.passed is False
    assert res_missing.score == 0.5
    assert "skills" in res_missing.explanation

    invalid_json = '{"name": "Alice", incomplete'
    res_invalid = evaluate_output("structured_output", invalid_json, criteria_json=criteria)
    assert res_invalid.passed is False
    assert res_invalid.score == 0.0

def test_rubric_evaluator():
    criteria = json.dumps({
        "required_keywords": ["bukit"],
        "max_word_count": 10
    })
    res_pass = evaluate_output("rubric", "Sedikit demi sedikit lama-lama menjadi bukit", criteria_json=criteria)
    assert res_pass.passed is True
    assert res_pass.score == 1.0

    res_missing_kw = evaluate_output("rubric", "Sedikit demi sedikit lama-lama menjadi gunung", criteria_json=criteria)
    assert res_missing_kw.passed is False
    assert res_missing_kw.score < 0.8
