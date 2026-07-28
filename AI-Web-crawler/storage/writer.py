import json
import os
from datetime import datetime, timezone

from config import settings


def save_result(url: str, data: dict) -> str:
    os.makedirs(settings.output_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(settings.output_dir, f"{timestamp}.json")
    payload = {"url": url, "scraped_at": timestamp, **data}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path
