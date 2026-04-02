from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List

from app.scraper import Post


@dataclass
class TimeWindow:
    start: date
    end: date


def last_n_days(days: int) -> TimeWindow:
    today = date.today()
    start = today - timedelta(days=days - 1)
    return TimeWindow(start=start, end=today)


def full_window(posts: List[Post]) -> TimeWindow:
    if not posts:
        today = date.today()
        return TimeWindow(start=today, end=today)
    first = min(p.timestamp.date() for p in posts)
    last = max(p.timestamp.date() for p in posts)
    return TimeWindow(start=first, end=last)


def filter_posts(posts: List[Post], window: TimeWindow) -> List[Post]:
    out: List[Post] = []
    for p in posts:
        d = p.timestamp.date()
        if window.start <= d <= window.end:
            out.append(p)
    return out
