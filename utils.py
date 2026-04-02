import re
import json
import logging
from typing import Any, Optional, Union, List
import pandas as pd

logger = logging.getLogger(__name__)

NaTType = type(pd.NaT)

def best_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Return the first matching column name from candidates (case-insensitive)."""
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols_lower:
            return cols_lower[cand.lower()]
    return None

def to_datetime_safe(x: Any) -> Union[pd.Timestamp, NaTType]:
    """Parse timestamps robustly (unix seconds/ms OR ISO strings). Always UTC."""
    if x is None or pd.isna(x):
        return pd.NaT

    if isinstance(x, (int, float)):
        try:
            xi = int(x)
            if xi > 10_000_000_000:
                return pd.to_datetime(xi, unit="ms", utc=True, errors="coerce")
            return pd.to_datetime(xi, unit="s", utc=True, errors="coerce")
        except (ValueError, OverflowError, TypeError) as e:
            logger.debug(f"Failed to parse numeric timestamp {x}: {e}")
            return pd.NaT

    s = str(x).strip()
    if not s:
        return pd.NaT

    if re.fullmatch(r"\d{10,13}", s):
        try:
            xi = int(s)
            if xi > 10_000_000_000:
                return pd.to_datetime(xi, unit="ms", utc=True, errors="coerce")
            return pd.to_datetime(xi, unit="s", utc=True, errors="coerce")
        except (ValueError, OverflowError) as e:
            logger.debug(f"Failed to parse string numeric timestamp {s}: {e}")
            return pd.NaT

    return pd.to_datetime(s, utc=True, errors="coerce")

def safe_json_loads(s: str) -> Optional[Any]:
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        logger.debug(f"JSON decode failed for string: {e}")
        return None

def extract_tagged_users(cell: Any) -> List[str]:
    """Extract tagged usernames from list/dict/json-string or comma/space string."""
    if cell is None or (not isinstance(cell, (list, dict)) and pd.isna(cell)):
        return []

    if isinstance(cell, list):
        out = []
        for item in cell:
            if isinstance(item, str):
                out.append(item.strip().lstrip("@"))
            elif isinstance(item, dict):
                username = item.get("username") or item.get("user", {}).get("username")
                if isinstance(username, str):
                    out.append(username.strip().lstrip("@"))
        return sorted({x for x in out if x})

    if isinstance(cell, dict):
        if "taggedUsers" in cell:
            return extract_tagged_users(cell.get("taggedUsers"))
        if "users" in cell:
            return extract_tagged_users(cell.get("users"))
        if isinstance(cell.get("username"), str):
            return [cell["username"].strip().lstrip("@")]
        return []

    s = str(cell).strip()
    if not s:
        return []

    if s.startswith("[") or s.startswith("{"):
        obj = safe_json_loads(s)
        if obj is not None:
            return extract_tagged_users(obj)

    parts = re.split(r"[,\s]+", s)
    cleaned = [p.strip().lstrip("@") for p in parts if p.strip()]
    return sorted({x for x in cleaned if x})