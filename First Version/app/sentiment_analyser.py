from __future__ import annotations

from typing import List, Dict

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.scraper import Post

_analyser = SentimentIntensityAnalyzer()


def sentiment_dataframe(posts: List[Post]) -> pd.DataFrame:
    rows = []
    for p in posts:
        text = p.text or ""
        scores = _analyser.polarity_scores(text)
        rows.append(
            {
                "post_id": p.post_id,
                "timestamp": p.timestamp,
                "text": text,
                "compound": scores["compound"],
                "pos": scores["pos"],
                "neu": scores["neu"],
                "neg": scores["neg"],
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["date"] = df["timestamp"].dt.date
    return df


def daily_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return (
        df.groupby("date")["compound"]
        .mean()
        .reset_index(name="avg_compound")
        .sort_values("date")
    )


def sentiment_summary(df: pd.DataFrame) -> Dict[str, float]:
    if df.empty:
        return {
            "mean_compound": 0.0,
            "median_compound": 0.0,
            "min_compound": 0.0,
            "max_compound": 0.0,
        }
    return {
        "mean_compound": float(df["compound"].mean()),
        "median_compound": float(df["compound"].median()),
        "min_compound": float(df["compound"].min()),
        "max_compound": float(df["compound"].max()),
    }
