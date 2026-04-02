from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any

from app.scraper import Post
from app.exif_analyser import image_path_for, extract_exif_gps, extract_text_from_image


@dataclass
class ImageLeak:
    post_id: str
    username: str
    image_filename: str
    gps_lat: float | None
    gps_lon: float | None
    text: str


def analyse_image_leaks(posts: List[Post]) -> List[ImageLeak]:
    leaks: List[ImageLeak] = []
    for p in posts:
        if not getattr(p, "image_filenames", None):
            continue
        for fname in p.image_filenames:
            try:
                path = image_path_for(p.username, fname)
            except Exception:
                leaks.append(
                    ImageLeak(
                        post_id=p.post_id,
                        username=p.username,
                        image_filename=fname,
                        gps_lat=None,
                        gps_lon=None,
                        text="",
                    )
                )
                continue
            try:
                gps = extract_exif_gps(path)
            except Exception:
                gps = None
            try:
                text = extract_text_from_image(path)
            except Exception:
                text = ""
            gps_lat = gps[0] if gps else None
            gps_lon = gps[1] if gps else None
            leaks.append(
                ImageLeak(
                    post_id=p.post_id,
                    username=p.username,
                    image_filename=fname,
                    gps_lat=gps_lat,
                    gps_lon=gps_lon,
                    text=text or "",
                )
            )
    return leaks


def leakage_summary(leaks: List[ImageLeak]) -> Dict[str, Any]:
    total = len(leaks)
    gps_count = 0
    text_count = 0
    for l in leaks:
        if l.gps_lat is not None and l.gps_lon is not None:
            gps_count += 1
        if l.text and l.text.strip():
            text_count += 1
    return {
        "total_images": total,
        "images_with_gps": gps_count,
        "images_with_text": text_count,
    }
