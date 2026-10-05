#!/usr/bin/env python3
"""days/*.md → _site/ (index · day pages · glossary · expressions · storylines).

Claude writes one days/<date>.md per day; everything else here is mechanical.
Collected markers (anywhere in a day file):
  - 📚 **term** — explanation        → glossary.html
  - 🔤 **expression** — meaning · "quote"  → expressions.html
  🧵 줄기: <name> · <chapter>          → storylines.html
"""
import html
import re
import shutil
import zlib
from pathlib import Path

import markdown

ROOT = Path(__file__).parent
OUT = ROOT / "_site"
SITE_TITLE = "미국 뉴스 공부 노트"

FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
TERM_RE = re.compile(r"^- 📚 \*\*(.+?)\*\* — (.+)$", re.M)
EXPR_RE = re.compile(r"^- 🔤 \*\*(.+?)\*\* — (.+)$", re.M)
THREAD_RE = re.compile(r"🧵 줄기: (.+?) · ([^·\n]+?)(?: · |$)", re.M)
H2_RE = re.compile(r"^## (\d+)\. (.+)$", re.M)

CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1f;--muted:#6b6b70;--line:#e4e2dc;--card:#ffffff;--accent:#2f5bd3;--chip:#f0eee8;--quote:#f5f3ee}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141416;--fg:#ececee;--muted:#9a9aa2;--line:#2c2c31;--card:#1c1c20;--accent:#8aa8ff;--chip:#26262b;--quote:#202025}}
:root[data-theme="dark"]{--bg:#141416;--fg:#ececee;--muted:#9a9aa2;--line:#2c2c31;--card:#1c1c20;--accent:#8aa8ff;--chip:#26262b;--quote:#202025}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.75 "Pretendard","Apple SD Gothic Neo","Noto Sans KR",system-ui,sans-serif;word-break:keep-all;overflow-wrap:break-word}
.wrap{max-width:760px;margin:0 auto;padding:24px 16px 80px}
nav.top{display:flex;gap:14px;flex-wrap:nowrap;white-space:nowrap;align-items:baseline;font-size:14px;padding-bottom:14px;border-bottom:1px solid var(--line);margin-bottom:28px}
nav.top a{color:var(--muted);text-decoration:none}nav.top a:hover,nav.top a.on{color:var(--accent)}
nav.top .brand{color:var(--fg);font-weight:700;margin-right:auto}
h1{font-size:28px;line-height:1.35;margin:0 0 6px}
h2{font-size:21px;line-height:1.45;margin:48px 0 8px;padding-top:20px;border-top:1px solid var(--line)}
a{color:var(--accent)}
.sub{color:var(--muted);font-size:15px;margin:0 0 24px}
blockquote{margin:20px 0;padding:14px 18px;background:var(--quote);border-left:3px solid var(--accent);border-radius:6px}
blockquote p{margin:6px 0}
ul{padding-left:20px}li{margin:6px 0}
table{width:100%;border-collapse:collapse;font-size:15px;display:block;overflow-x:auto}
th,td{border-bottom:1px solid var(--line);padding:10px 8px;text-align:left;vertical-align:top}
th{white-space:nowrap;color:var(--muted);font-weight:600}
td:first-child{min-width:150px;font-weight:600}td:nth-child(2){white-space:nowrap}
@media (max-width:640px){table,tbody,tr,td{display:block;width:100%}thead{display:none}
tr{border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:12px 0;background:var(--card)}
td{border:0;padding:2px 0;min-width:0!important;white-space:normal!important}
td:nth-child(2){color:var(--muted);font-size:14px;margin-bottom:6px}}
.daylist{list-style:none;padding:0}
.daylist>li{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:12px 0}
.daylist .d{font-weight:700;text-decoration:none;font-size:18px}
.daylist .h{margin:4px 0 8px;color:var(--fg)}
.daylist ol{margin:0;padding-left:20px;color:var(--muted);font-size:15px}
.daylist ol a{color:var(--muted);text-decoration:none}.daylist ol a:hover{color:var(--accent);text-decoration:underline}
.exlink{display:inline-block;font-size:15px;font-weight:600;margin-bottom:10px;text-decoration:none}
.pager{display:flex;justify-content:space-between;gap:12px;margin-top:56px;padding-top:18px;border-top:1px solid var(--line);font-size:15px}
.entry{padding:12px 0;border-bottom:1px solid var(--line)}
.entry b{font-size:17px}.entry .when{color:var(--muted);font-size:13px;margin-left:8px}
.entry .when a{color:var(--muted)}
.chip{display:inline-block;background:var(--chip);border-radius:20px;padding:1px 10px;font-size:13px;color:var(--muted);margin:0 4px 4px 0;text-decoration:none}
footer{margin-top:60px;color:var(--muted);font-size:13px}
"""


def page(title, body, active=""):
    links = [("index.html", "날짜별"), ("storylines.html", "이야기 줄기"), ("glossary.html", "용어집")]
    nav = "".join(
        f'<a href="{{root}}{h}"{" class=on" if h == active else ""}>{t}</a>' for h, t in links)
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style></head><body><div class="wrap">
<nav class="top"><a class="brand" href="{{root}}index.html">🗽 {SITE_TITLE}</a>{nav}</nav>
{body}
<footer><a class="exlink" href="{{root}}expressions.html">🔤 영어 표현 모음 →</a><br>📄 뉴스 자료 기반 · 🧭 Claude 배경 설명(제도·개념) · 원본 카드 = <a href="https://prism-news.org/en">PRISM</a></footer>
</div></body></html>"""


def parse_day(p):
    text = p.read_text(encoding="utf-8")
    fm, body = {}, text
    m = FM_RE.match(text)
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
        body = text[m.end():]
    date = fm.get("date", p.stem)
    return {"date": date, "weekday": fm.get("weekday", ""), "headline": fm.get("headline", ""),
            "body": body, "cards": H2_RE.findall(body)}


def card_of(body, pos):
    """Number + title of the card section containing character offset pos."""
    last = None
    for m in H2_RE.finditer(body):
        if m.start() > pos:
            break
        last = m
    return (last.group(1), last.group(2)) if last else ("", "")


def md(s):
    return markdown.markdown(s, extensions=["tables", "sane_lists", "toc"],
                             extension_configs={"toc": {"slugify": card_slug}})


def card_slug(value, separator="-"):
    """'1. 해안경비대…' → 'c1' so storylines can deep-link; other headings → 's-<n>'."""
    m = re.match(r"(\d+)\.", value)
    return f"c{m.group(1)}" if m else "s-" + str(zlib.crc32(value.encode()) % 100000)


def label(d):
    y, m, dd = d["date"].split("-")
    return f"{int(m)}월 {int(dd)}일 ({d['weekday']})"


def main():
    days = sorted((parse_day(p) for p in (ROOT / "days").glob("*.md")), key=lambda d: d["date"])
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "days").mkdir(parents=True)

    terms, exprs, threads = {}, [], {}
    for i, d in enumerate(days):
        for m in TERM_RE.finditer(d["body"]):
            terms.setdefault(m.group(1), {"desc": m.group(2), "dates": []})["dates"].append(d["date"])
        for m in EXPR_RE.finditer(d["body"]):
            exprs.append((m.group(1), m.group(2), d["date"]))
        for m in THREAD_RE.finditer(d["body"]):
            num, title = card_of(d["body"], m.start())
            threads.setdefault(m.group(1).strip(), []).append(
                (d["date"], m.group(2).strip(), num, title))

        prev = f'<a href="{days[i-1]["date"]}.html">← {label(days[i-1])}</a>' if i else "<span></span>"
        nxt = f'<a href="{days[i+1]["date"]}.html">{label(days[i+1])} →</a>' if i + 1 < len(days) else "<span></span>"
        body = (f"<h1>{label(d)} 미국 뉴스</h1><p class=sub>{html.escape(d['headline'])}</p>"
                + md(d["body"]) + f'<div class="pager">{prev}{nxt}</div>')
        (OUT / "days" / f"{d['date']}.html").write_text(
            page(f"{label(d)} · {SITE_TITLE}", body).replace("{root}", "../"), encoding="utf-8")

    def dlink(date, anchor=""):
        return f'<a href="days/{date}.html">{date[5:].replace("-", "/")}</a>'

    items = []
    for d in reversed(days):
        cards = "".join(f'<li><a href="days/{d["date"]}.html#c{n}">{html.escape(t)}</a></li>' for n, t in d["cards"])
        items.append(f'<li><a class="d" href="days/{d["date"]}.html">{label(d)}</a>'
                     f'<div class="h">{html.escape(d["headline"])}</div><ol>{cards}</ol></li>')
    intro = (f"<h1>{SITE_TITLE}</h1><p class=sub>매일 미국에서 크게 다뤄진 뉴스를 한국어로 읽고, "
             f"왜 오늘 뉴스가 됐는지 · 무엇을 왜 뺐는지 · 영어 표현까지 함께 쌓는 노트. "
             f"지금까지 {len(days)}일 · 용어 {len(terms)}개 · 표현 {len(exprs)}개.</p>")
    (OUT / "index.html").write_text(
        page(SITE_TITLE, intro + f'<ul class="daylist">{"".join(items)}</ul>', "index.html")
        .replace("{root}", ""), encoding="utf-8")

    rows = "".join(
        f'<div class="entry"><b>{html.escape(k)}</b><span class="when">'
        f'{" · ".join(dlink(x) for x in sorted(set(v["dates"])))}</span><div>{md(v["desc"])}</div></div>'
        for k, v in sorted(terms.items(), key=lambda kv: kv[0].lower()))
    (OUT / "glossary.html").write_text(
        page(f"용어집 · {SITE_TITLE}", f"<h1>용어집</h1><p class=sub>뉴스에 나온 미국 제도·개념. 날짜를 누르면 처음 나온 맥락으로 갑니다.</p>{rows}",
             "glossary.html").replace("{root}", ""), encoding="utf-8")

    rows = "".join(
        f'<div class="entry"><b>{html.escape(e)}</b><span class="when">{dlink(dt)}</span><div>{md(desc)}</div></div>'
        for e, desc, dt in sorted(exprs, key=lambda x: x[2], reverse=True))
    (OUT / "expressions.html").write_text(
        page(f"영어 표현 · {SITE_TITLE}", f"<h1>영어 표현</h1><p class=sub>카드 원문에서 고른 표현. 최근 날짜가 위입니다.</p>{rows}",
             "expressions.html").replace("{root}", ""), encoding="utf-8")

    blocks = []
    for name, eps in sorted(threads.items(), key=lambda kv: max(e[0] for e in kv[1]), reverse=True):
        lis = "".join(f'<li>{dlink(dt)} · {html.escape(ch)} — <a href="days/{dt}.html#c{n}">{html.escape(t)}</a></li>'
                      for dt, ch, n, t in sorted(eps))
        blocks.append(f'<div class="entry"><b>🧵 {html.escape(name)}</b><ul>{lis}</ul></div>')
    (OUT / "storylines.html").write_text(
        page(f"이야기 줄기 · {SITE_TITLE}", "<h1>이야기 줄기</h1><p class=sub>여러 날에 걸쳐 이어지는 사건. 최근에 움직인 줄기가 위입니다.</p>"
             + "".join(blocks), "storylines.html").replace("{root}", ""), encoding="utf-8")

    (OUT / ".nojekyll").write_text("")
    print(f"built {len(days)} day(s) · terms {len(terms)} · expressions {len(exprs)} · storylines {len(threads)} → {OUT}")


if __name__ == "__main__":
    main()
