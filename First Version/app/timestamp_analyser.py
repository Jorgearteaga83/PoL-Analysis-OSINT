from __future__ import annotations  # Import necessary module or component

from typing import List, Dict  # Import necessary module or component

import pandas as pd  # Import necessary module or component
import matplotlib.pyplot as plt  # Import necessary module or component

from app.config import OUTPUT_DIR, MATPLOTLIB_STYLE, ensure_directories  # Import necessary module or component
from app.scraper import Post  # Import necessary module or component

plt.style.use(MATPLOTLIB_STYLE)  # Close bracket/parenthesis


def posts_to_dataframe(posts: List[Post]) -> pd.DataFrame:  # Define function posts_to_dataframe
    df = pd.DataFrame(  # Assign value to df
        [{  # Execute statement or expression
            "post_id": p.post_id,  # Execute statement or expression
            "username": p.username,  # Execute statement or expression
            "text": p.text,  # Execute statement or expression
            "timestamp": p.timestamp,  # Execute statement or expression
        } for p in posts]  # Close bracket/parenthesis
    )  # Close bracket/parenthesis
    if df.empty:  # Check conditional statement
        return df  # Return value from function
    df["date"] = df["timestamp"].dt.date  # Assign value to df["date"]
    df["hour"] = df["timestamp"].dt.hour  # Assign value to df["hour"]
    df["weekday"] = df["timestamp"].dt.day_name()  # Assign value to df["weekday"]
    df["month"] = df["timestamp"].dt.to_period("M")  # Assign value to df["month"]
    return df  # Return value from function


def posting_summary(df: pd.DataFrame) -> Dict[str, object]:  # Define function posting_summary
    if df.empty:  # Check conditional statement
        return {  # Return value from function
            "total_posts": 0,  # Execute statement or expression
            "first_post": None,  # Execute statement or expression
            "last_post": None,  # Execute statement or expression
            "days_covered": 0,  # Execute statement or expression
            "mean_posts_per_day": 0.0,  # Execute statement or expression
            "median_posts_per_day": 0.0,  # Execute statement or expression
            "busiest_hour": None,  # Execute statement or expression
            "busiest_hour_count": 0,  # Execute statement or expression
        }  # Close bracket/parenthesis
    total_posts = len(df)  # Assign value to total_posts
    first_post = df["timestamp"].min()  # Assign value to first_post
    last_post = df["timestamp"].max()  # Assign value to last_post
    days_covered = (last_post.date() - first_post.date()).days + 1  # Assign value to days_covered
    per_day = df.groupby("date")["post_id"].count()  # Assign value to per_day
    mean_posts_per_day = float(per_day.mean())  # Assign value to mean_posts_per_day
    median_posts_per_day = float(per_day.median())  # Assign value to median_posts_per_day
    per_hour = df.groupby("hour")["post_id"].count()  # Assign value to per_hour
    busiest_hour = int(per_hour.idxmax())  # Assign value to busiest_hour
    busiest_hour_count = int(per_hour.max())  # Assign value to busiest_hour_count
    return {  # Return value from function
        "total_posts": total_posts,  # Execute statement or expression
        "first_post": first_post,  # Execute statement or expression
        "last_post": last_post,  # Execute statement or expression
        "days_covered": days_covered,  # Execute statement or expression
        "mean_posts_per_day": mean_posts_per_day,  # Execute statement or expression
        "median_posts_per_day": median_posts_per_day,  # Execute statement or expression
        "busiest_hour": busiest_hour,  # Execute statement or expression
        "busiest_hour_count": busiest_hour_count,  # Execute statement or expression
    }  # Close bracket/parenthesis


def hourly_heatmap(df: pd.DataFrame, username: str) -> str:  # Define function hourly_heatmap
    ensure_directories()  # Call function ensure_directories
    if df.empty:  # Check conditional statement
        path = OUTPUT_DIR / f"{username}_heatmap_empty.png"  # Assign value to path
        plt.figure()  # Close bracket/parenthesis
        plt.text(0.5, 0.5, "No data", ha="center", va="center")  # Close bracket/parenthesis
        plt.axis("off")  # Close bracket/parenthesis
        plt.savefig(path, bbox_inches="tight")  # Close bracket/parenthesis
        plt.close()  # Close bracket/parenthesis
        return str(path)  # Return value from function
    pivot = df.pivot_table(  # Assign value to pivot
        index="weekday",  # Assign value to index
        columns="hour",  # Assign value to columns
        values="post_id",  # Assign value to values
        aggfunc="count",  # Assign value to aggfunc
        fill_value=0,  # Assign value to fill_value
    )  # Close bracket/parenthesis
    order = ["Monday", "Tuesday", "Wednesday", "Thursday",  # Assign value to order
             "Friday", "Saturday", "Sunday"]  # Close bracket/parenthesis
    pivot = pivot.reindex(order)  # Assign value to pivot
    plt.figure(figsize=(10, 4))  # Close bracket/parenthesis
    plt.imshow(pivot, aspect="auto")  # Close bracket/parenthesis
    plt.xticks(range(24), range(24))  # Close bracket/parenthesis
    plt.yticks(range(len(pivot.index)), pivot.index)  # Close bracket/parenthesis
    plt.xlabel("Hour of day")  # Close bracket/parenthesis
    plt.ylabel("Weekday")  # Close bracket/parenthesis
    plt.colorbar(label="Number of posts")  # Close bracket/parenthesis
    plt.title(f"Posting heatmap for @{username}")  # Close bracket/parenthesis
    plt.tight_layout()  # Close bracket/parenthesis
    path = OUTPUT_DIR / f"{username}_hourly_heatmap.png"  # Assign value to path
    plt.savefig(path)  # Close bracket/parenthesis
    plt.close()  # Close bracket/parenthesis
    return str(path)  # Return value from function


def monthly_activity_chart(df: pd.DataFrame, username: str) -> str:  # Define function monthly_activity_chart
    ensure_directories()  # Call function ensure_directories
    if df.empty:  # Check conditional statement
        path = OUTPUT_DIR / f"{username}_monthly_empty.png"  # Assign value to path
        plt.figure()  # Close bracket/parenthesis
        plt.text(0.5, 0.5, "No data", ha="center", va="center")  # Close bracket/parenthesis
        plt.axis("off")  # Close bracket/parenthesis
        plt.savefig(path, bbox_inches="tight")  # Close bracket/parenthesis
        plt.close()  # Close bracket/parenthesis
        return str(path)  # Return value from function
    per_month = df.groupby("month")["post_id"].count()  # Assign value to per_month
    per_month.index = per_month.index.astype(str)  # Assign value to per_month.index
    plt.figure(figsize=(10, 4))  # Close bracket/parenthesis
    per_month.plot(kind="bar")  # Close bracket/parenthesis
    plt.ylabel("Number of posts")  # Close bracket/parenthesis
    plt.title(f"Monthly activity for @{username}")  # Close bracket/parenthesis
    plt.tight_layout()  # Close bracket/parenthesis
    path = OUTPUT_DIR / f"{username}_monthly_activity.png"  # Assign value to path
    plt.savefig(path)  # Close bracket/parenthesis
    plt.close()  # Close bracket/parenthesis
    return str(path)  # Return value from function
