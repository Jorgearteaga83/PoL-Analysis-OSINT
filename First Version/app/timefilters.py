from __future__ import annotations  # Import necessary module or component

from dataclasses import dataclass  # Import necessary module or component
from datetime import date, datetime, timedelta  # Import necessary module or component
from typing import List  # Import necessary module or component

from app.scraper import Post  # Import necessary module or component


@dataclass  # Apply decorator
class TimeWindow:  # Define class TimeWindow
    start: date  # Execute statement or expression
    end: date  # Execute statement or expression


def last_n_days(days: int) -> TimeWindow:  # Define function last_n_days
    today = date.today()  # Assign value to today
    start = today - timedelta(days=days - 1)  # Assign value to start
    return TimeWindow(start=start, end=today)  # Return value from function


def full_window(posts: List[Post]) -> TimeWindow:  # Define function full_window
    if not posts:  # Check conditional statement
        today = date.today()  # Assign value to today
        return TimeWindow(start=today, end=today)  # Return value from function
    first = min(p.timestamp.date() for p in posts)  # Assign value to first
    last = max(p.timestamp.date() for p in posts)  # Assign value to last
    return TimeWindow(start=first, end=last)  # Return value from function


def filter_posts(posts: List[Post], window: TimeWindow) -> List[Post]:  # Define function filter_posts
    out: List[Post] = []  # Close bracket/parenthesis
    for p in posts:  # Iterate in a loop
        d = p.timestamp.date()  # Assign value to d
        if window.start <= d <= window.end:  # Check conditional statement
            out.append(p)  # Close bracket/parenthesis
    return out  # Return value from function
