from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Optional

from model.main import ResumeProfile
from model.preferences import PreferenceVector


BASE_DIR = Path(__file__).resolve().parents[1]
STATE_PATH = BASE_DIR / "data" / "user_state.json"


class UserStorage:
    def __init__(self, path: Path = STATE_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    def _load(self) -> Dict:
        if not self.path.exists():
            return {"users": {}}
        with self.path.open(encoding="utf-8") as f:
            return json.load(f)

    def _save(self) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def save_profile(self, user_id: int, profile: ResumeProfile) -> None:
        users = self.state.setdefault("users", {})
        user_entry = users.setdefault(str(user_id), {})
        user_entry["profile"] = asdict(profile)
        self._save()

    def get_profile(self, user_id: int) -> Optional[ResumeProfile]:
        user_entry = self.state.get("users", {}).get(str(user_id))
        if not user_entry or "profile" not in user_entry:
            return None
        profile_dict = user_entry["profile"]
        return ResumeProfile(**profile_dict)

    def get_preferences(self, user_id: int) -> PreferenceVector:
        user_entry = self.state.setdefault("users", {}).setdefault(str(user_id), {})
        payload = user_entry.get("preferences", {})
        return PreferenceVector.from_payload(payload)

    def save_preferences(self, user_id: int, preferences: PreferenceVector) -> None:
        user_entry = self.state.setdefault("users", {}).setdefault(str(user_id), {})
        user_entry["preferences"] = preferences.to_payload()
        self._save()

