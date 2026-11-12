import re

import pandas as pd
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer

from app.services.dataset_service import UPLOAD_DIR, get_connection


POSITIVE_WORDS = {
    "amazing", "awesome", "best", "easy", "excellent", "fast",
    "friendly", "good", "great", "helpful", "love", "nice",
    "perfect", "quick", "smooth", "wonderful",
}
NEGATIVE_WORDS = {
    "annoying", "bad", "broken", "crash", "crashes", "deducted",
    "delay", "difficult", "error", "failed", "failure", "frequently",
    "hate", "issue", "late", "poor", "problem", "slow", "stuck",
    "terrible", "unable", "unfortunately", "worst",
}
NEGATIONS = {"no", "not", "never", "isn't", "wasn't", "don't", "didn't", "cannot"}


def _sentiment(text, rating):
    tokens = re.findall(r"[a-z']+", str(text).lower())
    score = 0

    for index, token in enumerate(tokens):
        if token in POSITIVE_WORDS:
            value = 1
        elif token in NEGATIVE_WORDS:
            value = -1
        else:
            continue

        if any(word in NEGATIONS for word in tokens[max(0, index - 3):index]):
            value *= -1
        score += value

    # Use the customer rating as a transparent fallback when the text
    # contains no words from the lightweight sentiment lexicon.
    if score == 0:
        if rating <= 2:
            return "Negative"
        if rating >= 4:
            return "Positive"
        return "Neutral"

    if score > 0:
        return "Positive"
    if score < 0:
        return "Negative"
    return "Neutral"


def _extract_topics(negative_reviews):
    documents = [str(value).strip() for value in negative_reviews if str(value).strip()]
    if not documents:
        return []

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=80,
        min_df=1,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]+\b",
    )

    try:
        matrix = vectorizer.fit_transform(documents)
    except ValueError:
        return []

    terms = vectorizer.get_feature_names_out()
    if len(terms) == 0:
        return []

    topic_count = min(3, len(documents), len(terms))
    if topic_count == 1:
        weights = matrix.toarray()
        top_indices = weights.mean(axis=0).argsort()[::-1][:5]
        return [{
            "label": "Recurring negative feedback",
            "keywords": [str(terms[index]) for index in top_indices if weights.mean(axis=0)[index] > 0],
            "review_count": len(documents),
            "evidence": documents[0][:240],
        }]

    model = NMF(
        n_components=topic_count,
        init="nndsvda",
        random_state=42,
        max_iter=400,
    )
    document_topic = model.fit_transform(matrix)
    topics = []

    for topic_index, component in enumerate(model.components_):
        top_indices = component.argsort()[::-1][:5]
        keywords = [str(terms[index]) for index in top_indices if component[index] > 0]
        if not keywords:
            continue

        representative_index = int(document_topic[:, topic_index].argmax())
        topics.append({
            "label": " / ".join(keywords[:2]).title(),
            "keywords": keywords,
            "review_count": int((document_topic[:, topic_index] > 0).sum()),
            "evidence": documents[representative_index][:240],
        })

    return topics


def calculate_voice_of_customer():
    connection = get_connection()
    try:
        row = connection.execute(
            """
            SELECT stored_filename, original_filename, row_count
            FROM datasets
            WHERE dataset_type = ?
            ORDER BY uploaded_at DESC
            LIMIT 1
            """,
            ("reviews",),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        raise ValueError("No customer reviews dataset has been uploaded.")

    file_path = UPLOAD_DIR / row["stored_filename"]
    if not file_path.is_file():
        raise ValueError("The stored reviews dataset file is missing.")

    df = pd.read_csv(file_path)
    required = {"review_id", "rating", "review_text"}
    if not required.issubset(df.columns):
        raise ValueError("The reviews dataset is missing required columns.")

    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["review_text"] = df["review_text"].fillna("").astype(str)
    df = df.dropna(subset=["rating"])
    df = df[df["rating"].between(1, 5)].copy()

    if df.empty:
        raise ValueError("No valid customer reviews were found.")

    df["sentiment"] = df.apply(
        lambda record: _sentiment(record["review_text"], float(record["rating"])),
        axis=1,
    )

    sentiment_counts = df["sentiment"].value_counts()
    sentiment_distribution = [
        {"sentiment": label, "count": int(sentiment_counts.get(label, 0))}
        for label in ["Positive", "Neutral", "Negative"]
    ]

    rating_counts = df["rating"].round().astype(int).value_counts()
    rating_distribution = [
        {"rating": rating, "count": int(rating_counts.get(rating, 0))}
        for rating in range(1, 6)
    ]

    negative = df[df["sentiment"] == "Negative"]
    topics = _extract_topics(negative["review_text"].tolist())

    evidence = [
        {
            "rating": int(record["rating"]),
            "review_text": str(record["review_text"])[:300],
            "sentiment": str(record["sentiment"]),
        }
        for _, record in negative.head(5).iterrows()
    ]

    return {
        "data_source": "uploaded_csv",
        "filename": row["original_filename"],
        "total_reviews": int(len(df)),
        "average_rating": round(float(df["rating"].mean()), 2),
        "sentiment_distribution": sentiment_distribution,
        "rating_distribution": rating_distribution,
        "topics": topics,
        "negative_evidence": evidence,
        "methodology": {
            "sentiment": "Transparent keyword lexicon with rating-based fallback; not a trained language model.",
            "topics": "TF-IDF features grouped with non-negative matrix factorisation (NMF) over negative reviews.",
        },
    }
