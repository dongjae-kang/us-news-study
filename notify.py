#!/usr/bin/env python3
"""Phone push via ntfy when a push ADDS a days/<date>.md (runs in Actions after deploy).

Delivered at 08:00 America/New_York if the push lands overnight, otherwise immediately.
Silent no-op when NTFY_TOPIC is unset or no new day file was added.
"""
import json
import os
import re
import subprocess
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SITE = "https://dongjae-kang.github.io/us-news-study"
NY = ZoneInfo("America/New_York")


def new_days():
    if os.environ.get("FORCE_DATE"):
        return [os.environ["FORCE_DATE"]]
    before = os.environ.get("BEFORE", "")
    if not before or set(before) == {"0"}:
        return []
    out = subprocess.run(["git", "diff", "--name-only", "--diff-filter=A", before, "HEAD", "--", "days/"],
                         capture_output=True, text=True, check=True).stdout
    return sorted(re.findall(r"days/(\d{4}-\d{2}-\d{2})\.md", out))


def headline(date):
    m = re.search(r"^headline:\s*(.+)$", Path(f"days/{date}.md").read_text(encoding="utf-8"), re.M)
    return m.group(1).strip() if m else "오늘 노트가 올라왔습니다"


def main():
    topic = os.environ.get("NTFY_TOPIC")
    days = new_days()
    if not topic or not days:
        print(f"notify: skip (topic={'set' if topic else 'unset'}, new days={days})")
        return
    date = days[-1]
    now = datetime.now(NY)
    eight = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now.hour >= 22:
        eight += timedelta(days=1)
    m, d = int(date[5:7]), int(date[8:10])
    payload = {
        "topic": topic,
        "title": f"🗽 {m}/{d} 미국 뉴스 노트 올라왔어요",
        "message": headline(date),
        "click": f"{SITE}/days/{date}.html",
        "tags": ["newspaper"],
    }
    if now < eight:
        payload["delay"] = str(int(eight.timestamp()))
    req = urllib.request.Request("https://ntfy.sh", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        print(f"notify: {date} → status {r.status} · delay={payload.get('delay', 'now')}")


if __name__ == "__main__":
    main()
