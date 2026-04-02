from __future__ import annotations

from typing import List, Dict

import pandas as pd
import matplotlib.pyplot as plt

from app.config import OUTPUT_DIR, MATPLOTLIB_STYLE, ensure_directories
from app.scraper import Post

plt.style.use(MATPLOTLIB_STYLE)


def posts_to_dataframe(posts: List[Post]) -> pd.DataFrame:
    df = pd.DataFrame(
        [{
            "post_id": p.post_id,
            "username": p.username,
            "text": p.text,
            "timestamp": p.timestamp,
        } for p in posts]
    )
    if df.empty:
        return df
    df["date"] = df["timestamp"].dt.date
    df["hour"] = df["timestamp"].dt.hour
    df["weekday"] = df["timestamp"].dt.day_name()
    df["month"] = df["timestamp"].dt.to_period("M")
    return df


def posting_summary(df: pd.DataFrame) -> Dict[str, object]:
    if df.empty:
        return {
            "total_posts": 0,
            "first_post": None,
            "last_post": None,
            "days_covered": 0,
            "mean_posts_per_day": 0.0,
            "median_posts_per_day": 0.0,
            "busiest_hour": None,
            "busiest_hour_count": 0,
        }
    total_posts = len(df)
    first_post = df["timestamp"].min()
    last_post = df["timestamp"].max()
    days_covered = (last_post.date() - first_post.date()).days + 1
    per_day = df.groupby("date")["post_id"].count()
    mean_posts_per_day = float(per_day.mean())
    median_posts_per_day = float(per_day.median())
    per_hour = df.groupby("hour")["post_id"].count()
    busiest_hour = int(per_hour.idxmax())
    busiest_hour_count = int(per_hour.max())
    return {
        "total_posts": total_posts,
        "first_post": first_post,
        "last_post": last_post,
        "days_covered": days_covered,
        "mean_posts_per_day": mean_posts_per_day,
        "median_posts_per_day": median_posts_per_day,
        "busiest_hour": busiest_hour,
        "busiest_hour_count": busiest_hour_count,
    }


def hourly_heatmap(df: pd.DataFrame, username: str) -> str:
    ensure_directories()
    if df.empty:
        path = OUTPUT_DIR / f"{username}_heatmap_empty.png"
        plt.figure()
        plt.text(0.5, 0.5, "No data", ha="center", va="center")
        plt.axis("off")
        plt.savefig(path, bbox_inches="tight")
        plt.close()
        return str(path)
    pivot = df.pivot_table(
        index="weekday",
        columns="hour",
        values="post_id",
        aggfunc="count",
        fill_value=0,
    )
    order = ["Monday", "Tuesday", "Wednesday", "Thursday",
             "Friday", "Saturday", "Sunday"]
    pivot = pivot.reindex(order)
    plt.figure(figsize=(10, 4))
    plt.imshow(pivot, aspect="auto")
    plt.xticks(range(24), range(24))
    plt.yticks(range(len(pivot.index)), pivot.index)
    plt.xlabel("Hour of day")
    plt.ylabel("Weekday")
    plt.colorbar(label="Number of posts")
    plt.title(f"Posting heatmap for @{username}")
    plt.tight_layout()
    path = OUTPUT_DIR / f"{username}_hourly_heatmap.png"
    plt.savefig(path)
    plt.close()
    return str(path)


def monthly_activity_chart(df: pd.DataFrame, username: str) -> str:
    ensure_directories()
    if df.empty:
        path = OUTPUT_DIR / f"{username}_monthly_empty.png"
        plt.figure()
        plt.text(0.5, 0.5, "No data", ha="center", va="center")
        plt.axis("off")
        plt.savefig(path, bbox_inches="tight")
        plt.close()
        return str(path)
    per_month = df.groupby("month")["post_id"].count()
    per_month.index = per_month.index.astype(str)
    plt.figure(figsize=(10, 4))
    per_month.plot(kind="bar")
    plt.ylabel("Number of posts")
    plt.title(f"Monthly activity for @{username}")
    plt.tight_layout()
    path = OUTPUT_DIR / f"{username}_monthly_activity.png"
    plt.savefig(path)
    plt.close()
    return str(path)
