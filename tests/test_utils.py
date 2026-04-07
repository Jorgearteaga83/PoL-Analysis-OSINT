import pytest  # Import necessary module or component
import pandas as pd  # Import necessary module or component
from utils import to_datetime_safe, extract_tagged_users  # Import necessary module or component

def test_to_datetime_safe_valid_unix_seconds():  # Define function test_to_datetime_safe_valid_unix_seconds
    # 1609459200 is 2021-01-01 00:00:00 UTC
    result = to_datetime_safe(1609459200)  # Assign value to result
    assert pd.api.types.is_datetime64_any_dtype(pd.Series([result]))  # Assert a condition holds true
    assert result.year == 2021  # Assert a condition holds true
    assert result.month == 1  # Assert a condition holds true

def test_to_datetime_safe_valid_unix_milliseconds():  # Define function test_to_datetime_safe_valid_unix_milliseconds
    # 1609459200000 is 2021-01-01 00:00:00 UTC
    result = to_datetime_safe(1609459200000)  # Assign value to result
    assert result.year == 2021  # Assert a condition holds true

def test_to_datetime_safe_iso_string():  # Define function test_to_datetime_safe_iso_string
    result = to_datetime_safe("2021-05-15T10:30:00Z")  # Assign value to result
    assert result.month == 5  # Assert a condition holds true
    assert result.day == 15  # Assert a condition holds true

def test_to_datetime_safe_invalid_input():  # Define function test_to_datetime_safe_invalid_input
    result = to_datetime_safe("invalid_date_string")  # Assign value to result
    assert pd.isna(result)  # Assert a condition holds true

def test_extract_tagged_users():  # Define function test_extract_tagged_users
    # Test dictionary lists
    cell = [{"username": "user1"}, {"username": "user2"}]  # Assign value to cell
    assert extract_tagged_users(cell) == ["user1", "user2"]  # Assert a condition holds true

    # Test string splitting
    cell_str = "@target_user, buddy123 @friend"  # Assign value to cell_str
    assert extract_tagged_users(cell_str) == ["buddy123", "friend", "target_user"]  # Assert a condition holds true
