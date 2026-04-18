import pytest
import pandas as pd
from utils import to_datetime_safe, extract_tagged_users

def test_to_datetime_safe_valid_unix_seconds():
    """
    Tests parsing a valid UNIX timestamp in seconds.

    Args:
        None

    Returns:
        None
    """
    result = to_datetime_safe(1609459200)
    assert pd.api.types.is_datetime64_any_dtype(pd.Series([result]))
    assert result.year == 2021
    assert result.month == 1

def test_to_datetime_safe_valid_unix_milliseconds():
    """
    Tests parsing a valid UNIX timestamp in milliseconds.

    Args:
        None

    Returns:
        None
    """
    result = to_datetime_safe(1609459200000)
    assert result.year == 2021

def test_to_datetime_safe_iso_string():
    """
    Tests parsing a valid ISO formatted datetime string.

    Args:
        None

    Returns:
        None
    """
    result = to_datetime_safe("2021-05-15T10:30:00Z")
    assert result.month == 5
    assert result.day == 15

def test_to_datetime_safe_invalid_input():
    """
    Tests parsing an invalid string to ensure it safely returns NaT.

    Args:
        None

    Returns:
        None
    """
    result = to_datetime_safe("invalid_date_string")
    assert pd.isna(result)

def test_extract_tagged_users():
    """
    Tests extracting tagged users from different data structures (dictionaries and strings).

    Args:
        None

    Returns:
        None
    """
    cell = [{"username": "user1"}, {"username": "user2"}]
    assert extract_tagged_users(cell) == ["user1", "user2"]

    cell_str = "@target_user, buddy123 @friend"
    assert extract_tagged_users(cell_str) == ["buddy123", "friend", "target_user"]
