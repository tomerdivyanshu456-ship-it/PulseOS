from app.services import document_retrieval_service


def _document_fixture(monkeypatch, tmp_path, text):
    document = tmp_path / "selected.txt"
    document.write_text(text, encoding="utf-8")
    monkeypatch.setattr(document_retrieval_service, "DOCUMENT_DIR", tmp_path)
    monkeypatch.setattr(
        document_retrieval_service,
        "get_dataset_record",
        lambda _kind: {
            "id": "doc-1",
            "stored_filename": "selected.txt",
            "original_filename": "payments-spec.docx",
        },
    )
    return document


def test_chunks_preserve_paragraphs_and_overlap_long_text():
    text = "First product requirement.\n\n" + ("checkout payment failure details " * 100)
    chunks = document_retrieval_service._chunks(text, chunk_size=300, overlap=40)
    assert len(chunks) > 2
    assert "First product requirement." in chunks[0]
    assert all(len(chunk) <= 300 for chunk in chunks)


def test_semantic_retrieval_ranks_passages_and_preserves_response_contract(monkeypatch, tmp_path):
    _document_fixture(
        monkeypatch,
        tmp_path,
        "The mobile app supports account registration and profile settings.\n\n"
        "Payment failures should be logged with gateway response codes. "
        "The checkout service must retry transient gateway timeouts and show a clear error.",
    )
    monkeypatch.setattr(document_retrieval_service, "SEMANTIC_RETRIEVAL_ENABLED", True)
    monkeypatch.setattr(
        document_retrieval_service,
        "_semantic_scores",
        lambda _question, chunks: __import__("numpy").array([0.01, 0.91]),
    )

    result = document_retrieval_service.retrieve_document_evidence(
        "How should the checkout recover when the payment processor is unavailable?"
    )

    assert result["status"] == "ready"
    assert result["retrieval_mode"] == "semantic"
    assert result["document_name"] == "payments-spec.docx"
    assert result["passages"][0]["chunk_index"] == 2
    assert "gateway timeouts" in result["passages"][0]["text"]
    assert result["passages"][0]["page"] is None
    assert "not a confidence" in result["methodology"]


def test_semantic_model_failure_falls_back_to_tfidf(monkeypatch, tmp_path):
    _document_fixture(
        monkeypatch,
        tmp_path,
        "The mobile app supports account registration and profile settings.\n\n"
        "Payment failures should be logged with gateway response codes.",
    )
    monkeypatch.setattr(document_retrieval_service, "SEMANTIC_RETRIEVAL_ENABLED", True)

    def fail_semantic(_question, _chunks):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(document_retrieval_service, "_semantic_scores", fail_semantic)
    result = document_retrieval_service.retrieve_document_evidence(
        "How should payment failures be recorded?"
    )
    assert result["status"] == "ready"
    assert result["retrieval_mode"] == "tfidf"
    assert any("TF-IDF lexical retrieval was used" in item for item in result["limitations"])


def test_semantic_disabled_uses_tfidf_without_loading_model(monkeypatch, tmp_path):
    _document_fixture(
        monkeypatch,
        tmp_path,
        "Payment failures should be logged with gateway response codes.",
    )
    monkeypatch.setattr(document_retrieval_service, "SEMANTIC_RETRIEVAL_ENABLED", False)
    monkeypatch.setattr(
        document_retrieval_service,
        "_semantic_scores",
        lambda *_args: (_ for _ in ()).throw(AssertionError("semantic model must not load")),
    )
    result = document_retrieval_service.retrieve_document_evidence(
        "How should payment failures be recorded?"
    )
    assert result["status"] == "ready"
    assert result["retrieval_mode"] == "tfidf"


def test_retrieval_returns_clear_status_when_no_active_document(monkeypatch):
    def no_active(_kind):
        raise ValueError("No active documents dataset is selected.")

    monkeypatch.setattr(document_retrieval_service, "get_dataset_record", no_active)
    result = document_retrieval_service.retrieve_document_evidence("What is the release plan?")
    assert result["status"] == "no_active_document"
    assert result["passages"] == []


def test_ai_analyst_returns_document_passages_without_event_or_review_data(monkeypatch):
    from app.services import ai_analyst_service

    def no_dataset():
        raise ValueError("No active source selected.")

    passages = [{
        "document_id": "doc-1",
        "document_name": "product-brief.pdf",
        "chunk_index": 2,
        "similarity": 0.42,
        "text": "The product must support offline checkout.",
        "locator": "Chunk 2",
        "page": None,
    }]
    monkeypatch.setattr(ai_analyst_service, "calculate_product_analytics", no_dataset)
    monkeypatch.setattr(ai_analyst_service, "calculate_voice_of_customer", no_dataset)
    monkeypatch.setattr(
        ai_analyst_service,
        "retrieve_document_evidence",
        lambda _question: {
            "status": "ready",
            "document_name": "product-brief.pdf",
            "passages": passages,
            "limitations": ["Document passage retrieval is not a generated summary."],
        },
    )

    result = ai_analyst_service.answer_product_question("What does the brief require?")
    assert result["document_evidence"] == passages
    assert "offline checkout" in result["answer"]
    assert result["document_answer"]["status"] == "ready"
    assert result["document_answer"]["citations"][0]["locator"] == "Chunk 2"
    assert any(source["name"] == "Selected product document" for source in result["sources"])


def test_extractive_answer_returns_requested_cv_section_with_chunk_citation():
    passages = [{
        "document_name": "resume.pdf",
        "chunk_index": 1,
        "locator": "Chunk 1",
        "text": (
            "EDUCATION\nB.Tech Chemical Engineering.\n"
            "EXPERIENCE\nBusiness Analyst Intern at Gyana Deep Products.\n"
            "Analysed sales and inventory records using Python and Excel.\n"
            "Developed KPI dashboards for the business.\n"
            "PROJECTS\nBuilt a machine learning prediction API."
        ),
    }]
    result = document_retrieval_service.synthesize_document_answer(
        "Describe the experience section", passages
    )
    assert result["status"] == "ready"
    assert "Business Analyst Intern" in result["text"]
    assert "machine learning prediction API" not in result["text"]
    assert result["citations"][0]["locator"] == "Chunk 1"


def test_extractive_answer_declines_when_no_sentence_matches():
    passages = [{
        "document_name": "brief.pdf",
        "chunk_index": 3,
        "locator": "Chunk 3",
        "text": "A completely unrelated statement about gardening and soil.",
    }]
    result = document_retrieval_service.synthesize_document_answer(
        "What is the payment gateway timeout policy?", passages
    )
    assert result["status"] == "insufficient_evidence"
    assert result["citations"] == []


def test_broad_document_summary_returns_unranked_overview_chunks(monkeypatch, tmp_path):
    _document_fixture(
        monkeypatch,
        tmp_path,
        "Divyanshu Tomer\nB.Tech Chemical Engineering at BIT Mesra.\n"
        "Business Analyst Intern: worked with SQL and Python.\n"
        "Projects include customer churn prediction and product analytics.",
    )
    monkeypatch.setattr(document_retrieval_service, "SEMANTIC_RETRIEVAL_ENABLED", False)
    result = document_retrieval_service.retrieve_document_evidence(
        "Summarise the key requirements in this document"
    )
    assert result["status"] == "ready"
    assert result["passages"][0]["similarity"] == 0
    answer = document_retrieval_service.synthesize_document_answer(
        "Summarise the key requirements in this document", result["passages"]
    )
    assert answer["status"] == "ready"
    assert "B.Tech Chemical Engineering" in answer["text"]


def test_internship_responsibility_question_retrieves_experience_section(monkeypatch, tmp_path):
    _document_fixture(
        monkeypatch,
        tmp_path,
        "EDUCATION\nB.Tech Chemical Engineering.\n\n"
        "EXPERIENCE\nBusiness Analyst Intern at Gyana Deep Products.\n"
        "Analysed sales and inventory data using SQL and Python.\n"
        "Built KPI dashboards and supported business expansion.\n\n"
        "PROJECTS\nCustomer churn prediction.",
    )
    monkeypatch.setattr(document_retrieval_service, "SEMANTIC_RETRIEVAL_ENABLED", False)
    result = document_retrieval_service.retrieve_document_evidence(
        "What internship experience and responsibilities are described?"
    )
    assert result["status"] == "ready"
    assert any("Business Analyst Intern" in item["text"] for item in result["passages"])
