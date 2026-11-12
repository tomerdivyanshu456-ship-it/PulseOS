"""Lightweight local retrieval over the explicitly selected document.

This is retrieval-augmented evidence, not an LLM: it returns ranked source
passages and deliberately does not invent a natural-language synthesis.
"""
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.services.dataset_service import DOCUMENT_DIR, get_dataset_record


def _chunks(text, chunk_size=1200, overlap=180):
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            start = 0
            while start < len(paragraph):
                piece = paragraph[start:start + chunk_size].strip()
                if piece:
                    chunks.append(piece)
                start += chunk_size - overlap
            continue
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = paragraph
    if current:
        chunks.append(current)
    return chunks


def retrieve_document_evidence(question, top_k=5):
    """Retrieve passages from the active document using local TF-IDF similarity."""
    try:
        record = get_dataset_record("documents")
    except ValueError as exc:
        return {"status": "no_active_document", "passages": [], "message": str(exc)}
    if record is None:
        return {"status": "no_documents", "passages": [], "message": "No document has been uploaded."}

    path = DOCUMENT_DIR / record["stored_filename"]
    if not path.is_file():
        return {"status": "missing_document", "passages": [], "message": "The selected document text file is missing."}
    text = path.read_text(encoding="utf-8", errors="replace")
    chunks = _chunks(text)
    if not chunks:
        return {"status": "empty_document", "passages": [], "message": "The selected document contains no extractable text."}

    try:
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=12000, sublinear_tf=True)
        matrix = vectorizer.fit_transform(chunks + [question])
        scores = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
    except ValueError:
        return {"status": "no_match", "passages": [], "message": "The question and document do not contain enough searchable terms."}

    ranked = sorted(enumerate(scores), key=lambda item: (-float(item[1]), item[0]))
    passages = []
    for index, score in ranked[:max(1, min(int(top_k), 8))]:
        if score <= 0:
            continue
        passages.append({
            "document_id": record["id"],
            "document_name": record["original_filename"],
            "chunk_index": index + 1,
            "similarity": round(float(score), 4),
            "text": chunks[index],
            "locator": f"Chunk {index + 1}",
            "page": None,
        })
    return {
        "status": "ready" if passages else "no_match",
        "document_name": record["original_filename"],
        "passages": passages,
        "methodology": "Local TF-IDF unigram/bigram cosine retrieval over overlapping text chunks. Similarity ranks lexical relevance; it is not a confidence or factuality score.",
        "limitations": [
            "This version retrieves text but does not use a generative language model to synthesize an answer.",
            "PDF page-level offsets are not retained by the current document extraction pipeline; citations identify chunk numbers instead.",
            "Scanned PDFs without an embedded text layer are not searchable because OCR is not enabled.",
            "Only the currently selected Documents source is searched.",
        ],
    }
