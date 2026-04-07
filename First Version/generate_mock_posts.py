import csv  # Import necessary module or component
import json  # Import necessary module or component
import random  # Import necessary module or component
from datetime import datetime, timedelta, date  # Import necessary module or component
from pathlib import Path  # Import necessary module or component
from typing import List  # Import necessary module or component

from app.config import DATA_DIR, ensure_directories  # Import necessary module or component


def load_targets() -> List[dict]:  # Define function load_targets
    path = Path(__file__).resolve().parent / "targets.json"  # Assign value to path
    with open(path, "r", encoding="utf-8") as f:  # Use context manager
        return json.load(f)  # Return value from function


def parse_date(text: str) -> date | None:  # Define function parse_date
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):  # Iterate in a loop
        try:  # Start of try block for exception handling
            return datetime.strptime(text.strip(), fmt).date()  # Return value from function
        except Exception:  # Handle specific exceptions
            continue  # Skip to next loop iteration
    return None  # Return value from function


def random_datetime_between(start: datetime, end: datetime) -> datetime:  # Define function random_datetime_between
    delta = end - start  # Assign value to delta
    total_seconds = int(delta.total_seconds())  # Assign value to total_seconds
    if total_seconds <= 0:  # Check conditional statement
        return start  # Return value from function
    offset = random.randint(0, total_seconds)  # Assign value to offset
    return start + timedelta(seconds=offset)  # Return value from function


def make_caption(username: str, idx: int) -> str:  # Define function make_caption
    templates = [  # Assign value to templates
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
    ]  # Close bracket/parenthesis
    return random.choice(templates)  # Return value from function


def ask_int(prompt: str, default: int) -> int:  # Define function ask_int
    text = input(f"{prompt} [{default}]: ").strip()  # Assign value to text
    if not text:  # Check conditional statement
        return default  # Return value from function
    try:  # Start of try block for exception handling
        value = int(text)  # Assign value to value
        if value <= 0:  # Check conditional statement
            return default  # Return value from function
        return value  # Return value from function
    except Exception:  # Handle specific exceptions
        return default  # Return value from function


def ask_date(prompt: str, default: date) -> date:  # Define function ask_date
    text = input(f"{prompt} (YYYY-MM-DD) [{default}]: ").strip()  # Assign value to text
    if not text:  # Check conditional statement
        return default  # Return value from function
    d = parse_date(text)  # Assign value to d
    if d is None:  # Check conditional statement
        return default  # Return value from function
    return d  # Return value from function


# Define function generate_posts_for_username
# Define function generate_posts_for_username
def generate_posts_for_username(username: str, n_posts: int, start_date: date, end_date: date) -> List[dict]:
    start_dt = datetime.combine(start_date, datetime.min.time())  # Assign value to start_dt
    end_dt = datetime.combine(end_date, datetime.max.time())  # Assign value to end_dt
    posts: List[dict] = []  # Close bracket/parenthesis
    for i in range(1, n_posts + 1):  # Iterate in a loop
        ts = random_datetime_between(start_dt, end_dt)  # Assign value to ts
        timestamp = ts.strftime("%Y-%m-%dT%H:%M:%S")  # Assign value to timestamp
        caption = make_caption(username, i)  # Assign value to caption
        if random.random() < 0.7:  # Check conditional statement
            image_filename = f"img_{i:03d}.jpg"  # Assign value to image_filename
        else:  # Execute if preceding conditions are false
            image_filename = ""  # Assign value to image_filename
        posts.append(  # Execute statement or expression
            {  # Execute statement or expression
                "id": f"{username}_{i}",  # Execute statement or expression
                "username": username,  # Execute statement or expression
                "caption": caption,  # Execute statement or expression
                "timestamp": timestamp,  # Execute statement or expression
                "image_filename": image_filename,  # Execute statement or expression
            }  # Close bracket/parenthesis
        )  # Close bracket/parenthesis
    posts.sort(key=lambda r: r["timestamp"])  # Close bracket/parenthesis
    return posts  # Return value from function


def write_csv(username: str, rows: List[dict]) -> str:  # Define function write_csv
    ensure_directories()  # Call function ensure_directories
    path = DATA_DIR / f"{username}_posts.csv"  # Assign value to path
    fieldnames = ["id", "username", "caption", "timestamp", "image_filename"]  # Assign value to fieldnames
    with open(path, "w", encoding="utf-8", newline="") as f:  # Use context manager
        writer = csv.DictWriter(f, fieldnames=fieldnames)  # Assign value to writer
        writer.writeheader()  # Close bracket/parenthesis
        for r in rows:  # Iterate in a loop
            writer.writerow(r)  # Close bracket/parenthesis
    return str(path)  # Return value from function


def choose_target(targets: List[dict]) -> dict | None:  # Define function choose_target
    print("Available targets:")  # Output information to console
    for i, t in enumerate(targets, start=1):  # Iterate in a loop
        label = t.get("label") or t.get("username")  # Assign value to label
        group = t.get("group", "")  # Assign value to group
        print(f"{i}. {label} ({t.get('username')}, {group})")  # Output information to console
    choice = input("Select target by number (or 'a' for all): ").strip()  # Assign value to choice
    if choice.lower() == "a":  # Check conditional statement
        return None  # Return value from function
    if not choice.isdigit():  # Check conditional statement
        return None  # Return value from function
    idx = int(choice)  # Assign value to idx
    if idx < 1 or idx > len(targets):  # Check conditional statement
        return None  # Return value from function
    return targets[idx - 1]  # Return value from function


def main():  # Define function main
    random.seed()  # Close bracket/parenthesis
    targets = load_targets()  # Assign value to targets
    if not targets:  # Check conditional statement
        print("No targets found in targets.json")  # Output information to console
        return  # Return value from function
    selection = choose_target(targets)  # Assign value to selection
    today = date.today()  # Assign value to today
    default_start = today - timedelta(days=30)  # Assign value to default_start
    if selection is None:  # Check conditional statement
        n_posts_total = ask_int("Number of posts per target", 50)  # Assign value to n_posts_total
        start = ask_date("Start date for posts", default_start)  # Assign value to start
        end = ask_date("End date for posts", today)  # Assign value to end
        if start > end:  # Check conditional statement
            start, end = end, start  # Execute statement or expression
        for t in targets:  # Iterate in a loop
            username = t.get("username")  # Assign value to username
            if not username:  # Check conditional statement
                continue  # Skip to next loop iteration
            print(f"Generating {n_posts_total} posts for {username}...")  # Output information to console
            rows = generate_posts_for_username(username, n_posts_total, start, end)  # Assign value to rows
            out_path = write_csv(username, rows)  # Assign value to out_path
            print(f"Saved CSV for {username}: {out_path}")  # Output information to console
    else:  # Execute if preceding conditions are false
        username = selection.get("username")  # Assign value to username
        if not username:  # Check conditional statement
            print("Selected target has no username.")  # Output information to console
            return  # Return value from function
        n_posts = ask_int("Number of posts to generate", 50)  # Assign value to n_posts
        start = ask_date("Start date for posts", default_start)  # Assign value to start
        end = ask_date("End date for posts", today)  # Assign value to end
        if start > end:  # Check conditional statement
            start, end = end, start  # Execute statement or expression
        print(f"Generating {n_posts} posts for {username}...")  # Output information to console
        rows = generate_posts_for_username(username, n_posts, start, end)  # Assign value to rows
        out_path = write_csv(username, rows)  # Assign value to out_path
        print(f"Saved CSV for {username}: {out_path}")  # Output information to console


if __name__ == "__main__":  # Check conditional statement
    main()  # Call function main
