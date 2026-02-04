import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Union

import pandas as pd

from app.config import DATA_DIR, ensure_directories
from app.scraper import parse_timestamp, extract_username_from_profile_url


@dataclass
class RawPost:
    source_index: int
    raw: dict

    def get_field(self, candidates: List[str]) -> Optional[Union[str, int, float]]:
        for key in candidates:
            if key in self.raw and self.raw[key] not in (None, ""):
                return self.raw[key]
        return None


def load_json_list(path: str) -> List[RawPost]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        if "media" in data and isinstance(data["media"], list):
            data = data["media"]
        elif "posts" in data and isinstance(data["posts"], list):
            data = data["posts"]
        else:
            raise ValueError("JSON root is an object; expected keys 'media' or 'posts'")
    if not isinstance(data, list):
        raise ValueError("JSON root is not a list")
    items: List[RawPost] = []
    for idx, obj in enumerate(data):
        if isinstance(obj, dict):
            items.append(RawPost(source_index=idx, raw=obj))
    return items


def infer_caption(rp: RawPost) -> str:
    value = rp.get_field(["caption", "title", "text", "description"])
    if value is None:
        return ""
    return str(value)


def infer_timestamp(rp: RawPost) -> datetime:
    value = rp.get_field(
        [
            "timestamp",
            "taken_at",
            "taken_at_utc",
            "creation_time",
            "created_at",
            "date",
        ]
    )
    if value is None:
        raise ValueError("No timestamp field found")
    return parse_timestamp(value)


def infer_id(rp: RawPost) -> str:
    value = rp.get_field(["id", "media_id", "pk", "identifier"])
    if value is None:
        value = f"raw_{rp.source_index}"
    return str(value)


def infer_image_filename(rp: RawPost) -> str:
    value = rp.get_field(
        ["image_filename", "image_file", "file_name", "filename", "media_path"]
    )
    if value is None:
        return ""
    return str(value)


def create_dataframe(raw_posts: List[RawPost], username: str) -> pd.DataFrame:
    rows = []
    for rp in raw_posts:
        try:
            pid = infer_id(rp)
            caption = infer_caption(rp)
            ts = infer_timestamp(rp)
            img_file = infer_image_filename(rp)
            rows.append(
                {
                    "id": pid,
                    "username": username,
                    "caption": caption,
                    "timestamp": ts.isoformat(),
                    "image_filename": img_file,
                }
            )
        except Exception as exc:
            print("Skipping item", rp.source_index, "error:", exc)
    df = pd.DataFrame(rows)
    return df


def save_dataframe_to_csv(df: pd.DataFrame, username: str) -> str:
    ensure_directories()
    path = DATA_DIR / f"{username}_posts.csv"
    df = df.sort_values("timestamp")
    df.to_csv(path, index=False, encoding="utf-8")
    return str(path)


def prompt_profile_url() -> str:
    url = input("Enter Instagram profile URL (for this export): ").strip()
    if not url:
        raise ValueError("No URL entered")
    return url


def prompt_username_from_url(url: str) -> str:
    username = extract_username_from_profile_url(url)
    if not username:
        raise ValueError("Could not extract username from URL")
    return username


def prompt_export_path() -> str:
    path = input("Enter path to Instagram export JSON file: ").strip()
    if not path:
        raise ValueError("No path entered")
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    return path


def main():
    url = prompt_profile_url()
    username = prompt_username_from_url(url)
    print("Detected username:", username)
    path = prompt_export_path()
    print("Loading JSON from:", path)
    raw_posts = load_json_list(path)
    print("Items in JSON:", len(raw_posts))
    df = create_dataframe(raw_posts, username)
    if df.empty:
        print("No valid posts extracted from JSON.")
        return
    csv_path = save_dataframe_to_csv(df, username)
    print("Saved CSV:", csv_path)
    print("Now you can run analysis for this profile in main.py or visualiser.py.")


if __name__ == "__main__":
    main()
