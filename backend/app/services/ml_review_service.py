import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score

from app.services.dataset_service import UPLOAD_DIR, get_dataset_record
from app.services.workspace_data_context import current_workspace_data


def cluster_review_themes(n_clusters=4):
    """Cluster review text with TF-IDF and KMeans; ratings are descriptive metadata."""
    if not 2 <= n_clusters <= 8:
        raise ValueError("n_clusters must be between 2 and 8.")

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
    df["review_text"] = df["review_text"].fillna("").astype(str).str.strip()
    df = df.dropna(subset=["rating"])
    df = df[df["rating"].between(1, 5) & df["review_text"].ne("")].copy()
    if len(df) < 3:
        raise ValueError("At least 3 valid, non-empty reviews are required for clustering.")

    # Exact duplicate text is still retained as separate review volume, but
    # the number of clusters is capped by the number of distinct documents.
    unique_documents = df["review_text"].str.lower().nunique()
    actual_clusters = min(n_clusters, unique_documents)
    if actual_clusters < 2:
        raise ValueError("At least 2 distinct review texts are required for clustering.")

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=2000,
        min_df=1,
        sublinear_tf=True,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]+\b",
    )
    try:
        matrix = vectorizer.fit_transform(df["review_text"])
    except ValueError as exc:
        raise ValueError("Review text does not contain enough meaningful words to cluster.") from exc

    model = KMeans(n_clusters=actual_clusters, random_state=42, n_init=10)
    labels = model.fit_predict(matrix)
    terms = vectorizer.get_feature_names_out()

    clusters = []
    for cluster_id in sorted(set(int(label) for label in labels)):
        positions = [index for index, label in enumerate(labels) if int(label) == cluster_id]
        group = df.iloc[positions]
        term_indices = model.cluster_centers_[cluster_id].argsort()[::-1][:6]
        keywords = [str(terms[index]) for index in term_indices if model.cluster_centers_[cluster_id][index] > 0]
        examples = [
            {
                "rating": int(record.rating),
                "review_text": str(record.review_text)[:280],
            }
            for record in group.sort_values("rating").head(4).itertuples()
        ]
        clusters.append({
            "cluster_id": cluster_id,
            "label": " · ".join(keywords[:3]) if keywords else f"Review group {cluster_id + 1}",
            "keywords": keywords,
            "review_count": int(len(group)),
            "share": round(len(group) / len(df) * 100, 1),
            "average_rating": round(float(group["rating"].mean()), 2),
            "examples": examples,
        })

    clusters.sort(key=lambda item: (-item["review_count"], item["cluster_id"]))
    unique_labels = len(set(int(label) for label in labels))
    silhouette = None
    if 1 < unique_labels < len(df):
        try:
            silhouette = round(float(silhouette_score(matrix, labels, metric="cosine")), 3)
        except ValueError:
            silhouette = None

    return {
        "status": "ready",
        "filename": row["original_filename"],
        "reviews_clustered": int(len(df)),
        "requested_clusters": int(n_clusters),
        "clusters_created": unique_labels,
        "silhouette_score": silhouette,
        "clusters": clusters,
        "methodology": (
            "Review text is converted into TF-IDF unigram/bigram vectors and grouped with "
            "KMeans (k-means++ initialisation, 10 runs, fixed random seed). Cluster labels "
            "are generated from the highest-weight terms; ratings are summarised after clustering "
            "and are not model features. This is unsupervised theme discovery, not sentiment "
            "classification or proof that a theme causes dissatisfaction."
        ),
        "limitations": [
            "Short, multilingual, sarcastic or highly ambiguous reviews may cluster poorly.",
            "Cluster labels are keyword summaries and should be reviewed by a person.",
            "Results depend on the selected cluster count and the uploaded review sample.",
        ],
    }
