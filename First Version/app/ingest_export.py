import json  # Import necessary module or component
import os  # Import necessary module or component
from dataclasses import dataclass  # Import necessary module or component
from datetime import datetime  # Import necessary module or component
from typing import List, Optional, Union  # Import necessary module or component

import pandas as pd  # Import necessary module or component

from app.config import DATA_DIR, ensure_directories  # Import necessary module or component
from app.scraper import parse_timestamp, extract_username_from_profile_url  # Import necessary module or component


@dataclass  # Apply decorator
class RawPost:  # Define class RawPost
    source_index: int  # Execute statement or expression
    raw: dict  # Execute statement or expression

    def get_field(self, candidates: List[str]) -> Optional[Union[str, int, float]]:  # Define function get_field
        for key in candidates:  # Iterate in a loop
            if key in self.raw and self.raw[key] not in (None, ""):  # Check conditional statement
                return self.raw[key]  # Return value from function
        return None  # Return value from function


def load_json_list(path: str) -> List[RawPost]:  # Define function load_json_list
    with open(path, "r", encoding="utf-8") as f:  # Use context manager
        data = json.load(f)  # Assign value to data
    if isinstance(data, dict):  # Check conditional statement
        if "media" in data and isinstance(data["media"], list):  # Check conditional statement
            data = data["media"]  # Assign value to data
        elif "posts" in data and isinstance(data["posts"], list):  # Check alternative condition
            data = data["posts"]  # Assign value to data
        else:  # Execute if preceding conditions are false
            raise ValueError("JSON root is an object; expected keys 'media' or 'posts'")  # Raise an exception
    if not isinstance(data, list):  # Check conditional statement
        raise ValueError("JSON root is not a list")  # Raise an exception
    items: List[RawPost] = []  # Close bracket/parenthesis
    for idx, obj in enumerate(data):  # Iterate in a loop
        if isinstance(obj, dict):  # Check conditional statement
            items.append(RawPost(source_index=idx, raw=obj))  # Close bracket/parenthesis
    return items  # Return value from function


def infer_caption(rp: RawPost) -> str:  # Define function infer_caption
    value = rp.get_field(["caption", "title", "text", "description"])  # Assign value to value
    if value is None:  # Check conditional statement
        return ""  # Return value from function
    return str(value)  # Return value from function


def infer_timestamp(rp: RawPost) -> datetime:  # Define function infer_timestamp
    value = rp.get_field(  # Assign value to value
        [  # Execute statement or expression
            "timestamp",  # Execute statement or expression
            "taken_at",  # Execute statement or expression
            "taken_at_utc",  # Execute statement or expression
            "creation_time",  # Execute statement or expression
            "created_at",  # Execute statement or expression
            "date",  # Execute statement or expression
        ]  # Close bracket/parenthesis
    )  # Close bracket/parenthesis
    if value is None:  # Check conditional statement
        raise ValueError("No timestamp field found")  # Raise an exception
    return parse_timestamp(value)  # Return value from function


def infer_id(rp: RawPost) -> str:  # Define function infer_id
    value = rp.get_field(["id", "media_id", "pk", "identifier"])  # Assign value to value
    if value is None:  # Check conditional statement
        value = f"raw_{rp.source_index}"  # Assign value to value
    return str(value)  # Return value from function


def infer_image_filename(rp: RawPost) -> str:  # Define function infer_image_filename
    value = rp.get_field(  # Assign value to value
        ["image_filename", "image_file", "file_name", "filename", "media_path"]  # Close bracket/parenthesis
    )  # Close bracket/parenthesis
    if value is None:  # Check conditional statement
        return ""  # Return value from function
    return str(value)  # Return value from function


def create_dataframe(raw_posts: List[RawPost], username: str) -> pd.DataFrame:  # Define function create_dataframe
    rows = []  # Assign value to rows
    for rp in raw_posts:  # Iterate in a loop
        try:  # Start of try block for exception handling
            pid = infer_id(rp)  # Assign value to pid
            caption = infer_caption(rp)  # Assign value to caption
            ts = infer_timestamp(rp)  # Assign value to ts
            img_file = infer_image_filename(rp)  # Assign value to img_file
            rows.append(  # Execute statement or expression
                {  # Execute statement or expression
                    "id": pid,  # Execute statement or expression
                    "username": username,  # Execute statement or expression
                    "caption": caption,  # Execute statement or expression
                    "timestamp": ts.isoformat(),  # Execute statement or expression
                    "image_filename": img_file,  # Execute statement or expression
                }  # Close bracket/parenthesis
            )  # Close bracket/parenthesis
        except Exception as exc:  # Handle specific exceptions
            print("Skipping item", rp.source_index, "error:", exc)  # Output information to console
    df = pd.DataFrame(rows)  # Assign value to df
    return df  # Return value from function


def save_dataframe_to_csv(df: pd.DataFrame, username: str) -> str:  # Define function save_dataframe_to_csv
    ensure_directories()  # Call function ensure_directories
    path = DATA_DIR / f"{username}_posts.csv"  # Assign value to path
    df = df.sort_values("timestamp")  # Assign value to df
    df.to_csv(path, index=False, encoding="utf-8")  # Close bracket/parenthesis
    return str(path)  # Return value from function


def prompt_profile_url() -> str:  # Define function prompt_profile_url
    url = input("Enter Instagram profile URL (for this export): ").strip()  # Assign value to url
    if not url:  # Check conditional statement
        raise ValueError("No URL entered")  # Raise an exception
    return url  # Return value from function


def prompt_username_from_url(url: str) -> str:  # Define function prompt_username_from_url
    username = extract_username_from_profile_url(url)  # Assign value to username
    if not username:  # Check conditional statement
        raise ValueError("Could not extract username from URL")  # Raise an exception
    return username  # Return value from function


def prompt_export_path() -> str:  # Define function prompt_export_path
    path = input("Enter path to Instagram export JSON file: ").strip()  # Assign value to path
    if not path:  # Check conditional statement
        raise ValueError("No path entered")  # Raise an exception
    if not os.path.exists(path):  # Check conditional statement
        raise FileNotFoundError(path)  # Raise an exception
    return path  # Return value from function


def main():  # Define function main
    url = prompt_profile_url()  # Assign value to url
    username = prompt_username_from_url(url)  # Assign value to username
    print("Detected username:", username)  # Output information to console
    path = prompt_export_path()  # Assign value to path
    print("Loading JSON from:", path)  # Output information to console
    raw_posts = load_json_list(path)  # Assign value to raw_posts
    print("Items in JSON:", len(raw_posts))  # Output information to console
    df = create_dataframe(raw_posts, username)  # Assign value to df
    if df.empty:  # Check conditional statement
        print("No valid posts extracted from JSON.")  # Output information to console
        return  # Return value from function
    csv_path = save_dataframe_to_csv(df, username)  # Assign value to csv_path
    print("Saved CSV:", csv_path)  # Output information to console
    print("Now you can run analysis for this profile in main.py or visualiser.py.")  # Output information to console


if __name__ == "__main__":  # Check conditional statement
    main()  # Call function main
