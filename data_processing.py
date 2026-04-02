import logging
import re
from pathlib import Path
from typing import Tuple, Optional, Any
import pandas as pd
from PIL import Image, ExifTags, UnidentifiedImageError

from utils import best_col, to_datetime_safe, extract_tagged_users

logger = logging.getLogger(__name__)
GPSTAGS = ExifTags.GPSTAGS

def ratio_to_float(x: Any) -> float:
    try:
        if hasattr(x, "numerator") and hasattr(x, "denominator"):
            return float(x.numerator) / float(x.denominator)
        if isinstance(x, (tuple, list)) and len(x) == 2:
            num, den = x
            return float(num) / float(den) if den else 0.0
        return float(x)
    except (ValueError, TypeError, ZeroDivisionError) as e:
        logger.debug(f"Failed to convert EXIF ratio {x} to float: {e}")
        return 0.0

def dms_to_decimal(dms: Any, ref: str) -> Optional[float]:
    try:
        deg = ratio_to_float(dms[0])
        minutes = ratio_to_float(dms[1])
        seconds = ratio_to_float(dms[2])
        dec = deg + (minutes / 60.0) + (seconds / 3600.0)
        if ref in ("S", "W"):
            dec = -dec
        return dec
    except (IndexError, TypeError, ValueError) as e:
        logger.debug(f"Failed to convert DMS {dms} to decimal: {e}")
        return None

def extract_exif(path: Path) -> Tuple[bool, bool, Optional[float], Optional[float]]:
    """Returns (exif_readable, gps_present, lat, lon)."""
    try:
        img = Image.open(path)
        exif = img.getexif()
        if not exif:
            return False, False, None, None

        gps_tag = next((k for k, v in ExifTags.TAGS.items() if v == "GPSInfo"), None)
        if gps_tag is None or gps_tag not in exif:
            return True, False, None, None

        gps_info = exif[gps_tag]
        if not isinstance(gps_info, dict):
            return True, False, None, None

        decoded = {GPSTAGS.get(k, k): v for k, v in gps_info.items()}
        lat, lon = None, None
        
        if "GPSLatitude" in decoded and "GPSLatitudeRef" in decoded:
            lat = dms_to_decimal(decoded["GPSLatitude"], str(decoded["GPSLatitudeRef"]))
        if "GPSLongitude" in decoded and "GPSLongitudeRef" in decoded:
            lon = dms_to_decimal(decoded["GPSLongitude"], str(decoded["GPSLongitudeRef"]))

        return True, True, lat, lon
    except (UnidentifiedImageError, FileNotFoundError, IOError) as e:
        logger.error(f"Image processing failed for {path}: {e}")
        return False, False, None, None

def normalize_dataset(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    out = pd.DataFrame()

    c_post = best_col(df, ["post_id", "id", "postId", "shortCode", "shortcode"])
    c_user = best_col(df, ["account", "username", "ownerUsername", "owner.username"])
    c_time = best_col(df, ["timestamp_utc", "timestamp", "takenAtTimestamp", "createdAt"])
    c_caption = best_col(df, ["caption", "text", "description"])
    c_url = best_col(df, ["display_url", "displayUrl", "imageUrl"])
    c_posturl = best_col(df, ["post_url", "url"])
    c_loc = best_col(df, ["location", "locationName", "location_name", "placeName"])
    c_img = best_col(df, ["image_ref", "imagePath", "local_path"])

    out["post_id"] = df[c_post].fillna("") if c_post else ""
    out["username"] = df[c_user].fillna("unknown") if c_user else "unknown"
    out["timestamp_utc"] = df[c_time].apply(to_datetime_safe) if c_time else pd.NaT
    out["caption"] = df[c_caption].fillna("") if c_caption else ""
    out["display_url"] = df[c_url].fillna("") if c_url else ""
    out["post_url"] = df[c_posturl].fillna("") if c_posturl else ""
    out["location"] = df[c_loc].fillna("") if c_loc else ""
    out["image_ref"] = df[c_img].fillna("").astype(str) if c_img else ""

    mention_cols = [c for c in df.columns if re.search(r'.*taggedUsers.*username.*|mentions/\d+', c, re.IGNORECASE)]
    for simple_col_name in ["tagged_users", "taggedUsers", "userTags", "mentions"]:
        simple_col = best_col(df, [simple_col_name])
        if simple_col and simple_col not in mention_cols:
            mention_cols.append(simple_col)

    all_entities = []
    for _, row in df.iterrows():
        row_entities = set()
        for col in mention_cols:
            cell_val = row[col]
            if pd.notna(cell_val):
                for user in extract_tagged_users(cell_val):
                    row_entities.add(user)
        all_entities.append(sorted(list(row_entities)))

    out["associated_entities"] = all_entities
    out["username"] = out["username"].astype(str).str.strip()
    out["post_id"] = out["post_id"].astype(str).str.strip()

    out = out[out["post_id"] != ""]
    out = out[out["username"] != "unknown"]
    return out.reset_index(drop=True)