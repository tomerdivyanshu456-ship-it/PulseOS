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
