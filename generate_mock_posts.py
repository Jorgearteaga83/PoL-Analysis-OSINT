import csv
import json
import random
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List

from app.config import DATA_DIR, ensure_directories


def load_targets() -> List[dict]:
    path = Path(__file__).resolve().parent / "targets.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_date(text: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except Exception:
            continue
    return None


def random_datetime_between(start: datetime, end: datetime) -> datetime:
    delta = end - start
    total_seconds = int(delta.total_seconds())
    if total_seconds <= 0:
        return start
    offset = random.randint(0, total_seconds)
    return start + timedelta(seconds=offset)


def make_caption(username: str, idx: int) -> str:
    templates = [
        f"{username} daily update #{idx}",
        f"Checking in from a new location #{idx}",
        f"Another day, another post #{idx}",
        f"Routine activity log #{idx}",
        f"Sharing a moment #{idx}",
        f"Evening post from {username} #{idx}",
        f"Morning routine #{idx}",
        f"Travel snapshot #{idx}",
        f"Random thought #{idx}",
        f"Status update #{idx}",
    ]
    return random.choice(templates)


def ask_int(prompt: str, default: int) -> int:
    text = input(f"{prompt} [{default}]: ").strip()
    if not text:
        return default
    try:
        value = int(text)
        if value <= 0:
            return default
        return value
    except Exception:
        return default


def ask_date(prompt: str, default: date) -> date:
    text = input(f"{prompt} (YYYY-MM-DD) [{default}]: ").strip()
    if not text:
        return default
    d = parse_date(text)
    if d is None:
        return default
    return d


def generate_posts_for_username(username: str, n_posts: int, start_date: date, end_date: date) -> List[dict]:
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    posts: List[dict] = []
    for i in range(1, n_posts + 1):
        ts = random_datetime_between(start_dt, end_dt)
        timestamp = ts.strftime("%Y-%m-%dT%H:%M:%S")
        caption = make_caption(username, i)
        if random.random() < 0.7:
            image_filename = f"img_{i:03d}.jpg"
        else:
            image_filename = ""
        posts.append(
            {
                "id": f"{username}_{i}",
                "username": username,
                "caption": caption,
                "timestamp": timestamp,
                "image_filename": image_filename,
            }
        )
    posts.sort(key=lambda r: r["timestamp"])
    return posts


def write_csv(username: str, rows: List[dict]) -> str:
    ensure_directories()
    path = DATA_DIR / f"{username}_posts.csv"
    fieldnames = ["id", "username", "caption", "timestamp", "image_filename"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return str(path)


def choose_target(targets: List[dict]) -> dict | None:
    print("Available targets:")
    for i, t in enumerate(targets, start=1):
        label = t.get("label") or t.get("username")
        group = t.get("group", "")
        print(f"{i}. {label} ({t.get('username')}, {group})")
    choice = input("Select target by number (or 'a' for all): ").strip()
    if choice.lower() == "a":
        return None
    if not choice.isdigit():
        return None
    idx = int(choice)
    if idx < 1 or idx > len(targets):
        return None
    return targets[idx - 1]


def main():
    random.seed()
    targets = load_targets()
    if not targets:
        print("No targets found in targets.json")
        return
    selection = choose_target(targets)
    today = date.today()
    default_start = today - timedelta(days=30)
    if selection is None:
        n_posts_total = ask_int("Number of posts per target", 50)
        start = ask_date("Start date for posts", default_start)
        end = ask_date("End date for posts", today)
        if start > end:
            start, end = end, start
        for t in targets:
            username = t.get("username")
            if not username:
                continue
            print(f"Generating {n_posts_total} posts for {username}...")
            rows = generate_posts_for_username(username, n_posts_total, start, end)
            out_path = write_csv(username, rows)
            print(f"Saved CSV for {username}: {out_path}")
    else:
        username = selection.get("username")
        if not username:
            print("Selected target has no username.")
            return
        n_posts = ask_int("Number of posts to generate", 50)
        start = ask_date("Start date for posts", default_start)
        end = ask_date("End date for posts", today)
        if start > end:
            start, end = end, start
        print(f"Generating {n_posts} posts for {username}...")
        rows = generate_posts_for_username(username, n_posts, start, end)
        out_path = write_csv(username, rows)
        print(f"Saved CSV for {username}: {out_path}")


if __name__ == "__main__":
    main()
