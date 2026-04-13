import json
from pathlib import Path
from typing import Any, Dict, Optional


class JsonUserStore:
    """Simple JSON-backed profile store for local development."""

    def __init__(self, path: str = "data/interim/user_profiles.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def _read(self) -> Dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: Dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def upsert_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        data = self._read()
        data[profile["user_id"]] = profile
        self._write(data)
        return profile

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self._read().get(user_id)
