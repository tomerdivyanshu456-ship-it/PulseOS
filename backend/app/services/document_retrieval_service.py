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
            "Answers are extractive: relevant source lines are selected verbatim; no generative language model paraphrases or invents content.",
            "PDF page-level offsets are not retained by the current document extraction pipeline; citations identify chunk numbers instead.",
            "Scanned PDFs without an embedded text layer are not searchable because OCR is not enabled.",
            "Only the currently selected Documents source is searched.",
        ],
    }



def synthesize_document_answer(question, passages, max_sentences=6):
    """Create a transparent extractive answer from retrieved source text.

    This deliberately does not paraphrase or invent facts: selected source
    lines are returned verbatim with chunk-level citations.
    """
    if not passages:
        return None

    lines = []
    for passage in passages:
        for raw_line in passage.get("text", "").splitlines():
            line = re.sub(r"^\s*(?:[•*\-]|\d+[.)])\s*", "", raw_line).strip()
            if len(line) >= 18:
                lines.append({
                    "text": line,
                    "document_name": passage.get("document_name", "Selected document"),
                    "chunk_index": passage.get("chunk_index"),
                    "locator": passage.get("locator", f"Chunk {passage.get('chunk_index', '?')}"),
                })

    if not lines:
        return None

    # Section questions (e.g. "describe experience section") should return
    # the contents of that named section rather than only matching its heading.
    section_match = re.search(
        r"\b(education|experience|work experience|projects|skills|certifications|summary|objective)\b",
        question,
        re.IGNORECASE,
    )
    selected = []
    if section_match:
        target = section_match.group(1).lower()
        heading_pattern = re.compile(
            r"^\s*(?:#{1,3}\s*)?" + re.escape(target) + r"\s*:?[\s]*$",
            re.IGNORECASE,
        )
        heading_index = next(
            (i for i, item in enumerate(lines) if heading_pattern.match(item["text"])),
            None,
        )
        if heading_index is not None:
            stop_heading = re.compile(
                r"^\s*(?:#{1,3}\s*)?(education|experience|work experience|projects|skills|certifications|summary|objective)\s*:?[\s]*$",
                re.IGNORECASE,
            )
            for item in lines[heading_index + 1:]:
                if stop_heading.match(item["text"]):
                    break
                if len(item["text"]) >= 24:
                    selected.append(item)
                if len(selected) >= max_sentences:
                    break

    if not selected:
        candidates = [item for item in lines if not re.match(r"^[A-Z][A-Z &/+-]{2,}$", item["text"])]
        if not candidates:
            candidates = lines
        try:
            vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
            matrix = vectorizer.fit_transform(
                [item["text"] for item in candidates] + [question]
            )
            scores = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
            ranked = sorted(
                range(len(candidates)),
                key=lambda index: (-float(scores[index]), index),
            )
            selected_indices = [index for index in ranked if scores[index] > 0][:max_sentences]
            selected = [candidates[index] for index in sorted(selected_indices)]
        except ValueError:
            selected = []

    if not selected:
        return {
            "status": "insufficient_evidence",
            "text": "I found document passages, but none contained enough text matching this question to form a supported answer. Try asking about a specific section or topic.",
            "citations": [],
            "method": "extractive",
        }

    citations = []
    seen = set()
    for item in selected:
        key = (item["document_name"], item["chunk_index"], item["locator"])
        if key not in seen:
            seen.add(key)
            citations.append({
                "document_name": item["document_name"],
                "chunk_index": item["chunk_index"],
                "locator": item["locator"],
            })
    return {
        "status": "ready",
        "text": "\n".join(f"• {item['text']}" for item in selected),
        "citations": citations,
        "method": "extractive",
    }
