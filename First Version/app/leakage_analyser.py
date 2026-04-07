from __future__ import annotations  # Import necessary module or component

from dataclasses import dataclass  # Import necessary module or component
from typing import List, Dict, Any  # Import necessary module or component

from app.scraper import Post  # Import necessary module or component
from app.exif_analyser import image_path_for, extract_exif_gps, extract_text_from_image  # Import necessary module or component


@dataclass  # Apply decorator
class ImageLeak:  # Define class ImageLeak
    post_id: str  # Execute statement or expression
    username: str  # Execute statement or expression
    image_filename: str  # Execute statement or expression
    gps_lat: float | None  # Execute statement or expression
    gps_lon: float | None  # Execute statement or expression
    text: str  # Execute statement or expression


def analyse_image_leaks(posts: List[Post]) -> List[ImageLeak]:  # Define function analyse_image_leaks
    leaks: List[ImageLeak] = []  # Close bracket/parenthesis
    for p in posts:  # Iterate in a loop
        if not getattr(p, "image_filenames", None):  # Check conditional statement
            continue  # Skip to next loop iteration
        for fname in p.image_filenames:  # Iterate in a loop
            try:  # Start of try block for exception handling
                path = image_path_for(p.username, fname)  # Assign value to path
            except Exception:  # Handle specific exceptions
                leaks.append(  # Execute statement or expression
                    ImageLeak(  # Call function ImageLeak
                        post_id=p.post_id,  # Assign value to post_id
                        username=p.username,  # Assign value to username
                        image_filename=fname,  # Assign value to image_filename
                        gps_lat=None,  # Assign value to gps_lat
                        gps_lon=None,  # Assign value to gps_lon
                        text="",  # Assign value to text
                    )  # Close bracket/parenthesis
                )  # Close bracket/parenthesis
                continue  # Skip to next loop iteration
            try:  # Start of try block for exception handling
                gps = extract_exif_gps(path)  # Assign value to gps
            except Exception:  # Handle specific exceptions
                gps = None  # Assign value to gps
            try:  # Start of try block for exception handling
                text = extract_text_from_image(path)  # Assign value to text
            except Exception:  # Handle specific exceptions
                text = ""  # Assign value to text
            gps_lat = gps[0] if gps else None  # Assign value to gps_lat
            gps_lon = gps[1] if gps else None  # Assign value to gps_lon
            leaks.append(  # Execute statement or expression
                ImageLeak(  # Call function ImageLeak
                    post_id=p.post_id,  # Assign value to post_id
                    username=p.username,  # Assign value to username
                    image_filename=fname,  # Assign value to image_filename
                    gps_lat=gps_lat,  # Assign value to gps_lat
                    gps_lon=gps_lon,  # Assign value to gps_lon
                    text=text or "",  # Assign value to text
                )  # Close bracket/parenthesis
            )  # Close bracket/parenthesis
    return leaks  # Return value from function


def leakage_summary(leaks: List[ImageLeak]) -> Dict[str, Any]:  # Define function leakage_summary
    total = len(leaks)  # Assign value to total
    gps_count = 0  # Assign value to gps_count
    text_count = 0  # Assign value to text_count
    for l in leaks:  # Iterate in a loop
        if l.gps_lat is not None and l.gps_lon is not None:  # Check conditional statement
            gps_count += 1  # Assign value to gps_count
        if l.text and l.text.strip():  # Check conditional statement
            text_count += 1  # Assign value to text_count
    return {  # Return value from function
        "total_images": total,  # Execute statement or expression
        "images_with_gps": gps_count,  # Execute statement or expression
        "images_with_text": text_count,  # Execute statement or expression
    }  # Close bracket/parenthesis
