from __future__ import annotations  # Import necessary module or component

import os  # Import necessary module or component
from typing import Optional, Tuple  # Import necessary module or component

import exifread  # Import necessary module or component
import cv2  # Import necessary module or component
from PIL import Image  # Import necessary module or component
import pytesseract  # Import necessary module or component

from app.config import IMAGE_DIR  # Import necessary module or component


def image_path_for(username: str, filename: str) -> str:  # Define function image_path_for
    return str(IMAGE_DIR / username / filename)  # Return value from function


def extract_exif_gps(path: str) -> Optional[Tuple[float, float]]:  # Define function extract_exif_gps
    if not os.path.exists(path):  # Check conditional statement
        return None  # Return value from function
    with open(path, "rb") as f:  # Use context manager
        tags = exifread.process_file(f, details=False)  # Assign value to tags
    lat = tags.get("GPS GPSLatitude")  # Assign value to lat
    lat_ref = tags.get("GPS GPSLatitudeRef")  # Assign value to lat_ref
    lon = tags.get("GPS GPSLongitude")  # Assign value to lon
    lon_ref = tags.get("GPS GPSLongitudeRef")  # Assign value to lon_ref
    if not (lat and lat_ref and lon and lon_ref):  # Check conditional statement
        return None  # Return value from function

    def dms_to_decimal(dms, ref):  # Define function dms_to_decimal
        d, m, s = [x.num / x.den for x in dms.values]  # Close bracket/parenthesis
        dec = d + (m / 60.0) + (s / 3600.0)  # Assign value to dec
        if ref.values[0] in ["S", "W"]:  # Check conditional statement
            dec = -dec  # Assign value to dec
        return dec  # Return value from function

    lat_val = dms_to_decimal(lat, lat_ref)  # Assign value to lat_val
    lon_val = dms_to_decimal(lon, lon_ref)  # Assign value to lon_val
    return lat_val, lon_val  # Return value from function


def extract_text_from_image(path: str) -> str:  # Define function extract_text_from_image
    if not os.path.exists(path):  # Check conditional statement
        return ""  # Return value from function
    img = cv2.imread(path)  # Assign value to img
    if img is None:  # Check conditional statement
        return ""  # Return value from function
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # Assign value to gray
    _, thresh = cv2.threshold(  # Execute statement or expression
        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU  # Execute statement or expression
    )  # Close bracket/parenthesis
    pil_img = Image.fromarray(thresh)  # Assign value to pil_img
    text = pytesseract.image_to_string(pil_img, lang="eng")  # Assign value to text
    return text  # Return value from function
