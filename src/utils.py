import re  # Import necessary module or component
import json  # Import necessary module or component
import logging  # Import necessary module or component
from typing import Any, Optional, Union, List  # Import necessary module or component
import pandas as pd  # Import necessary module or component

logger = logging.getLogger(__name__)  # Assign value to logger

NaTType = type(pd.NaT)  # Assign value to NaTType

def best_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:  # Define function best_col
    """Return the first matching column name from candidates (case-insensitive)."""
    cols_lower = {c.lower(): c for c in df.columns}  # Assign value to cols_lower
    for cand in candidates:  # Iterate in a loop
        if cand.lower() in cols_lower:  # Check conditional statement
            return cols_lower[cand.lower()]  # Return value from function
    return None  # Return value from function

def to_datetime_safe(x: Any) -> Union[pd.Timestamp, NaTType]:  # Define function to_datetime_safe
    """Parse timestamps robustly (unix seconds/ms OR ISO strings). Always UTC."""
    if x is None or pd.isna(x):  # Check conditional statement
        return pd.NaT  # Return value from function

    if isinstance(x, (int, float)):  # Check conditional statement
        try:  # Start of try block for exception handling
            xi = int(x)  # Assign value to xi
            if xi > 10_000_000_000:  # Check conditional statement
                return pd.to_datetime(xi, unit="ms", utc=True, errors="coerce")  # Return value from function
            return pd.to_datetime(xi, unit="s", utc=True, errors="coerce")  # Return value from function
        except (ValueError, OverflowError, TypeError) as e:  # Handle specific exceptions
            logger.debug(f"Failed to parse numeric timestamp {x}: {e}")  # Close bracket/parenthesis
            return pd.NaT  # Return value from function

    s = str(x).strip()  # Assign value to s
    if not s:  # Check conditional statement
        return pd.NaT  # Return value from function

    if re.fullmatch(r"\d{10,13}", s):  # Check conditional statement
        try:  # Start of try block for exception handling
            xi = int(s)  # Assign value to xi
            if xi > 10_000_000_000:  # Check conditional statement
                return pd.to_datetime(xi, unit="ms", utc=True, errors="coerce")  # Return value from function
            return pd.to_datetime(xi, unit="s", utc=True, errors="coerce")  # Return value from function
        except (ValueError, OverflowError) as e:  # Handle specific exceptions
            logger.debug(f"Failed to parse string numeric timestamp {s}: {e}")  # Close bracket/parenthesis
            return pd.NaT  # Return value from function

    return pd.to_datetime(s, utc=True, errors="coerce")  # Return value from function

def safe_json_loads(s: str) -> Optional[Any]:  # Define function safe_json_loads
    try:  # Start of try block for exception handling
        return json.loads(s)  # Return value from function
    except json.JSONDecodeError as e:  # Handle specific exceptions
        logger.debug(f"JSON decode failed for string: {e}")  # Close bracket/parenthesis
        return None  # Return value from function

def extract_tagged_users(cell: Any) -> List[str]:  # Define function extract_tagged_users
    """Extract tagged usernames from list/dict/json-string or comma/space string."""
    if cell is None or (not isinstance(cell, (list, dict)) and pd.isna(cell)):  # Check conditional statement
        return []  # Return value from function

    if isinstance(cell, list):  # Check conditional statement
        out = []  # Assign value to out
        for item in cell:  # Iterate in a loop
            if isinstance(item, str):  # Check conditional statement
                out.append(item.strip().lstrip("@"))  # Close bracket/parenthesis
            elif isinstance(item, dict):  # Check alternative condition
                username = item.get("username") or item.get("user", {}).get("username")  # Assign value to username
                if isinstance(username, str):  # Check conditional statement
                    out.append(username.strip().lstrip("@"))  # Close bracket/parenthesis
        return sorted({x for x in out if x})  # Return value from function

    if isinstance(cell, dict):  # Check conditional statement
        if "taggedUsers" in cell:  # Check conditional statement
            return extract_tagged_users(cell.get("taggedUsers"))  # Return value from function
        if "users" in cell:  # Check conditional statement
            return extract_tagged_users(cell.get("users"))  # Return value from function
        if isinstance(cell.get("username"), str):  # Check conditional statement
            return [cell["username"].strip().lstrip("@")]  # Return value from function
        return []  # Return value from function

    s = str(cell).strip()  # Assign value to s
    if not s:  # Check conditional statement
        return []  # Return value from function

    if s.startswith("[") or s.startswith("{"):  # Check conditional statement
        obj = safe_json_loads(s)  # Assign value to obj
        if obj is not None:  # Check conditional statement
            return extract_tagged_users(obj)  # Return value from function

    parts = re.split(r"[,\s]+", s)  # Assign value to parts
    cleaned = [p.strip().lstrip("@") for p in parts if p.strip()]  # Assign value to cleaned
    return sorted({x for x in cleaned if x})  # Return value from function
