import logging  # Import necessary module or component
import re  # Import necessary module or component
from pathlib import Path  # Import necessary module or component
from typing import Tuple, Optional, Any  # Import necessary module or component
import pandas as pd  # Import necessary module or component
from PIL import Image, ExifTags, UnidentifiedImageError  # Import necessary module or component

from utils import best_col, to_datetime_safe, extract_tagged_users  # Import necessary module or component

logger = logging.getLogger(__name__)  # Assign value to logger
GPSTAGS = ExifTags.GPSTAGS  # Assign value to GPSTAGS

def ratio_to_float(x: Any) -> float:  # Define function ratio_to_float
    try:  # Start of try block for exception handling
        if hasattr(x, "numerator") and hasattr(x, "denominator"):  # Check conditional statement
            return float(x.numerator) / float(x.denominator)  # Return value from function
        if isinstance(x, (tuple, list)) and len(x) == 2:  # Check conditional statement
            num, den = x  # Execute statement or expression
            return float(num) / float(den) if den else 0.0  # Return value from function
        return float(x)  # Return value from function
    except (ValueError, TypeError, ZeroDivisionError) as e:  # Handle specific exceptions
        logger.debug(f"Failed to convert EXIF ratio {x} to float: {e}")  # Close bracket/parenthesis
        return 0.0  # Return value from function

def dms_to_decimal(dms: Any, ref: str) -> Optional[float]:  # Define function dms_to_decimal
    try:  # Start of try block for exception handling
        deg = ratio_to_float(dms[0])  # Assign value to deg
        minutes = ratio_to_float(dms[1])  # Assign value to minutes
        seconds = ratio_to_float(dms[2])  # Assign value to seconds
        dec = deg + (minutes / 60.0) + (seconds / 3600.0)  # Assign value to dec
        if ref in ("S", "W"):  # Check conditional statement
            dec = -dec  # Assign value to dec
        return dec  # Return value from function
    except (IndexError, TypeError, ValueError) as e:  # Handle specific exceptions
        logger.debug(f"Failed to convert DMS {dms} to decimal: {e}")  # Close bracket/parenthesis
        return None  # Return value from function

def extract_exif(path: Path) -> Tuple[bool, bool, Optional[float], Optional[float]]:  # Define function extract_exif
    """Returns (exif_readable, gps_present, lat, lon)."""
    try:  # Start of try block for exception handling
        img = Image.open(path)  # Assign value to img
        exif = img.getexif()  # Assign value to exif
        if not exif:  # Check conditional statement
            return False, False, None, None  # Return value from function

        gps_tag = next((k for k, v in ExifTags.TAGS.items() if v == "GPSInfo"), None)  # Assign value to gps_tag
        if gps_tag is None or gps_tag not in exif:  # Check conditional statement
            return True, False, None, None  # Return value from function

        gps_info = exif[gps_tag]  # Assign value to gps_info
        if not isinstance(gps_info, dict):  # Check conditional statement
            return True, False, None, None  # Return value from function

        decoded = {GPSTAGS.get(k, k): v for k, v in gps_info.items()}  # Assign value to decoded
        lat, lon = None, None  # Execute statement or expression
        
        if "GPSLatitude" in decoded and "GPSLatitudeRef" in decoded:  # Check conditional statement
            lat = dms_to_decimal(decoded["GPSLatitude"], str(decoded["GPSLatitudeRef"]))  # Assign value to lat
        if "GPSLongitude" in decoded and "GPSLongitudeRef" in decoded:  # Check conditional statement
            lon = dms_to_decimal(decoded["GPSLongitude"], str(decoded["GPSLongitudeRef"]))  # Assign value to lon

        return True, True, lat, lon  # Return value from function
    except (UnidentifiedImageError, FileNotFoundError, IOError) as e:  # Handle specific exceptions
        logger.error(f"Image processing failed for {path}: {e}")  # Close bracket/parenthesis
        return False, False, None, None  # Return value from function

def normalize_dataset(df_raw: pd.DataFrame) -> pd.DataFrame:  # Define function normalize_dataset
    df = df_raw.copy()  # Assign value to df
    out = pd.DataFrame()  # Assign value to out

    c_post = best_col(df, ["post_id", "id", "postId", "shortCode", "shortcode"])  # Assign value to c_post
    c_user = best_col(df, ["account", "username", "ownerUsername", "owner.username"])  # Assign value to c_user
    c_time = best_col(df, ["timestamp_utc", "timestamp", "takenAtTimestamp", "createdAt"])  # Assign value to c_time
    c_caption = best_col(df, ["caption", "text", "description"])  # Assign value to c_caption
    c_url = best_col(df, ["display_url", "displayUrl", "imageUrl"])  # Assign value to c_url
    c_posturl = best_col(df, ["post_url", "url"])  # Assign value to c_posturl
    c_loc = best_col(df, ["location", "locationName", "location_name", "placeName"])  # Assign value to c_loc
    c_img = best_col(df, ["image_ref", "imagePath", "local_path"])  # Assign value to c_img

    out["post_id"] = df[c_post].fillna("") if c_post else ""  # Assign value to out["post_id"]
    out["username"] = df[c_user].fillna("unknown") if c_user else "unknown"  # Assign value to out["username"]
    out["timestamp_utc"] = df[c_time].apply(to_datetime_safe) if c_time else pd.NaT  # Assign value to out["timestamp_utc"]
    out["caption"] = df[c_caption].fillna("") if c_caption else ""  # Assign value to out["caption"]
    out["display_url"] = df[c_url].fillna("") if c_url else ""  # Assign value to out["display_url"]
    out["post_url"] = df[c_posturl].fillna("") if c_posturl else ""  # Assign value to out["post_url"]
    out["location"] = df[c_loc].fillna("") if c_loc else ""  # Assign value to out["location"]
    out["image_ref"] = df[c_img].fillna("").astype(str) if c_img else ""  # Assign value to out["image_ref"]

    # Assign value to mention_cols
    # Assign value to mention_cols
    mention_cols = [c for c in df.columns if re.search(r'.*taggedUsers.*username.*|mentions/\d+', c, re.IGNORECASE)]
    for simple_col_name in ["tagged_users", "taggedUsers", "userTags", "mentions"]:  # Iterate in a loop
        simple_col = best_col(df, [simple_col_name])  # Assign value to simple_col
        if simple_col and simple_col not in mention_cols:  # Check conditional statement
            mention_cols.append(simple_col)  # Close bracket/parenthesis

    all_entities = []  # Assign value to all_entities
    for _, row in df.iterrows():  # Iterate in a loop
        row_entities = set()  # Assign value to row_entities
        for col in mention_cols:  # Iterate in a loop
            cell_val = row[col]  # Assign value to cell_val
            if pd.notna(cell_val):  # Check conditional statement
                for user in extract_tagged_users(cell_val):  # Iterate in a loop
                    row_entities.add(user)  # Close bracket/parenthesis
        all_entities.append(sorted(list(row_entities)))  # Close bracket/parenthesis

    out["associated_entities"] = all_entities  # Assign value to out["associated_entities"]
    out["username"] = out["username"].astype(str).str.strip()  # Assign value to out["username"]
    out["post_id"] = out["post_id"].astype(str).str.strip()  # Assign value to out["post_id"]

    out = out[out["post_id"] != ""]  # Assign value to out
    out = out[out["username"] != "unknown"]  # Assign value to out
    return out.reset_index(drop=True)  # Return value from function
