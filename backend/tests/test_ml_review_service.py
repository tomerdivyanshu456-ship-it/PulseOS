import sqlite3

import pandas as pd
import pytest

from app.services import ml_review_service


def _seed_reviews(tmp_path, monkeypatch, reviews):
    upload_dir = tmp_path / "raw"
    upload_dir.mkdir()
    db_path = tmp_path / "pulseos.db"
    stored = "reviews.csv"
    pd.DataFrame(reviews).to_csv(upload_dir / stored, index=False)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """CREATE TABLE datasets (
                id TEXT PRIMARY KEY, dataset_type TEXT NOT NULL,
                original_filename TEXT NOT NULL, stored_filename TEXT NOT NULL,
                row_count INTEGER NOT NULL, uploaded_at TEXT NOT NULL
            )"""
        )
        connection.execute(
            "INSERT INTO datasets VALUES (?, ?, ?, ?, ?, ?)",
            ("review-set", "reviews", "reviews.csv", stored, len(reviews), "2026-11-01T00:00:00+00:00"),
        )
    monkeypatch.setattr(ml_review_service, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(ml_review_service, "get_connection", lambda: sqlite3.connect(db_path))


def test_review_clustering_discovers_distinct_text_groups(tmp_path, monkeypatch):
    reviews = [
        {"review_id": str(i), "rating": rating, "review_text": text}
        for i, (rating, text) in enumerate([
            (1, "Payment failed and money was deducted from my bank account"),
            (2, "UPI payment failed but amount was deducted"),
            (1, "Refund for failed transaction is still pending"),
            (2, "Payment gateway error during checkout"),
            (1, "Application crashes every time I open the home screen"),
            (2, "App keeps crashing and freezes on startup"),
            (1, "The mobile application crashes after login"),
            (2, "App freezes and crashes when I search"),
            (4, "Delivery arrived quickly and packaging was excellent"),
            (5, "Fast delivery and friendly courier service"),
            (4, "Order was delivered early, great experience"),
            (5, "Excellent delivery service and quick shipping"),
        ])
    ]
    _seed_reviews(tmp_path, monkeypatch, reviews)

    result = ml_review_service.cluster_review_themes(n_clusters=3)

    assert result["status"] == "ready"
    assert result["reviews_clustered"] == 12
    assert result["clusters_created"] >= 2
    assert sum(cluster["review_count"] for cluster in result["clusters"]) == 12
    assert all(cluster["keywords"] for cluster in result["clusters"])
    assert result["methodology"].startswith("Review text is converted into TF-IDF")


def test_review_clustering_requires_distinct_documents(tmp_path, monkeypatch):
    reviews = [
        {"review_id": str(i), "rating": 2, "review_text": "Payment failed"}
        for i in range(4)
    ]
    _seed_reviews(tmp_path, monkeypatch, reviews)

    with pytest.raises(ValueError, match="2 distinct review texts"):
        ml_review_service.cluster_review_themes(n_clusters=3)


def test_review_clustering_validates_cluster_count():
    with pytest.raises(ValueError, match="between 2 and 8"):
        ml_review_service.cluster_review_themes(n_clusters=1)
