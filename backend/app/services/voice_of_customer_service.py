import re
from collections import defaultdict

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from app.services.dataset_service import UPLOAD_DIR, get_dataset_record
from app.services.workspace_data_context import current_workspace_data


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

# Transparent keyword rules give themes readable product-language labels.
# Each review is assigned to its strongest matching theme only.
TOPIC_RULES = [
    {
        "key": "payments",
        "label": "Payments & Transactions",
        "terms": {"payment", "payments", "paid", "pay", "transaction", "transactions", "money", "deducted", "refund", "refunded", "gateway", "upi", "card"},
        "recommendation": "Review payment-gateway errors, transaction status handling and refund or reversal communication.",
    },
    {
        "key": "app_stability",
        "label": "App Stability & Crashes",
        "terms": {"crash", "crashes", "crashed", "crashing", "crashes", "bug", "bugs", "freeze", "freezes", "freezing", "restart", "technical"},
        "recommendation": "Reproduce crash scenarios, inspect device and app-version logs, and prioritise fixes for high-impact failures.",
    },
    {
        "key": "customer_support",
        "label": "Customer Support",
        "terms": {"support", "customer", "agent", "agents", "help", "response", "respond", "reply", "replies", "service", "contact"},
        "recommendation": "Audit support response times, unresolved ticket categories and escalation paths.",
    },
    {
        "key": "delivery",
        "label": "Delivery & Fulfilment",
        "terms": {"delivery", "delivered", "deliver", "late", "delay", "delayed", "order", "orders", "courier", "shipping"},
        "recommendation": "Inspect fulfilment delays by location and communicate more accurate delivery updates.",
    },
    {
        "key": "performance",
        "label": "App Performance & Speed",
        "terms": {"slow", "loading", "load", "lag", "laggy", "speed", "performance", "hang", "hanging"},
        "recommendation": "Measure screen-load times and API latency, then investigate the slowest user journeys.",
    },
    {
        "key": "usability",
        "label": "Usability & Navigation",
        "terms": {"confusing", "difficult", "navigation", "navigate", "interface", "design", "button", "screen", "layout", "search"},
        "recommendation": "Review the affected journey with usability tests and simplify confusing screens or navigation steps.",
    },
    {
        "key": "pricing",
        "label": "Pricing & Charges",
        "terms": {"price", "pricing", "expensive", "cost", "charge", "charges", "fee", "fees", "overpriced"},
        "recommendation": "Check price transparency, unexpected charges and how fees are explained before checkout.",
    },
]


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

    if score == 0:
        if rating <= 2:
            return "Negative"
        if rating >= 4:
            return "Positive"
        return "Neutral"
    return "Positive" if score > 0 else "Negative"


def _classify_topic(text):
    tokens = set(re.findall(r"[a-z']+", str(text).lower()))
    matches = []
    for rule in TOPIC_RULES:
        overlap = tokens.intersection(rule["terms"])
        if overlap:
            matches.append((len(overlap), rule))
    if not matches:
        return {
            "key": "general",
            "label": "General Product Experience",
            "recommendation": "Review this feedback alongside related sessions and support records to identify the affected product journey.",
        }
    # Stable order breaks ties consistently.
    matches.sort(key=lambda item: item[0], reverse=True)
    return matches[0][1]


def _extract_keywords(documents):
    if not documents:
        return []
    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=40,
            min_df=1,
            token_pattern=r"(?u)\\b[a-zA-Z][a-zA-Z]+\\b",
        )
        matrix = vectorizer.fit_transform(documents)
        terms = vectorizer.get_feature_names_out()
        scores = matrix.mean(axis=0).A1
        indices = scores.argsort()[::-1]
        return [str(terms[index]) for index in indices if scores[index] > 0][:5]
    except ValueError:
        return []


def _build_topics(negative_df, total_negative):
    grouped = defaultdict(list)
    for _, record in negative_df.iterrows():
        rule = _classify_topic(record["review_text"])
        grouped[rule["key"]].append((record, rule))

    topics = []
    for entries in grouped.values():
        records = [entry[0] for entry in entries]
        rule = entries[0][1]
        count = len(records)
        average_rating = round(sum(float(record["rating"]) for record in records) / count, 2)
        severity_score = ((5 - average_rating) / 4) * 100
        frequency_share = (count / max(total_negative, 1)) * 100
        priority_score = round((0.6 * severity_score) + (0.4 * frequency_share))
        priority = "High attention" if priority_score >= 70 else "Moderate attention" if priority_score >= 45 else "Monitor"

        if count == 1:
            evidence_level = "Single report — validate before generalising"
        elif count < 5:
            evidence_level = "Early signal — more feedback needed"
        else:
            evidence_level = "Repeated feedback"

        documents = [str(record["review_text"]) for record in records]
        evidence = [
            {
                "rating": int(record["rating"]),
                "review_text": str(record["review_text"])[:300],
            }
            for record in records[:5]
        ]
        topics.append({
            "key": rule["key"],
            "label": rule["label"],
            "keywords": _extract_keywords(documents),
            "review_count": count,
            "average_rating": average_rating,
            "priority_score": priority_score,
            "priority": priority,
            "evidence_level": evidence_level,
            "recommendation": rule["recommendation"],
            "evidence": evidence,
        })

    return sorted(topics, key=lambda topic: (topic["priority_score"], topic["review_count"]), reverse=True)


def calculate_voice_of_customer():
    workspace = current_workspace_data()
    if workspace is not None:
        item = workspace.get("reviews")
        if not item:
            raise ValueError("No customer reviews dataset has been uploaded.")
        row = item["record"]
        df = item["dataframe"].copy()
    else:
        row = get_dataset_record("reviews")
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
    df = df[df["review_text"].str.strip().ne("")].copy()

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
    topics = _build_topics(negative, len(negative))

    evidence = [
        {
            "rating": int(record["rating"]),
            "review_text": str(record["review_text"])[:300],
            "sentiment": str(record["sentiment"]),
        }
        for _, record in negative.head(10).iterrows()
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
            "topics": "Negative reviews are assigned to readable themes using explicit keyword rules. TF-IDF extracts representative terms within each theme.",
            "prioritisation": "Priority score combines review severity (60%) and share of negative reviews (40%). It is a heuristic for triage, not a statistical risk estimate.",
        },
    }
