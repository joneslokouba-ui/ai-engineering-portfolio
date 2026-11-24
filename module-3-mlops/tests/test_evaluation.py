import json
from pathlib import Path

import pytest

from evaluation.scoring import check_answer, cost_usd, extract_numbers, percentile, summarize

QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "evaluation" / "questions.json"


def test_extract_numbers_handles_commas_and_decimals():
    assert extract_numbers("It is 2,500 metres, or 2.5 km.") == [2500.0, 2.5]


def test_number_check_accepts_answer_inside_a_sentence():
    assert check_answer("17 x 23 = 391", {"type": "number", "value": 391})
    assert not check_answer("It is 392.", {"type": "number", "value": 391})


def test_number_check_tolerance():
    assert check_answer("About 36.1", {"type": "number", "value": 36, "tolerance": 0.2})


def test_contains_any_and_all_are_case_insensitive():
    assert check_answer("The capital is EDMONTON.", {"type": "contains_any", "keywords": ["Edmonton"]})
    assert check_answer("Elastic Container Service", {"type": "contains_all", "keywords": ["elastic", "container", "service"]})
    assert not check_answer("Elastic Compute Cloud", {"type": "contains_all", "keywords": ["elastic", "container"]})


def test_regex_case_sensitive_symbol():
    check = {"type": "regex", "pattern": "\\bNa\\b", "case_sensitive": True}
    assert check_answer("Na", check)
    assert not check_answer("and na", check)


def test_regex_answer_starts_with_yes():
    check = {"type": "regex", "pattern": "^\\W*yes"}
    assert check_answer("Yes, because accuracy hides rare positives.", check)
    assert not check_answer("No, accuracy is fine. Yes, really.", check)


def test_empty_answer_never_passes():
    assert not check_answer("", {"type": "contains_any", "keywords": ["x"]})
    assert not check_answer(None, {"type": "number", "value": 1})


def test_unknown_check_type_raises():
    with pytest.raises(ValueError):
        check_answer("x", {"type": "magic"})


def test_cost_from_token_counts():
    # 1,000 prompt tokens at $0.15/M plus 2,000 completion tokens at $0.60/M
    assert cost_usd(1000, 2000, 0.15, 0.60) == pytest.approx(0.00135)


def test_percentile_nearest_rank():
    assert percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 50) == 5
    assert percentile([], 95) == 0.0


def test_summarize_counts_errors_as_wrong_and_excludes_them_from_latency():
    rows = [
        {"passed": True, "error": False, "latency_s": 1.0, "prompt_tokens": 20, "completion_tokens": 100, "cost_usd": 0.001},
        {"passed": False, "error": False, "latency_s": 3.0, "prompt_tokens": 20, "completion_tokens": 300, "cost_usd": 0.003},
        {"passed": False, "error": True, "latency_s": 0.0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0},
    ]
    s = summarize(rows)
    assert s["n_questions"] == 3
    assert s["accuracy"] == pytest.approx(0.3333, abs=1e-4)
    assert s["error_count"] == 1
    assert s["latency_ms_mean"] == 2000.0
    assert s["completion_tokens_total"] == 400
    assert s["cost_usd_total"] == pytest.approx(0.004)
    assert s["cost_usd_per_1k_requests"] == pytest.approx(2.0)


def test_question_file_is_valid():
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    questions = data["questions"]
    assert len(questions) == 15
    assert len({q["id"] for q in questions}) == 15
    for q in questions:
        assert q["prompt"].strip()
        assert q["check"]["type"] in {"contains_all", "contains_any", "regex", "number"}
        # every check must run without error on an arbitrary answer
        check_answer("sample answer 1", q["check"])