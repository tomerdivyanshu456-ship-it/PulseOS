"""Local document retrieval with optional semantic embeddings and TF-IDF fallback.

Semantic mode uses Sentence Transformers on CPU. Model weights are downloaded
on first use and then cached locally. If the optional dependency or model is
unavailable, retrieval transparently falls back to TF-IDF.
"""
import os
import re
from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.services.dataset_service import DOCUMENT_DIR, get_dataset_record

DEFAULT_EMBEDDING_MODEL = os.getenv(
    "PULSEOS_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
SEMANTIC_RETRIEVAL_ENABLED = os.getenv("PULSEOS_SEMANTIC_SEARCH", "true").lower() not in {
    "0", "false", "no", "off"
}


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


@lru_cache(maxsize=1)
def _load_embedding_model(model_name=DEFAULT_EMBEDDING_MODEL):
    """Load one small sentence-transformer model and reuse it for this process."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, device="cpu")


def _semantic_scores(question, chunks):
    """Return cosine scores, or raise so the caller can use lexical fallback."""
    model = _load_embedding_model()
    embeddings = model.encode(
        chunks + [question],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=16,
    )
    return embeddings[:-1] @ embeddings[-1]


def _tfidf_scores(question, chunks):
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=12000,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(chunks + [question])
    return cosine_similarity(matrix[-1], matrix[:-1]).ravel()


def _rank_chunks(question, chunks):
    """Prefer semantic similarity; preserve a deterministic TF-IDF fallback."""
    semantic_error = None
    if SEMANTIC_RETRIEVAL_ENABLED:
        try:
            return _semantic_scores(question, chunks), "semantic"
        except Exception as exc:  # optional dependency/model/cache/network failures
            semantic_error = exc

    try:
        return _tfidf_scores(question, chunks), "tfidf"
    except ValueError:
        if semantic_error is not None:
            return None, "unavailable"
        return None, "tfidf"


def retrieve_document_evidence(question, top_k=5):
    """Retrieve passages from the active document with semantic/lexical ranking."""
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

    scores, retrieval_mode = _rank_chunks(question, chunks)
    if scores is None:
        return {
            "status": "no_match",
            "passages": [],
            "message": "The question and document do not contain enough searchable terms.",
        }

    ranked = sorted(enumerate(scores), key=lambda item: (-float(item[1]), item[0]))
    broad_document_question = bool(re.search(
        r"\b(summar(?:y|ise|ize)|overview|describe this document|what is in this document|key points)\b",
        question,
        re.IGNORECASE,
    ))
    selected = [(index, float(score)) for index, score in ranked if score > 0][
        :max(1, min(int(top_k), 8))
    ]
    # Broad summary requests may have no query terms in common with the source.
    # Return opening chunks as explicitly unranked overview evidence in that case.
    if not selected and broad_document_question:
        selected = [(index, 0.0) for index in range(min(len(chunks), max(1, min(int(top_k), 8))))]

    # Preserve the existing heuristic for CV experience-section requests.
    experience_question = bool(re.search(
        r"\b(internship|intern|responsibilit(?:y|ies)|duties|employment history|previous role)\b",
        question,
        re.IGNORECASE,
    ))
    if not selected and experience_question:
        section_pattern = re.compile(
            r"(?im)^\s*(?:#{1,3}\s*)?(?:(?:professional|work)\s+)?experience\s*:?\s*$"
        )
        section_indices = []
        heading_positions = [
            index for index, chunk in enumerate(chunks)
            if section_pattern.search(chunk)
        ]
        if heading_positions:
            for heading_index in heading_positions:
                section_indices.append(heading_index)
                for index in range(heading_index + 1, len(chunks)):
                    if re.search(
                        r"(?im)^\s*(?:#{1,3}\s*)?(?:education|projects|skills|certifications|summary|objective)\s*:?\s*$",
                        chunks[index],
                    ):
                        break
                    section_indices.append(index)
        else:
            section_indices = [
                index for index, chunk in enumerate(chunks)
                if re.search(r"(?i)\b(business analyst intern|internship|intern)\b", chunk)
            ]
        section_indices = list(dict.fromkeys(section_indices))
        selected = [(index, 0.0) for index in section_indices[:max(1, min(int(top_k), 8))]]

    passages = []
    for index, score in selected:
        passages.append({
            "document_id": record["id"],
            "document_name": record["original_filename"],
            "chunk_index": index + 1,
            "similarity": round(score, 4),
            "text": chunks[index],
            "locator": f"Chunk {index + 1}",
            "page": None,
        })

    method_label = (
        "semantic embeddings (all-MiniLM-L6-v2)"
        if retrieval_mode == "semantic"
        else "TF-IDF unigram/bigram cosine"
    )
    fallback_note = (
        ["The optional semantic model was unavailable; TF-IDF lexical retrieval was used."]
        if SEMANTIC_RETRIEVAL_ENABLED and retrieval_mode == "tfidf"
        else []
    )
    return {
        "status": "ready" if passages else "no_match",
        "document_name": record["original_filename"],
        "passages": passages,
        "retrieval_mode": retrieval_mode,
        "methodology": (
            f"Local {method_label} over overlapping text chunks. Similarity ranks relevance; "
            "it is not a confidence or factuality score."
        ),
        "limitations": [
            "Answers are extractive: relevant source lines are selected verbatim; no generative language model paraphrases or invents content.",
            "PDF page-level offsets are not retained by the current document extraction pipeline; citations identify chunk numbers instead.",
            "Scanned PDFs without an embedded text layer are not searchable because OCR is not enabled.",
            "Only the currently selected Documents source is searched.",
            "The first semantic-model load may download model weights; subsequent loads are cached locally.",
        ] + fallback_note,
    }


def synthesize_document_answer(question, passages, max_sentences=6):
    """Create a transparent extractive answer from retrieved source text.

    Semantic ranking is also used to select relevant source lines. The returned
    lines remain verbatim and retain their chunk-level citations.
    """
    if not passages:
        return None

    lines = []
    for passage in passages:
        for raw_line in passage.get("text", "").splitlines():
            line = re.sub(r"^\s*(?:[•*\-]|\d+[.)])\s*", "", raw_line).strip()
            if len(line) >= 1:
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
        r"\b(education|experience|work experience|projects|skills|certifications|summary|objective|internship|intern|responsibilit(?:y|ies)|duties|employment history)\b",
        question,
        re.IGNORECASE,
    )
    selected = []
    if section_match:
        target = section_match.group(1).lower()
        if target in {"internship", "intern", "responsibility", "responsibilities", "duties", "employment history"}:
            target = "experience"
        heading_pattern = re.compile(
            r"^\s*(?:#{1,3}\s*)?(?:(?:professional|work)\s+)?"
            + re.escape(target) + r"\s*:?\s*$",
            re.IGNORECASE,
        )
        heading_index = next(
            (i for i, item in enumerate(lines) if heading_pattern.match(item["text"])),
            None,
        )
        if heading_index is not None:
            stop_heading = re.compile(
                r"^\s*(?:#{1,3}\s*)?(education|experience|work experience|projects|skills|certifications|summary|objective)\s*:?\s*$",
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
            scores, _mode = _rank_chunks(question, [item["text"] for item in candidates])
            if scores is not None:
                ranked = sorted(
                    range(len(candidates)),
                    key=lambda index: (-float(scores[index]), index),
                )
                selected_indices = [index for index in ranked if scores[index] > 0][:max_sentences]
                selected = [candidates[index] for index in sorted(selected_indices)]
        except Exception:
            selected = []

    if not selected:
        fallback = passages[0]
        fallback_text = fallback.get("text", "").strip()
        try:
            retrieval_score = float(fallback.get("similarity", 0))
        except (TypeError, ValueError):
            retrieval_score = 0.0

        broad_document_question = bool(re.search(
            r"\b(summar(?:y|ise|ize)|overview|describe this document|what is in this document|key points)\b",
            question,
            re.IGNORECASE,
        ))
        if not fallback_text or (retrieval_score <= 0 and not broad_document_question):
            return {
                "status": "insufficient_evidence",
                "text": "I couldn't find document text with enough relevance to answer this question.",
                "citations": [],
                "method": "extractive",
            }

        return {
            "status": "ready",
            "text": fallback_text,
            "citations": [{
                "document_name": fallback.get("document_name", "Selected document"),
                "chunk_index": fallback.get("chunk_index"),
                "locator": fallback.get("locator", f"Chunk {fallback.get('chunk_index', '?')}"),
            }],
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
