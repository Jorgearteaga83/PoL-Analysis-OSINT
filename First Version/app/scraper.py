from __future__ import annotations  # Import necessary module or component

import os  # Import necessary module or component
from dataclasses import dataclass  # Import necessary module or component
from datetime import datetime  # Import necessary module or component
from typing import List, Optional, Protocol, Union  # Import necessary module or component
import logging  # Import necessary module or component

import pandas as pd  # Import necessary module or component

LOGGER = logging.getLogger(__name__)  # Assign value to LOGGER
if not LOGGER.handlers:  # Check conditional statement
    handler = logging.StreamHandler()  # Assign value to handler
    formatter = logging.Formatter(  # Assign value to formatter
        "[%(asctime)s] [%(levelname)s] scraper: %(message)s",  # Execute statement or expression
        datefmt="%Y-%m-%d %H:%M:%S",  # Assign value to datefmt
    )  # Close bracket/parenthesis
    handler.setFormatter(formatter)  # Close bracket/parenthesis
    LOGGER.addHandler(handler)  # Close bracket/parenthesis
LOGGER.setLevel(logging.INFO)  # Close bracket/parenthesis


@dataclass  # Apply decorator
class Post:  # Define class Post
    post_id: str  # Execute statement or expression
    username: str  # Execute statement or expression
    text: str  # Execute statement or expression
    timestamp: datetime  # Execute statement or expression
    image_urls: List[str]  # Close bracket/parenthesis
    image_filenames: List[str]  # Close bracket/parenthesis

    def has_text(self) -> bool:  # Define function has_text
        return bool(self.text and self.text.strip())  # Return value from function

    def has_images(self) -> bool:  # Define function has_images
        return bool(self.image_urls or self.image_filenames)  # Return value from function


def extract_username_from_profile_url(url: str) -> str:  # Define function extract_username_from_profile_url
    if not url:  # Check conditional statement
        return ""  # Return value from function
    url = url.split("?", 1)[0].strip()  # Assign value to url
    url = url.rstrip("/")  # Assign value to url
    parts = url.split("/")  # Assign value to parts
    if not parts:  # Check conditional statement
        return ""  # Return value from function
    candidate = parts[-1]  # Assign value to candidate
    if not candidate:  # Check conditional statement
        return ""  # Return value from function
    return candidate  # Return value from function


def parse_timestamp(value: Union[str, datetime]) -> datetime:  # Define function parse_timestamp
    if isinstance(value, datetime):  # Check conditional statement
        return value  # Return value from function
    text = str(value).strip()  # Assign value to text
    if not text:  # Check conditional statement
        raise ValueError("Empty timestamp string")  # Raise an exception
    formats = [  # Assign value to formats
        "%Y-%m-%dT%H:%M:%S",  # Execute statement or expression
        "%Y-%m-%d %H:%M:%S",  # Execute statement or expression
        "%Y-%m-%d",  # Execute statement or expression
        "%d/%m/%Y %H:%M",  # Execute statement or expression
        "%d/%m/%Y",  # Execute statement or expression
    ]  # Close bracket/parenthesis
    for fmt in formats:  # Iterate in a loop
        try:  # Start of try block for exception handling
            return datetime.strptime(text, fmt)  # Return value from function
        except ValueError:  # Handle specific exceptions
            continue  # Skip to next loop iteration
    return pd.to_datetime(text).to_pydatetime()  # Return value from function


class PostSource(Protocol):  # Define class PostSource
    def load_posts(self, username: str) -> List[Post]:  # Define function load_posts
        ...  # Execute statement or expression


class CSVPostSource:  # Define class CSVPostSource
    def __init__(self, base_dir: str = "data"):  # Define function __init__
        self.base_dir = base_dir  # Assign value to self.base_dir

    def _resolve_path(self, username: str) -> str:  # Define function _resolve_path
        filename = f"{username}_posts.csv"  # Assign value to filename
        path = os.path.join(self.base_dir, filename)  # Assign value to path
        LOGGER.debug("Resolved CSV path for %s -> %s", username, path)  # Close bracket/parenthesis
        return path  # Return value from function

    def load_posts(self, username: str) -> List[Post]:  # Define function load_posts
        path = self._resolve_path(username)  # Assign value to path
        if not os.path.exists(path):  # Check conditional statement
            raise FileNotFoundError(  # Raise an exception
                f"CSV file not found for username '{username}': {path}"  # Execute statement or expression
            )  # Close bracket/parenthesis
        LOGGER.info("Loading posts for @%s from %s", username, path)  # Close bracket/parenthesis
        df = pd.read_csv(path)  # Assign value to df
        colmap = {c.lower(): c for c in df.columns}  # Assign value to colmap
        id_col = colmap.get("id", colmap.get("post_id"))  # Assign value to id_col
        text_col = (  # Assign value to text_col
            colmap.get("caption")  # Close bracket/parenthesis
            or colmap.get("text")  # Close bracket/parenthesis
            or colmap.get("content")  # Close bracket/parenthesis
        )  # Close bracket/parenthesis
        ts_col = colmap.get("timestamp")  # Assign value to ts_col
        img_url_col = (  # Assign value to img_url_col
            colmap.get("image_url")  # Close bracket/parenthesis
            or colmap.get("imageurl")  # Close bracket/parenthesis
            or colmap.get("img_url")  # Close bracket/parenthesis
        )  # Close bracket/parenthesis
        img_urls_col = colmap.get("image_urls")  # Assign value to img_urls_col
        img_file_col = (  # Assign value to img_file_col
            colmap.get("image_file")  # Close bracket/parenthesis
            or colmap.get("image_filename")  # Close bracket/parenthesis
            or colmap.get("filename")  # Close bracket/parenthesis
        )  # Close bracket/parenthesis
        missing = [name for name, col in  # Assign value to missing
                   [("id", id_col), ("caption/text", text_col), ("timestamp", ts_col)]  # Close bracket/parenthesis
                   if col is None]  # Check conditional statement
        if missing:  # Check conditional statement
            raise ValueError(  # Raise an exception
                f"CSV for '{username}' is missing required columns: {', '.join(missing)}"  # Execute statement or expression
            )  # Close bracket/parenthesis
        posts: List[Post] = []  # Close bracket/parenthesis
        for idx, row in df.iterrows():  # Iterate in a loop
            try:  # Start of try block for exception handling
                post_id = str(row[id_col])  # Assign value to post_id
                text = "" if pd.isna(row[text_col]) else str(row[text_col])  # Assign value to text
                ts_value = row[ts_col]  # Assign value to ts_value
                ts = parse_timestamp(ts_value)  # Assign value to ts
                image_urls: List[str] = []  # Close bracket/parenthesis
                image_filenames: List[str] = []  # Close bracket/parenthesis
                if img_url_col and not pd.isna(row[img_url_col]):  # Check conditional statement
                    image_urls.append(str(row[img_url_col]))  # Close bracket/parenthesis
                if img_urls_col and not pd.isna(row[img_urls_col]):  # Check conditional statement
                    raw = str(row[img_urls_col])  # Assign value to raw
                    image_urls.extend(self._split_listish_field(raw))  # Close bracket/parenthesis
                if img_file_col and not pd.isna(row[img_file_col]):  # Check conditional statement
                    image_filenames.append(str(row[img_file_col]))  # Close bracket/parenthesis
                posts.append(  # Execute statement or expression
                    Post(  # Call function Post
                        post_id=post_id,  # Assign value to post_id
                        username=username,  # Assign value to username
                        text=text,  # Assign value to text
                        timestamp=ts,  # Assign value to timestamp
                        image_urls=image_urls,  # Assign value to image_urls
                        image_filenames=image_filenames,  # Assign value to image_filenames
                    )  # Close bracket/parenthesis
                )  # Close bracket/parenthesis
            except Exception as exc:  # Handle specific exceptions
                LOGGER.warning(  # Execute statement or expression
                    "Failed to parse row %s for username @%s: %s", idx, username, exc  # Execute statement or expression
                )  # Close bracket/parenthesis
        LOGGER.info("Loaded %d posts for @%s", len(posts), username)  # Close bracket/parenthesis
        return posts  # Return value from function

    @staticmethod  # Apply decorator
    def _split_listish_field(raw: str) -> List[str]:  # Define function _split_listish_field
        raw = raw.strip()  # Assign value to raw
        if not raw:  # Check conditional statement
            return []  # Return value from function
        if raw.startswith("[") and raw.endswith("]"):  # Check conditional statement
            import json  # Import necessary module or component
            try:  # Start of try block for exception handling
                val = json.loads(raw)  # Assign value to val
                if isinstance(val, list):  # Check conditional statement
                    return [str(x).strip() for x in val if str(x).strip()]  # Return value from function
            except json.JSONDecodeError:  # Handle specific exceptions
                pass  # No-op placeholder
        parts = []  # Assign value to parts
        for token in raw.replace(",", ";").split(";"):  # Iterate in a loop
            token = token.strip()  # Assign value to token
            if token:  # Check conditional statement
                parts.append(token)  # Close bracket/parenthesis
        return parts  # Return value from function


class InstagramAPISource:  # Define class InstagramAPISource
    def __init__(self, access_token: str):  # Define function __init__
        self.access_token = access_token  # Assign value to self.access_token

    def load_posts(self, username: str) -> List[Post]:  # Define function load_posts
        raise NotImplementedError(  # Raise an exception
            "InstagramAPISource.load_posts is not implemented."  # Execute statement or expression
        )  # Close bracket/parenthesis


class ScraperConfig:  # Define class ScraperConfig
    def __init__(self, prefer_api: bool = False):  # Define function __init__
        self.prefer_api = prefer_api  # Assign value to self.prefer_api


class Scraper:  # Define class Scraper
    def __init__(  # Define function __init__
        self,  # Execute statement or expression
        csv_source: Optional[PostSource] = None,  # Execute statement or expression
        api_source: Optional[PostSource] = None,  # Execute statement or expression
        config: Optional[ScraperConfig] = None,  # Execute statement or expression
    ):  # Close structure
        self.csv_source = csv_source or CSVPostSource()  # Assign value to self.csv_source
        self.api_source = api_source  # Assign value to self.api_source
        self.config = config or ScraperConfig()  # Assign value to self.config

    def get_posts_for_profile_url(self, profile_url: str) -> List[Post]:  # Define function get_posts_for_profile_url
        username = extract_username_from_profile_url(profile_url)  # Assign value to username
        if not username:  # Check conditional statement
            raise ValueError(f"Could not extract username from URL: {profile_url!r}")  # Raise an exception
        return self.get_posts_for_username(username)  # Return value from function

    def get_posts_for_username(self, username: str) -> List[Post]:  # Define function get_posts_for_username
        username = username.strip()  # Assign value to username
        if not username:  # Check conditional statement
            raise ValueError("Empty username")  # Raise an exception
        LOGGER.info("Resolving posts for @%s", username)  # Close bracket/parenthesis
        if self.config.prefer_api and self.api_source is not None:  # Check conditional statement
            try:  # Start of try block for exception handling
                LOGGER.info("Attempting to load posts via API source...")  # Close bracket/parenthesis
                posts = self.api_source.load_posts(username)  # Assign value to posts
                if posts:  # Check conditional statement
                    return posts  # Return value from function
                LOGGER.info("API source returned no posts; falling back to CSV.")  # Close bracket/parenthesis
            except NotImplementedError:  # Handle specific exceptions
                LOGGER.warning("API source not implemented; falling back to CSV.")  # Close bracket/parenthesis
            except Exception as exc:  # Handle specific exceptions
                LOGGER.warning("API source failed for @%s: %s", username, exc)  # Close bracket/parenthesis
        return self.csv_source.load_posts(username)  # Return value from function


_default_scraper: Optional[Scraper] = None  # Execute statement or expression


def _get_default_scraper() -> Scraper:  # Define function _get_default_scraper
    global _default_scraper  # Declare variable scope
    if _default_scraper is None:  # Check conditional statement
        _default_scraper = Scraper()  # Assign value to _default_scraper
    return _default_scraper  # Return value from function


def get_posts_for_profile(profile_url: str) -> List[Post]:  # Define function get_posts_for_profile
    scraper = _get_default_scraper()  # Assign value to scraper
    return scraper.get_posts_for_profile_url(profile_url)  # Return value from function
