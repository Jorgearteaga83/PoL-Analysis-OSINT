import json  # Import necessary module or component
from dataclasses import dataclass  # Import necessary module or component
from pathlib import Path  # Import necessary module or component
from typing import List  # Import necessary module or component

from app.config import PROJECT_ROOT  # Import necessary module or component


@dataclass  # Apply decorator
class TargetAccount:  # Define class TargetAccount
    label: str  # Execute statement or expression
    username: str  # Execute statement or expression
    profile_url: str  # Execute statement or expression
    group: str  # Execute statement or expression


def load_targets() -> List[TargetAccount]:  # Define function load_targets
    path = PROJECT_ROOT / "targets.json"  # Assign value to path
    with open(path, "r", encoding="utf-8") as f:  # Use context manager
        data = json.load(f)  # Assign value to data
    items: List[TargetAccount] = []  # Close bracket/parenthesis
    for obj in data:  # Iterate in a loop
        items.append(  # Execute statement or expression
            TargetAccount(  # Call function TargetAccount
                label=str(obj.get("label", obj.get("username", ""))),  # Assign value to label
                username=str(obj.get("username", "")),  # Assign value to username
                profile_url=str(obj.get("profile_url", "")),  # Assign value to profile_url
                group=str(obj.get("group", "")),  # Assign value to group
            )  # Close bracket/parenthesis
        )  # Close bracket/parenthesis
    return items  # Return value from function
