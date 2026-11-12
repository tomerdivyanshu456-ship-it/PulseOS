from app.services import document_retrieval_service


def test_chunks_preserve_paragraphs_and_overlap_long_text():
    text = "First product requirement.\n\n" + ("checkout payment failure details " * 100)
    chunks = document_retrieval_service._chunks(text, chunk_size=300, overlap=40)
    assert len(chunks) > 2
    assert "First product requirement." in chunks[0]
    assert all(len(chunk) <= 300 for chunk in chunks)


def test_retrieval_ranks_relevant_document_passage(monkeypatch, tmp_path):
    document = tmp_path / "selected.txt"
    document.write_text(
        "The mobile app supports account registration and profile settings.\n\n"
        "Payment failures should be logged with gateway response codes. "
        "The checkout service must retry transient gateway timeouts and show a clear error.",
        encoding="utf-8",
    )
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

    result = document_retrieval_service.retrieve_document_evidence("How should checkout handle payment gateway failures?")

    assert result["status"] == "ready"
    assert result["document_name"] == "payments-spec.docx"
    assert result["passages"][0]["chunk_index"] == 1
    assert "gateway response codes" in result["passages"][0]["text"]
    assert result["passages"][0]["page"] is None
    assert "not a confidence" in result["methodology"]


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
            "EDUCATION\\nB.Tech Chemical Engineering.\\n"
            "EXPERIENCE\\nBusiness Analyst Intern at Gyana Deep Products.\\n"
            "Analyzed 50K+ sales and inventory records using Python and Excel.\\n"
            "Developed KPI dashboards that improved peak-season stock availability.\\n"
            "PROJECTS\\nBuilt a machine learning prediction API."
        ),
    }]

    result = document_retrieval_service.synthesize_document_answer(
        "Describe the experience section", passages
    )

    assert result["status"] == "ready"
    assert "Business Analyst Intern" in result["text"]
    assert "50K+ sales and inventory records" in result["text"]
    assert "machine learning prediction API" not in result["text"]
    assert result["citations"][0]["locator"] == "Chunk 1"
    assert result["method"] == "extractive"


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
