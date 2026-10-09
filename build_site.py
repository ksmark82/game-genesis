#!/usr/bin/env python3
"""md 문서를 웹문서(html)로 바꾸고, 저장소 첫 화면(index.html)을 만든다.

md 파일이 원본이다. md를 고친 뒤 이 스크립트를 다시 돌리면 html이 따라 바뀐다.
    python3 build_site.py
"""
import datetime
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# (원본 md, 만들 html, 첫 화면에 보일 이름, 한 줄 설명, 소설처럼 읽기 좋은 모양으로 할지)
DOCS = [
    ("스토리_흐름.md", "story.html", "스토리 흐름", "지금까지의 줄거리를 들른 순서대로 정리", False),
    ("떡밥_정리.md", "clues.html", "떡밥 정리", "NPC 대화에서 나온 복선, 세계관, 아직 안 풀린 의문", False),
    ("진행중인_내용.md", "todo.html", "진행 중인 내용", "놓치면 안 되는 아이템, 하다 만 일, 나중에 챙길 일", False),
    ("상점_정리.md", "shops.html", "상점 정리", "마을별 상점 물건과 값, 돈 버는 법", False),
    ("소설_서풍의_광시곡.md", "novel.html", "소설", "지금까지 진행한 이야기를 소설로", True),
]
# md가 아닌, 따로 만든 웹문서
EXTRA = [
    ("map-atlas/", "지도첩", "던전·숲·산·저택 지도 모음. 지명으로 찾기"),
    ("antaria-map.html", "안타리아 전도", "대륙 전체 지도"),
]

MARKED = "https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"
FONTS = "https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=IBM+Plex+Sans+KR:wght@400;500;600&display=swap"

# 지도첩과 같은 색과 글꼴을 쓴다
BASE_CSS = """
:root {
  --ink: #0b0f17; --panel: #121926; --line: #243149;
  --text: #e9e2d0; --muted: #95a0b5; --gold: #e2c27a; --gold-dim: #9c8556;
  --font-display: "Gowun Batang", "Nanum Myeongjo", "Batang", serif;
  --font-ui: "IBM Plex Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;
  color-scheme: dark;
}
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--ink); color: var(--text); }
body { font-family: var(--font-ui); font-size: 16px; line-height: 1.7; }
a { color: var(--gold); text-underline-offset: 3px; }
a:hover { color: #f3dca4; }
.top { position: sticky; top: 0; z-index: 5; background: rgba(11, 15, 23, .94); backdrop-filter: blur(6px); border-bottom: 1px solid var(--line); }
.top nav { max-width: 1180px; margin: 0 auto; padding: 10px 16px; display: flex; gap: 6px 16px; flex-wrap: wrap; align-items: center; font-size: 14px; }
.top nav a { color: var(--muted); text-decoration: none; white-space: nowrap; }
.top nav a:hover, .top nav a[aria-current="page"] { color: var(--gold); }
.top nav .home { font-family: var(--font-display); font-weight: 700; color: var(--text); margin-right: 8px; }
"""

DOC_CSS = """
.layout { max-width: 1180px; margin: 0 auto; padding: 24px 16px 64px; display: grid; grid-template-columns: 240px minmax(0, 1fr); gap: 32px; align-items: start; }
@media (max-width: 900px) { .layout { grid-template-columns: minmax(0, 1fr); gap: 12px; } }
.toc { position: sticky; top: 64px; max-height: calc(100vh - 80px); overflow-y: auto; font-size: 13px; border-left: 1px solid var(--line); padding-left: 12px; }
.toc summary { cursor: pointer; color: var(--muted); font-weight: 600; letter-spacing: .06em; list-style: none; margin-bottom: 6px; }
.toc ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }
.toc a { color: var(--muted); text-decoration: none; display: block; line-height: 1.4; word-break: keep-all; }
.toc a:hover, .toc a.on { color: var(--gold); }
@media (max-width: 900px) { .toc { position: static; max-height: none; border: 1px solid var(--line); border-radius: 6px; padding: 8px 12px; } }
article { min-width: 0; max-width: 78ch; word-break: keep-all; overflow-wrap: anywhere; }
article hr + h2 { border-top: 0; margin-top: 0; }
article h1 { font-family: var(--font-display); font-size: clamp(26px, 4vw, 36px); line-height: 1.25; margin: 0 0 16px; text-wrap: balance; }
article h2 { font-family: var(--font-display); font-size: 24px; line-height: 1.3; margin: 44px 0 12px; padding-top: 8px; border-top: 1px solid var(--line); scroll-margin-top: 64px; }
article h3 { font-size: 17px; margin: 28px 0 8px; color: var(--gold); scroll-margin-top: 64px; }
article p, article ul, article ol { margin: 0 0 12px; }
article ul, article ol { padding-left: 1.3em; }
article li { margin: 3px 0; }
article li > ul { margin: 4px 0 0; }
article strong { color: #fff4dc; font-weight: 600; }
article blockquote { margin: 0 0 20px; padding: 10px 14px; border-left: 3px solid var(--gold-dim); background: var(--panel); border-radius: 0 6px 6px 0; color: var(--muted); }
article blockquote p { margin: 4px 0; }
article blockquote strong { color: var(--gold); }
article hr { border: 0; border-top: 1px solid var(--line); margin: 32px 0; }
article code { font-size: .9em; background: var(--panel); border: 1px solid var(--line); border-radius: 4px; padding: 1px 5px; }
.tbl { overflow-x: auto; margin: 0 0 16px; border: 1px solid var(--line); border-radius: 6px; }
article table { border-collapse: collapse; width: 100%; font-size: 14px; }
article th, article td { padding: 8px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
article th { background: var(--panel); color: var(--gold); font-weight: 600; white-space: nowrap; }
article tr:last-child td { border-bottom: 0; }
/* 소설은 읽기 좋게: 명조 글꼴, 넓은 줄 간격, 좁은 폭 */
.novel article { max-width: 36em; margin: 0 auto; font-family: var(--font-display); font-size: 18px; line-height: 1.95; }
.novel article p { margin: 0 0 1.1em; }
.novel article h2 { text-align: center; border-top: 0; margin-top: 72px; }
.novel article hr { width: 40%; margin: 40px auto; }
.foot { color: var(--muted); font-size: 13px; margin-top: 48px; }
"""

DOC_JS = """
const md = document.getElementById("md").textContent;
const art = document.querySelector("article");
const slug = s => s.trim().toLowerCase().replace(/[^\\p{L}\\p{N}]+/gu, "-").replace(/^-|-$/g, "");
if (window.marked) {
  // 한국어는 **"…"**의 처럼 굵은 글씨 바로 뒤에 조사가 붙으면 marked가 굵게 처리하지 못해서 먼저 바꿔 둔다
  const src = JSON.parse(md).replace(/\\*\\*(?=\\S)(.+?)(?<=\\S)\\*\\*/g, "<strong>$1</strong>");
  art.innerHTML = marked.parse(src);
} else {
  // 글자 라이브러리를 못 받아 오면 원문 그대로 보여 준다
  const pre = document.createElement("pre"); pre.style.whiteSpace = "pre-wrap"; pre.textContent = JSON.parse(md); art.replaceChildren(pre);
}
art.querySelectorAll("table").forEach(t => { const w = document.createElement("div"); w.className = "tbl"; t.before(w); w.append(t); });
art.querySelectorAll("a[href^='http']").forEach(a => { a.target = "_blank"; a.rel = "noopener"; });
const used = new Set();
const heads = [...art.querySelectorAll("h2, h3")];
heads.forEach(h => { let id = slug(h.textContent) || "s"; while (used.has(id)) id += "-"; used.add(id); h.id = id; });
const toc = document.querySelector(".toc ol");
const tocHeads = heads.filter(h => h.tagName === "H2" || heads.filter(x => x.tagName === "H2").length < 6);
toc.innerHTML = tocHeads.map(h => `<li><a href="#${h.id}" style="padding-left:${h.tagName === "H3" ? 12 : 0}px">${h.textContent.replace(/[<>&]/g, "")}</a></li>`).join("");
if (!tocHeads.length) document.querySelector(".toc").hidden = true;
if (matchMedia("(max-width: 900px)").matches) document.querySelector(".toc details").open = false;
if (location.hash) { const t = document.getElementById(decodeURIComponent(location.hash.slice(1))); if (t) t.scrollIntoView(); }
// 지금 읽는 곳을 목차에 표시
const links = Object.fromEntries([...toc.querySelectorAll("a")].map(a => [a.getAttribute("href").slice(1), a]));
const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting && links[e.target.id]) { toc.querySelectorAll(".on").forEach(x => x.classList.remove("on")); links[e.target.id].classList.add("on"); } }), { rootMargin: "-70px 0px -70% 0px" });
tocHeads.forEach(h => io.observe(h));
"""


def nav(current):
    items = [f'<a class="home" href="index.html">서풍의 광시곡 플레이 기록</a>']
    for _, out, name, _, _ in DOCS:
        cur = ' aria-current="page"' if out == current else ""
        items.append(f'<a href="{out}"{cur}>{name}</a>')
    for href, name, _ in EXTRA:
        items.append(f'<a href="{href}">{name}</a>')
    return '<header class="top"><nav aria-label="문서 목록">' + "".join(items) + "</nav></header>"


def head(title, desc, css):
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<style>{BASE_CSS}{css}</style>
</head>"""


def first_title(md):
    m = re.search(r"^# (.+)$", md, re.M)
    return m.group(1).strip() if m else ""


def now_point(md):
    m = re.search(r"^> \*\*현재 진행 시점\*\*:\s*(.+)$", md, re.M)
    return m.group(1).strip() if m else ""


def build_doc(src, out, name, desc, novel):
    md = (ROOT / src).read_text(encoding="utf-8")
    title = first_title(md) or name
    # </script> 가 본문에 있어도 깨지지 않게 JSON으로 넣는다
    data = json.dumps(md, ensure_ascii=False).replace("</", "<\\/")
    page = head(title, desc, DOC_CSS) + f"""
<body class="{'novel' if novel else ''}">
{nav(out)}
<div class="layout">
  <aside class="toc"><details open><summary>목차</summary><ol></ol></details></aside>
  <article><p style="color:var(--muted)">불러오는 중…</p></article>
</div>
<script id="md" type="application/json">{data}</script>
<script src="{MARKED}"></script>
<script>{DOC_JS}</script>
</body>
</html>
"""
    (ROOT / out).write_text(page, encoding="utf-8")
    return title, md


INDEX_CSS = """
main { max-width: 980px; margin: 0 auto; padding: 40px 16px 64px; }
h1 { word-break: keep-all; font-family: var(--font-display); font-size: clamp(30px, 5vw, 44px); line-height: 1.2; margin: 0 0 6px; letter-spacing: .02em; text-wrap: balance; }
.sub { color: var(--muted); margin: 0 0 24px; }
.now { background: var(--panel); border: 1px solid var(--line); border-left: 3px solid var(--gold); border-radius: 6px; padding: 14px 16px; margin: 0 0 32px; }
.now b { display: block; font-size: 12px; letter-spacing: .08em; color: var(--gold); margin-bottom: 4px; }
h2 { font-size: 13px; letter-spacing: .1em; color: var(--muted); font-weight: 600; margin: 32px 0 10px; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
.card { display: grid; gap: 4px; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; text-decoration: none; color: var(--text); transition: border-color .15s; }
.card:hover { border-color: var(--gold-dim); color: var(--text); }
.card .n { font-family: var(--font-display); font-size: 21px; font-weight: 700; color: var(--gold); }
.card .d { word-break: keep-all; color: var(--muted); font-size: 14px; line-height: 1.5; }
.card .f { color: var(--muted); font-size: 12px; margin-top: 6px; }
.foot { color: var(--muted); font-size: 13px; margin-top: 48px; }
"""


def build_index(built):
    story_md = built["story.html"][1]
    point = now_point(story_md)
    cards = []
    for src, out, name, desc, _ in DOCS:
        cards.append(f'<a class="card" href="{out}"><span class="n">{name}</span><span class="d">{desc}</span><span class="f">원본: {src}</span></a>')
    extra = [f'<a class="card" href="{href}"><span class="n">{name}</span><span class="d">{desc}</span></a>' for href, name, desc in EXTRA]
    today = datetime.date.today().isoformat()
    page = head("서풍의 광시곡 플레이 기록", "창세기전 외전 서풍의 광시곡 리마스터 플레이 기록 모음", INDEX_CSS) + f"""
<body>
{nav("index.html")}
<main>
  <h1>서풍의 광시곡 플레이 기록</h1>
  <p class="sub">창세기전 외전: 서풍의 광시곡 (리마스터)를 하면서 정리한 문서 모음. 스포일러 없이 지금 진행한 곳까지만 적는다.</p>
  <div class="now"><b>현재 진행 시점</b>{html.escape(point)}</div>
  <h2>기록</h2>
  <div class="cards">{''.join(cards)}</div>
  <h2>지도</h2>
  <div class="cards">{''.join(extra)}</div>
  <p class="foot">마지막으로 만든 날: {today}</p>
</main>
</body>
</html>
"""
    (ROOT / "index.html").write_text(page, encoding="utf-8")


def main():
    built = {}
    for src, out, name, desc, novel in DOCS:
        built[out] = build_doc(src, out, name, desc, novel)
        print(f"{src} -> {out}")
    build_index(built)
    print("index.html")
    # GitHub Pages가 md를 따로 손대지 않고 그대로 두게 한다
    (ROOT / ".nojekyll").touch()


if __name__ == "__main__":
    main()
