"""
Module 11 — HELIX: Hybrid RAG regression tests

Retrieval (VectorSim + KeywordScore) is fully offline and tested for
real here. Generation (the Groq API call) is mocked, since this sandbox
has no live Groq API key — the mock verifies generate_answer() wires
retrieval -> context -> API call correctly, not that Groq itself works.

Run: pytest test_hybrid_rag.py -v
"""

from unittest.mock import MagicMock, patch

import pytest

from src.rag.hybrid_rag import GroqAPIKeyMissingError, generate_answer, retrieve
from src.rag.knowledge_base_builder import build_knowledge_base
from src.ingestion.omim_loader import load_omim_knowledge

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def kb():
    disorders = load_omim_knowledge(f"{FIXTURES}/omim_sample.csv")
    return build_knowledge_base(disorders)


class TestKnowledgeBaseBuilder:
    def test_builds_one_chunk_per_section_per_disorder(self, kb):
        # 3 disorders in the fixture x 4 sections each = 12 chunks
        assert len(kb.chunks) == 12

    def test_empty_disorders_raises(self):
        with pytest.raises(ValueError):
            build_knowledge_base({})


class TestRetrievalValidation:
    def test_empty_query_raises(self, kb):
        with pytest.raises(ValueError):
            retrieve("", kb)

    def test_whitespace_only_query_raises(self, kb):
        with pytest.raises(ValueError):
            retrieve("   ", kb)

    def test_alpha_out_of_range_raises(self, kb):
        with pytest.raises(ValueError):
            retrieve("cystic fibrosis", kb, alpha=1.5)

    def test_top_k_less_than_one_raises(self, kb):
        with pytest.raises(ValueError):
            retrieve("cystic fibrosis", kb, top_k=0)


class TestRetrievalRelevance:
    def test_query_about_cf_inheritance_returns_cf_chunk_top_ranked(self, kb):
        results = retrieve("What is the inheritance pattern of Cystic Fibrosis?", kb, top_k=3)
        assert results[0].chunk.disorder == "Cystic Fibrosis"
        assert results[0].hybrid_score > 0

    def test_query_about_sickle_cell_does_not_top_rank_huntingtons(self, kb):
        results = retrieve("sickle cell disease hemoglobin", kb, top_k=1)
        assert results[0].chunk.disorder == "Sickle Cell Disease"

    def test_results_are_sorted_descending_by_hybrid_score(self, kb):
        results = retrieve("genetic disorder inheritance", kb, top_k=5)
        scores = [r.hybrid_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_top_k_respected(self, kb):
        results = retrieve("cystic fibrosis", kb, top_k=2)
        assert len(results) <= 2


class TestAlphaWeighting:
    """
    Confirms alpha genuinely changes ranking behavior — alpha=1.0 should
    match pure VectorSim ranking, alpha=0.0 should match pure
    KeywordScore ranking. If these ever produced identical rankings, the
    hybrid formula wouldn't actually be hybrid.
    """

    def test_alpha_zero_uses_pure_keyword_score_for_ranking(self, kb):
        results = retrieve("CFTR chloride", kb, alpha=0.0, top_k=3)
        for r in results:
            assert r.hybrid_score == pytest.approx(r.keyword_score)

    def test_alpha_one_uses_pure_vector_sim_for_ranking(self, kb):
        results = retrieve("CFTR chloride", kb, alpha=1.0, top_k=3)
        for r in results:
            assert r.hybrid_score == pytest.approx(r.vector_sim)


class TestGenerateAnswerKeyHandling:
    def test_missing_api_key_raises_clear_error(self, kb, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        with pytest.raises(GroqAPIKeyMissingError):
            generate_answer("What causes Cystic Fibrosis?", kb)

    @patch("groq.Groq")
    def test_generate_answer_wires_retrieval_into_groq_call(self, mock_groq_class, kb):
        # Mock the Groq client entirely — this tests that generate_answer
        # correctly retrieves context and calls the API with it, not that
        # Groq's actual API works (untestable without a live key here).
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Mocked answer about CF."))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_class.return_value = mock_client

        answer = generate_answer(
            "What is the inheritance pattern of Cystic Fibrosis?",
            kb,
            api_key="fake-test-key",
        )

        assert answer == "Mocked answer about CF."
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "openai/gpt-oss-120b"
        # Confirm retrieved context (Cystic Fibrosis chunk text) actually
        # made it into the prompt sent to the model.
        user_message = call_kwargs["messages"][1]["content"]
        assert "Cystic Fibrosis" in user_message
        assert "QUESTION: What is the inheritance pattern" in user_message


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))