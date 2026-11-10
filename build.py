#!/usr/bin/env python3
"""days/*.md → _site/ (index · day pages · glossary · expressions · storylines).

Claude writes one days/<date>.md per day; everything else here is mechanical.
Collected markers (anywhere in a day file):
  - 📚 **term** — explanation        → glossary.html
  - 🔤 **expression** — meaning · "quote"  → expressions.html
  🧵 줄기: <name> · <chapter>          → storylines.html

Reader notes (notes.html + a strip under each card once switched on): 👍/👎 and one line per card,
one line for the day's set, and a "should have been in" mark on the left-out rows. The notes live
in the reader's own browser (localStorage) and are sent nowhere; the reader takes them out with
"복사" or "파일로 저장". The strips stay hidden on day pages until notes.html has been opened once
in that browser, so a passing visitor never sees a feedback control that leads nowhere.
"""
import html
import json
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
CARD_RE = re.compile(r"^## (\d+)\. (.+?)$(.*?)(?=^## |\Z)", re.M | re.S)
XID_RE = re.compile(r"\]\(https://prism-news\.org/en/today/([^)\s]+)\)")
LEFT_OUT_RE = re.compile(r"^## 🗂[^\n]*\n(.*?)(?=^## |\Z)", re.M | re.S)
NOTES_DAYS = 14

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
.rv{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:16px 0 6px;padding:10px 12px;border:1px dashed var(--line);border-radius:10px;background:var(--card)}
.rv-l{font-size:13px;color:var(--muted);margin-right:2px;white-space:nowrap}
.rv-b{font:inherit;font-size:17px;line-height:1;min-width:44px;min-height:40px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg);cursor:pointer}
.rv-b[aria-pressed="true"]{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent);background:var(--chip)}
.rv-n{flex:1 1 200px;min-width:0;font:inherit;font-size:15px;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg)}
.rv-x{font:inherit;font-size:12px;margin:4px 0 0 0;padding:3px 9px;border:1px solid var(--line);border-radius:12px;background:var(--bg);color:var(--muted);cursor:pointer;white-space:nowrap}
.rv-x[aria-pressed="true"]{color:var(--accent);border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
.rv-b:focus-visible,.rv-x:focus-visible,.rv-n:focus-visible,.rvbar button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.rvbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:18px 0;padding:12px 14px;border:1px solid var(--line);border-radius:10px;background:var(--card);font-size:14px}
.rvbar .n{margin-right:auto;color:var(--muted)}
.rvbar button{font:inherit;font-size:14px;min-height:38px;padding:6px 14px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg);cursor:pointer}
.rvbar .msg{flex-basis:100%;color:var(--muted);font-size:13px;min-height:1em}
.rvday{margin:28px 0;padding:16px 18px;border:1px solid var(--line);border-radius:10px;background:var(--card)}
.rvday h2{margin:0 0 4px;padding:0;border:0;font-size:18px}
.rvday .rvcard{margin-top:14px;padding-top:12px;border-top:1px solid var(--line)}
.rvday .rvcard a{font-weight:600;text-decoration:none}
.rvday .rv{margin:8px 0 0;border:0;padding:0;background:none}
.rvday .rvout{margin-top:14px;padding-top:12px;border-top:1px solid var(--line);font-size:14px;color:var(--muted)}
.rvday .rvout div{margin:6px 0}
"""

# Reader notes. Plain DOM code, no dependency. Storage can be unavailable (private window); the
# page then still works for the visit and says so.
NOTES_JS = r"""
(function(){
'use strict';
var el=document.getElementById('rv-data'); if(!el) return;
var DATA=JSON.parse(el.textContent), KEY='usn-notes-v1', FLAG='usn-notes-on';
var store={}, canStore=true;
try{ store=JSON.parse(localStorage.getItem(KEY)||'{}')||{}; }catch(e){ canStore=false; store={}; }
function flagOn(){ try{ return localStorage.getItem(FLAG)==='1'; }catch(e){ return false; } }
function setFlag(on){ try{ if(on){ localStorage.setItem(FLAG,'1'); } else { localStorage.removeItem(FLAG); } }catch(e){} }
if(/[?&]notes=1(&|$)/.test(location.search)) setFlag(true);
if(DATA.mode==='notes') setFlag(true);
if(DATA.mode==='day' && !flagOn()) return;

function persist(){ try{ localStorage.setItem(KEY, JSON.stringify(store)); }catch(e){ canStore=false; } refresh(); }
function setEntry(id, base, patch){
  var e=store[id]||JSON.parse(JSON.stringify(base)), k;
  for(k in patch){ e[k]=patch[k]; }
  e.at=new Date().toISOString();
  if(!e.verdict && !e.note){ delete store[id]; } else { store[id]=e; }
  persist();
}
function make(tag, cls, text){ var n=document.createElement(tag); if(cls){ n.className=cls; } if(text){ n.textContent=text; } return n; }
function strip(id, base, label){
  var box=make('div','rv'); box.setAttribute('data-id', id);
  box.appendChild(make('span','rv-l',label));
  [['up','👍','맞다'],['down','👎','아니다']].forEach(function(x){
    var b=make('button','rv-b',x[1]); b.type='button'; b.setAttribute('data-v',x[0]);
    b.setAttribute('aria-label', label+' '+x[2]); b.setAttribute('aria-pressed','false');
    b.addEventListener('click', function(){ var cur=(store[id]||{}).verdict; setEntry(id, base, {verdict: cur===x[0]?null:x[0]}); });
    box.appendChild(b);
  });
  var inp=make('input','rv-n'); inp.type='text'; inp.maxLength=200; inp.placeholder='한 줄 메모';
  inp.setAttribute('aria-label', label+' 한 줄 메모');
  inp.addEventListener('change', function(){ setEntry(id, base, {note: inp.value.trim()}); });
  box.appendChild(inp);
  return box;
}
function outButton(date, title){
  var id=date+'|left_out|'+title, base={date:date, kind:'left_out', title:title};
  var b=make('button','rv-x','넣었어야'); b.type='button'; b.setAttribute('data-id', id);
  b.setAttribute('aria-label', title+' — 넣었어야 했다'); b.setAttribute('aria-pressed','false');
  b.addEventListener('click', function(){ var cur=(store[id]||{}).verdict; setEntry(id, base, {verdict: cur==='add'?null:'add'}); });
  return b;
}
function cardStrip(date, c){ return strip(date+'|card|'+c.xid, {date:date, kind:'card', n:c.n, xid:c.xid, title:c.title}, '이 카드'); }
function dayStrip(date){ return strip(date+'|day|set', {date:date, kind:'day'}, '이날 묶음'); }

function entries(){ return Object.keys(store).sort().map(function(id){ return store[id]; }); }
function asText(){
  var es=entries(), lines=['[US 메모 v1] '+new Date().toISOString()+' · '+es.length+'건'];
  function flat(t){ return String(t||'').replace(/\s*\|\s*/g,' / '); }
  es.forEach(function(e){ lines.push([e.date, e.kind, e.n||'', e.verdict||'', flat(e.xid||e.title), flat(e.note)].join(' | ')); });
  return lines.join('\n');
}
function say(text){ var m=document.querySelector('.rvbar .msg'); if(m){ m.textContent=text; } }
function copyText(){
  var text=asText();
  function fallback(){ var t=make('textarea'); t.value=text; t.setAttribute('readonly',''); t.style.position='fixed'; t.style.opacity='0'; document.body.appendChild(t); t.select();
    var ok=false; try{ ok=document.execCommand('copy'); }catch(e){} document.body.removeChild(t); say(ok?'복사했습니다.':'복사하지 못했습니다. 파일로 저장을 써 주세요.'); }
  if(navigator.clipboard && navigator.clipboard.writeText){ navigator.clipboard.writeText(text).then(function(){ say('복사했습니다.'); }, fallback); } else { fallback(); }
}
function saveFile(){
  var body=JSON.stringify({version:'us-notes-v1', exported_at:new Date().toISOString(), entries:entries()}, null, 1);
  var a=make('a'), d=new Date(), p=function(n){ return (n<10?'0':'')+n; };
  a.href=URL.createObjectURL(new Blob([body], {type:'application/json'}));
  a.download='us-notes-'+d.getFullYear()+p(d.getMonth()+1)+p(d.getDate())+'-'+p(d.getHours())+p(d.getMinutes())+'.json';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(function(){ URL.revokeObjectURL(a.href); }, 1000);
  say('파일로 저장했습니다: '+a.download);
}
function refresh(){
  Array.prototype.forEach.call(document.querySelectorAll('.rv'), function(box){
    var e=store[box.getAttribute('data-id')]||{};
    Array.prototype.forEach.call(box.querySelectorAll('.rv-b'), function(b){ b.setAttribute('aria-pressed', e.verdict===b.getAttribute('data-v')?'true':'false'); });
    var inp=box.querySelector('.rv-n'); if(inp && document.activeElement!==inp){ inp.value=e.note||''; }
  });
  Array.prototype.forEach.call(document.querySelectorAll('.rv-x'), function(b){ b.setAttribute('aria-pressed', (store[b.getAttribute('data-id')]||{}).verdict==='add'?'true':'false'); });
  var n=Object.keys(store).length;
  Array.prototype.forEach.call(document.querySelectorAll('.rvbar .n'), function(x){
    x.textContent=(n?'메모 '+n+'건':'아직 메모가 없습니다')+(canStore?'':' · 이 브라우저는 저장을 막아 두어, 창을 닫으면 사라집니다');
  });
}
function bar(full){
  var b=make('div','rvbar'); b.appendChild(make('span','n'));
  if(full){
    var c=make('button',null,'복사'); c.type='button'; c.addEventListener('click', copyText); b.appendChild(c);
    var f=make('button',null,'파일로 저장'); f.type='button'; f.addEventListener('click', saveFile); b.appendChild(f);
    var x=make('button',null,'모두 지우기'); x.type='button';
    x.addEventListener('click', function(){ if(x.getAttribute('data-armed')==='1'){ store={}; x.removeAttribute('data-armed'); x.textContent='모두 지우기'; persist(); say('지웠습니다.'); }
      else { x.setAttribute('data-armed','1'); x.textContent='정말 지우기'; say('한 번 더 누르면 이 브라우저의 메모를 모두 지웁니다.'); } });
    b.appendChild(x);
    var h=make('button',null,'날짜별 페이지에서 메모 칸 숨기기'); h.type='button';
    h.addEventListener('click', function(){ setFlag(false); say('숨겼습니다. 이 페이지를 다시 열면 메모 칸이 다시 보입니다.'); }); b.appendChild(h);
    b.appendChild(make('span','msg')); b.querySelector('.msg').setAttribute('role','status');
  } else {
    var a=make('a',null,'내 메모 모아보기 →'); a.href=DATA.root+'notes.html'; b.appendChild(a);
  }
  return b;
}

if(DATA.mode==='day'){
  var day=DATA.days[0];
  day.cards.forEach(function(c){
    var h=document.getElementById('c'+c.n); if(!h) return;
    var next=h.nextElementSibling; while(next && next.tagName!=='H2'){ next=next.nextElementSibling; }
    h.parentNode.insertBefore(cardStrip(day.date, c), next);
  });
  Array.prototype.forEach.call(document.querySelectorAll('h2'), function(h){
    if(h.textContent.indexOf('뺀 뉴스')<0) return;
    var t=h.nextElementSibling; while(t && t.tagName!=='TABLE' && t.tagName!=='H2'){ t=t.nextElementSibling; }
    if(!t || t.tagName!=='TABLE') return;
    Array.prototype.forEach.call(t.querySelectorAll('tbody tr'), function(tr){
      var td=tr.querySelector('td'); if(!td) return; var title=td.textContent.trim();
      td.appendChild(document.createElement('br')); td.appendChild(outButton(day.date, title));
    });
  });
  var pager=document.querySelector('.pager');
  if(pager){ pager.parentNode.insertBefore(dayStrip(day.date), pager); pager.parentNode.insertBefore(bar(false), pager); }
} else {
  var root=document.getElementById('rv-root');
  root.appendChild(bar(true));
  DATA.days.forEach(function(d){
    var sec=make('section','rvday');
    var h=make('h2'), a=make('a',null,d.label); a.href='days/'+d.date+'.html'; h.appendChild(a); sec.appendChild(h);
    sec.appendChild(make('div','sub',d.headline));
    sec.appendChild(dayStrip(d.date));
    d.cards.forEach(function(c){
      var w=make('div','rvcard'), l=make('a',null,c.n+'. '+c.title); l.href='days/'+d.date+'.html#c'+c.n;
      w.appendChild(l); w.appendChild(cardStrip(d.date, c)); sec.appendChild(w);
    });
    if(d.left_out.length){
      var o=make('div','rvout'); o.appendChild(make('div',null,'그날 뺀 뉴스'));
      d.left_out.forEach(function(t){ var row=make('div',null,t+' '); row.appendChild(outButton(d.date, t)); o.appendChild(row); });
      sec.appendChild(o);
    }
    root.appendChild(sec);
  });
  root.appendChild(bar(true));
}
refresh();
})();
"""


def notes_script(mode, days, root):
    """The data block + script for a page with note strips. `days` = parsed day dicts."""
    data = {"mode": mode, "root": root, "days": [
        {"date": d["date"], "label": label(d), "headline": d["headline"], "cards": d["notes_cards"],
         "left_out": d["left_out"]} for d in days]}
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/json" id="rv-data">{blob}</script><script>{NOTES_JS}</script>'



def page(title, body, active=""):
    links = [("index.html", "날짜별"), ("storylines.html", "이야기 줄기"), ("glossary.html", "용어집")]
    nav = "".join(
        f'<a href="{{root}}{h}"{" class=on" if h == active else ""}>{t}</a>' for h, t in links)
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style></head><body><div class="wrap">
<nav class="top"><a class="brand" href="{{root}}index.html">🗽 {SITE_TITLE}</a>{nav}</nav>
{body}
<footer><a class="exlink" href="{{root}}expressions.html">🔤 영어 표현 모음 →</a> · <a class="exlink" href="{{root}}notes.html">✍︎ 내 메모</a><br>📄 뉴스 자료 기반 · 🧭 Claude 배경 설명(제도·개념) · 원본 카드 = <a href="https://prism-news.org/en">PRISM</a></footer>
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
    notes_cards = []
    for num, title, section in CARD_RE.findall(body):
        xid = XID_RE.search(section)
        if xid:            # a card without its source link has no stable key, so it gets no strip
            notes_cards.append({"n": num, "xid": xid.group(1), "title": title.strip()})
    left_out = []
    table = LEFT_OUT_RE.search(body)
    if table:
        for row in table.group(1).splitlines():
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            if row.lstrip().startswith("|") and len(cells) >= 2 and cells[0] and not set(cells[0]) <= set("-: ") \
                    and cells[0] != "뉴스":
                left_out.append(re.sub(r"[*_`]", "", cells[0]))
    return {"date": date, "weekday": fm.get("weekday", ""), "headline": fm.get("headline", ""),
            "body": body, "cards": H2_RE.findall(body), "notes_cards": notes_cards, "left_out": left_out}


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
            page(f"{label(d)} · {SITE_TITLE}", body).replace("{root}", "../")
            .replace("</body>", notes_script("day", [d], "../") + "</body>"), encoding="utf-8")

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

    recent = list(reversed(days))[:NOTES_DAYS]
    notes_body = (f"<h1>내 메모</h1><p class=sub>최근 {len(recent)}일의 카드에 👍/👎 와 한 줄을, 그날 묶음에도 한 줄을 남깁니다. "
                  "메모는 이 브라우저에만 저장되고 어디로도 전송되지 않습니다. 가져가려면 복사하거나 파일로 저장하세요.</p>"
                  '<div id="rv-root"></div><noscript><p>메모 칸은 자바스크립트가 켜져 있어야 보입니다.</p></noscript>')
    (OUT / "notes.html").write_text(
        page(f"내 메모 · {SITE_TITLE}", notes_body, "notes.html").replace("{root}", "")
        .replace("</body>", notes_script("notes", recent, "") + "</body>"), encoding="utf-8")

    (OUT / ".nojekyll").write_text("")
    print(f"built {len(days)} day(s) · terms {len(terms)} · expressions {len(exprs)} · storylines {len(threads)} → {OUT}")


if __name__ == "__main__":
    main()
