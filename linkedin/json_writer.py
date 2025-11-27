import json
from pathlib import Path
from typing import Any, List


class ProfileJSONWriter:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def write(self, payload: List[Any]):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open("w", encoding="utf-8") as output:
            json.dump(payload, output, ensure_ascii=False, indent=2)

