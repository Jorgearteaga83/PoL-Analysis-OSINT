import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from app.config import PROJECT_ROOT


@dataclass
class TargetAccount:
    label: str
    username: str
    profile_url: str
    group: str


def load_targets() -> List[TargetAccount]:
    path = PROJECT_ROOT / "targets.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items: List[TargetAccount] = []
    for obj in data:
        items.append(
            TargetAccount(
                label=str(obj.get("label", obj.get("username", ""))),
                username=str(obj.get("username", "")),
                profile_url=str(obj.get("profile_url", "")),
                group=str(obj.get("group", "")),
            )
        )
    return items
