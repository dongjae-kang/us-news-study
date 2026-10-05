#!/usr/bin/env python3
"""Gate for one day file before push (stdlib only).

  python3 check_day.py days/2026-10-04.md --cooked ~/github/prism-us/etl/cooked/2026-10-04

Fails (exit 1) when:
  1. a 🔤 quote is not a verbatim substring of any published card for that date
  2. internal jargon / people names leak into a public page
  3. a card section lacks 카드 원문 link, 🧵 줄기, 무슨 일, 왜 오늘인가
"""
import json
import re
import sys
from pathlib import Path

LEAK = [r"\bCID\b", r"순도", r"원리 ?\d", r"\d+회차", r"\b0-[a-z]{1,2}\b", r"아인", r"Jack", r"재훈",
        r"house_contract", r"corpus3", r"조회dom", r"external_id", r"~/", r"handoff/", r"큐레이터 추천\("]
QUOTE_RE = re.compile(r"^- 🔤 \*\*.+?\*\* — .*· \"(.+)\"\s*$", re.M)
SECTION_RE = re.compile(r"^## \d+\. .+?(?=^## |\Z)", re.M | re.S)
REQUIRED = ["카드 원문 ↗", "🧵 줄기:", "**무슨 일**", "**왜 오늘인가**"]


def card_text(cooked: Path) -> str:
    parts = []
    for p in sorted(cooked.glob("topic_*.json")):
        t = json.loads(p.read_text(encoding="utf-8"))
        parts += [t.get("title") or "", t.get("subtitle") or "", t.get("body") or "",
                  json.dumps(t.get("detail") or "", ensure_ascii=False)]
    return "\n".join(parts)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("“", '"').replace("”", '"').replace("’", "'"))


def main():
    day = Path(sys.argv[1])
    cooked = Path(sys.argv[sys.argv.index("--cooked") + 1]).expanduser()
    text = day.read_text(encoding="utf-8")
    corpus = norm(card_text(cooked))
    errs = []
    if not corpus.strip():
        errs.append(f"no cards under {cooked}")
    for q in QUOTE_RE.findall(text):
        if norm(q) not in corpus:
            errs.append(f"quote not in cards: {q[:80]}")
    for pat in LEAK:
        for m in re.finditer(pat, text):
            line = text[:m.start()].count("\n") + 1
            errs.append(f"leak {pat!r} at line {line}")
    for sec in SECTION_RE.findall(text):
        head = sec.splitlines()[0]
        for r in REQUIRED:
            if r not in sec:
                errs.append(f"{head[:30]}: missing {r}")
    n_quotes = len(QUOTE_RE.findall(text))
    n_expr = len(re.findall(r"^- 🔤 ", text, re.M))
    if n_quotes != n_expr:
        errs.append(f"🔤 lines {n_expr} but parsable quotes {n_quotes} (format: - 🔤 **expr** — meaning · \"quote\")")
    for e in errs:
        print("✗", e)
    print(f"{'FAIL' if errs else 'OK'} · cards {len(SECTION_RE.findall(text))} · quotes {n_quotes} verified against {cooked.name}")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
