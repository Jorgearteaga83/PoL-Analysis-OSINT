from __future__ import annotations  # Import necessary module or component

from typing import List, Dict  # Import necessary module or component

import pandas as pd  # Import necessary module or component
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # Import necessary module or component

from app.scraper import Post  # Import necessary module or component

_analyser = SentimentIntensityAnalyzer()  # Assign value to _analyser


def sentiment_dataframe(posts: List[Post]) -> pd.DataFrame:  # Define function sentiment_dataframe
    rows = []  # Assign value to rows
    for p in posts:  # Iterate in a loop
        text = p.text or ""  # Assign value to text
        scores = _analyser.polarity_scores(text)  # Assign value to scores
        rows.append(  # Execute statement or expression
            {  # Execute statement or expression
                "post_id": p.post_id,  # Execute statement or expression
                "timestamp": p.timestamp,  # Execute statement or expression
                "text": text,  # Execute statement or expression
                "compound": scores["compound"],  # Execute statement or expression
                "pos": scores["pos"],  # Execute statement or expression
                "neu": scores["neu"],  # Execute statement or expression
                "neg": scores["neg"],  # Execute statement or expression
            }  # Close bracket/parenthesis
        )  # Close bracket/parenthesis
    df = pd.DataFrame(rows)  # Assign value to df
    if df.empty:  # Check conditional statement
        return df  # Return value from function
    df["date"] = df["timestamp"].dt.date  # Assign value to df["date"]
    return df  # Return value from function


def daily_sentiment(df: pd.DataFrame) -> pd.DataFrame:  # Define function daily_sentiment
    if df.empty:  # Check conditional statement
        return df  # Return value from function
    return (  # Return value from function
        df.groupby("date")["compound"]  # Close bracket/parenthesis
        .mean()  # Close bracket/parenthesis
        .reset_index(name="avg_compound")  # Close bracket/parenthesis
        .sort_values("date")  # Close bracket/parenthesis
    )  # Close bracket/parenthesis


def sentiment_summary(df: pd.DataFrame) -> Dict[str, float]:  # Define function sentiment_summary
    if df.empty:  # Check conditional statement
        return {  # Return value from function
            "mean_compound": 0.0,  # Execute statement or expression
            "median_compound": 0.0,  # Execute statement or expression
            "min_compound": 0.0,  # Execute statement or expression
            "max_compound": 0.0,  # Execute statement or expression
        }  # Close bracket/parenthesis
    return {  # Return value from function
        "mean_compound": float(df["compound"].mean()),  # Execute statement or expression
        "median_compound": float(df["compound"].median()),  # Execute statement or expression
        "min_compound": float(df["compound"].min()),  # Execute statement or expression
        "max_compound": float(df["compound"].max()),  # Execute statement or expression
    }  # Close bracket/parenthesis
