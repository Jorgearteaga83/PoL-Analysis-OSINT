from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Protocol, Union
import logging

import pandas as pd

LOGGER = logging.getLogger(__name__)
if not LOGGER.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] scraper: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)


@dataclass
class Post:
    post_id: str
    username: str
    text: str
    timestamp: datetime
    image_urls: List[str]
    image_filenames: List[str]

    def has_text(self) -> bool:
        return bool(self.text and self.text.strip())

    def has_images(self) -> bool:
        return bool(self.image_urls or self.image_filenames)


def extract_username_from_profile_url(url: str) -> str:
    if not url:
        return ""
    url = url.split("?", 1)[0].strip()
    url = url.rstrip("/")
    parts = url.split("/")
    if not parts:
        return ""
    candidate = parts[-1]
    if not candidate:
        return ""
    return candidate


def parse_timestamp(value: Union[str, datetime]) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        raise ValueError("Empty timestamp string")
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return pd.to_datetime(text).to_pydatetime()


class PostSource(Protocol):
    def load_posts(self, username: str) -> List[Post]:
        ...


class CSVPostSource:
    def __init__(self, base_dir: str = "data"):
        self.base_dir = base_dir

    def _resolve_path(self, username: str) -> str:
        filename = f"{username}_posts.csv"
        path = os.path.join(self.base_dir, filename)
        LOGGER.debug("Resolved CSV path for %s -> %s", username, path)
        return path

    def load_posts(self, username: str) -> List[Post]:
        path = self._resolve_path(username)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"CSV file not found for username '{username}': {path}"
            )
        LOGGER.info("Loading posts for @%s from %s", username, path)
        df = pd.read_csv(path)
        colmap = {c.lower(): c for c in df.columns}
        id_col = colmap.get("id", colmap.get("post_id"))
        text_col = (
            colmap.get("caption")
            or colmap.get("text")
            or colmap.get("content")
        )
        ts_col = colmap.get("timestamp")
        img_url_col = (
            colmap.get("image_url")
            or colmap.get("imageurl")
            or colmap.get("img_url")
        )
        img_urls_col = colmap.get("image_urls")
        img_file_col = (
            colmap.get("image_file")
            or colmap.get("image_filename")
            or colmap.get("filename")
        )
        missing = [name for name, col in
                   [("id", id_col), ("caption/text", text_col), ("timestamp", ts_col)]
                   if col is None]
        if missing:
            raise ValueError(
                f"CSV for '{username}' is missing required columns: {', '.join(missing)}"
            )
        posts: List[Post] = []
        for idx, row in df.iterrows():
            try:
                post_id = str(row[id_col])
                text = "" if pd.isna(row[text_col]) else str(row[text_col])
                ts_value = row[ts_col]
                ts = parse_timestamp(ts_value)
                image_urls: List[str] = []
                image_filenames: List[str] = []
                if img_url_col and not pd.isna(row[img_url_col]):
                    image_urls.append(str(row[img_url_col]))
                if img_urls_col and not pd.isna(row[img_urls_col]):
                    raw = str(row[img_urls_col])
                    image_urls.extend(self._split_listish_field(raw))
                if img_file_col and not pd.isna(row[img_file_col]):
                    image_filenames.append(str(row[img_file_col]))
                posts.append(
                    Post(
                        post_id=post_id,
                        username=username,
                        text=text,
                        timestamp=ts,
                        image_urls=image_urls,
                        image_filenames=image_filenames,
                    )
                )
            except Exception as exc:
                LOGGER.warning(
                    "Failed to parse row %s for username @%s: %s", idx, username, exc
                )
        LOGGER.info("Loaded %d posts for @%s", len(posts), username)
        return posts

    @staticmethod
    def _split_listish_field(raw: str) -> List[str]:
        raw = raw.strip()
        if not raw:
            return []
        if raw.startswith("[") and raw.endswith("]"):
            import json
            try:
                val = json.loads(raw)
                if isinstance(val, list):
                    return [str(x).strip() for x in val if str(x).strip()]
            except json.JSONDecodeError:
                pass
        parts = []
        for token in raw.replace(",", ";").split(";"):
            token = token.strip()
            if token:
                parts.append(token)
        return parts


class InstagramAPISource:
    def __init__(self, access_token: str):
        self.access_token = access_token

    def load_posts(self, username: str) -> List[Post]:
        raise NotImplementedError(
            "InstagramAPISource.load_posts is not implemented."
        )


class ScraperConfig:
    def __init__(self, prefer_api: bool = False):
        self.prefer_api = prefer_api


class Scraper:
    def __init__(
        self,
        csv_source: Optional[PostSource] = None,
        api_source: Optional[PostSource] = None,
        config: Optional[ScraperConfig] = None,
    ):
        self.csv_source = csv_source or CSVPostSource()
        self.api_source = api_source
        self.config = config or ScraperConfig()

    def get_posts_for_profile_url(self, profile_url: str) -> List[Post]:
        username = extract_username_from_profile_url(profile_url)
        if not username:
            raise ValueError(f"Could not extract username from URL: {profile_url!r}")
        return self.get_posts_for_username(username)

    def get_posts_for_username(self, username: str) -> List[Post]:
        username = username.strip()
        if not username:
            raise ValueError("Empty username")
        LOGGER.info("Resolving posts for @%s", username)
        if self.config.prefer_api and self.api_source is not None:
            try:
                LOGGER.info("Attempting to load posts via API source...")
                posts = self.api_source.load_posts(username)
                if posts:
                    return posts
                LOGGER.info("API source returned no posts; falling back to CSV.")
            except NotImplementedError:
                LOGGER.warning("API source not implemented; falling back to CSV.")
            except Exception as exc:
                LOGGER.warning("API source failed for @%s: %s", username, exc)
        return self.csv_source.load_posts(username)


_default_scraper: Optional[Scraper] = None


def _get_default_scraper() -> Scraper:
    global _default_scraper
    if _default_scraper is None:
        _default_scraper = Scraper()
    return _default_scraper


def get_posts_for_profile(profile_url: str) -> List[Post]:
    scraper = _get_default_scraper()
    return scraper.get_posts_for_profile_url(profile_url)
