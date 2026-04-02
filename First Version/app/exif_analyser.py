from __future__ import annotations

import os
from typing import Optional, Tuple

import exifread
import cv2
from PIL import Image
import pytesseract

from app.config import IMAGE_DIR


def image_path_for(username: str, filename: str) -> str:
    return str(IMAGE_DIR / username / filename)


def extract_exif_gps(path: str) -> Optional[Tuple[float, float]]:
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        tags = exifread.process_file(f, details=False)
    lat = tags.get("GPS GPSLatitude")
    lat_ref = tags.get("GPS GPSLatitudeRef")
    lon = tags.get("GPS GPSLongitude")
    lon_ref = tags.get("GPS GPSLongitudeRef")
    if not (lat and lat_ref and lon and lon_ref):
        return None

    def dms_to_decimal(dms, ref):
        d, m, s = [x.num / x.den for x in dms.values]
        dec = d + (m / 60.0) + (s / 3600.0)
        if ref.values[0] in ["S", "W"]:
            dec = -dec
        return dec

    lat_val = dms_to_decimal(lat, lat_ref)
    lon_val = dms_to_decimal(lon, lon_ref)
    return lat_val, lon_val


def extract_text_from_image(path: str) -> str:
    if not os.path.exists(path):
        return ""
    img = cv2.imread(path)
    if img is None:
        return ""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    pil_img = Image.fromarray(thresh)
    text = pytesseract.image_to_string(pil_img, lang="eng")
    return text
