import pytest

from src.hybrid_score import hybrid_score, keyword_score, rank


def test_alpha_one_uses_only_vector_similarity():
    assert hybrid_score(0.8, 0.2, alpha=1.0) == pytest.approx(0.8)


def test_alpha_zero_uses_only_keyword_score():
    assert hybrid_score(0.8, 0.2, alpha=0.0) == pytest.approx(0.2)


def test_blend_matches_formula():
    assert hybrid_score(0.5, 1.0, alpha=0.6) == pytest.approx(0.6 * 0.5 + 0.4 * 1.0)


@pytest.mark.parametrize("bad_alpha", [-0.1, 1.1])
def test_alpha_out_of_range_raises(bad_alpha):
    with pytest.raises(ValueError):
        hybrid_score(0.5, 0.5, alpha=bad_alpha)


def test_keyword_score_counts_distinct_query_tokens():
    assert keyword_score("benzene plume", "benzene plume migration") == 1.0
    assert keyword_score("benzene plume", "benzene only") == 0.5
    assert keyword_score("", "anything") == 0.0


def test_rank_orders_best_first():
    candidates = [
        ("a", "unrelated text", 0.2),
        ("b", "benzene plume remediation", 0.7),
    ]
    ranked = rank("benzene plume", candidates, alpha=0.6)
    assert [doc_id for doc_id, _ in ranked] == ["b", "a"]