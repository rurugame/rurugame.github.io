"""data/videos.json から、動画1本ごとの攻略ページ（videos/<動画ID>.html）と一覧ページ、
sitemap.xml を作る。

GitHub Actions（.github/workflows/update-videos.yml）で fetch_videos.py の後に実行される。
ページの中身は動画の概要欄から作るので、概要欄が充実しているほどページも充実する。
概要欄に本文も目次もない動画のページは、検索エンジンに載せない（noindex）。

手で videos/ 以下を編集しても次の実行で上書きされる。見た目を変えるときはこのファイルを直す。
"""
import html
import json
import pathlib
import re
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "videos.json"
OUT = ROOT / "videos"
SITE = "https://rurugame.github.io"
CHANNEL = "https://www.youtube.com/@RuLgames"

# 概要欄のうち、攻略の内容ではない行（宣伝・リンク・素材のクレジットなど）
SKIP_WORDS = ("http", "チャンネル登録", "メンバーシップ", "メンバー登録", "BGM", "素材", "お借り", "効果音",
              "Twitter", "ツイッター", "X（旧", "X(旧", "サブチャンネル", "ご視聴", "高評価")
CHAPTER = re.compile(r"^\s*(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\s*[-－:：]?\s*(.*)$")
LIST_MARK = re.compile(r"^\s*([①-⑳]|[・•\-－]|\d+[\.．、)）])\s*")

e = html.escape


def seconds(h, m, s):
    return int(h or 0) * 3600 + int(m) * 60 + int(s)


def stamp(sec):
    h, rest = divmod(sec, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def parse_description(desc):
    """概要欄を「目次」と「本文のかたまり（段落か箇条書き）」に分ける"""
    chapters, blocks, current = [], [], []

    def flush():
        if current:
            blocks.append(list(current))
            current.clear()

    for raw in desc.splitlines():
        line = raw.strip()
        m = CHAPTER.match(line)
        if m and m.group(4):
            chapters.append((seconds(m[1], m[2], m[3]), m[4].strip()))
            flush()
            continue
        if not line:
            flush()
            continue
        if line.startswith("#") or any(w in line for w in SKIP_WORDS):
            flush()
            continue
        current.append(line)
    flush()
    return chapters, blocks


def render_blocks(blocks):
    out = []
    for block in blocks:
        if len(block) > 1 and all(LIST_MARK.match(l) for l in block):
            items = "".join(f"<li>{e(LIST_MARK.sub('', l))}</li>" for l in block)
            out.append(f"<ul>{items}</ul>")
        else:
            out.append("<p>" + "<br>".join(e(l) for l in block) + "</p>")
    return "\n".join(out)


def day(iso):
    try:
        d = datetime.fromisoformat(iso)
    except ValueError:
        return ""
    return f"{d.year}年{d.month}月{d.day}日"


def plain_title(title):
    """一覧などで使う短いタイトル（末尾の【にゃんこ大戦争】を外す）"""
    return re.sub(r"\s*【にゃんこ大戦争】\s*$", "", title).strip() or title


def related(video, videos, n=3):
    """同じシリーズ（タイトルの最初の5文字が同じ）を優先し、足りなければ新しい順で補う"""
    head = plain_title(video["title"])[:5]
    others = [v for v in videos if v["id"] != video["id"]]
    same = [v for v in others if plain_title(v["title"])[:5] == head]
    rest = [v for v in others if v not in same]
    return (same + rest)[:n]


STYLE = """
  :root {
    --red: #B8241C; --red-deep: #8A1A13; --cream: #FFF4E6; --ink: #3B0D09; --ink-dim: #5A2A1E;
    --gold: #F2B33D; --sky-morning: #CDEAF7; --sky-pale: #BFE2F2; --grass: #7DB356; --grass-deep: #557F35;
    --hill: #A9CC7E; --night-deep: #120D24; --cream-dim: #F2D6BE;
    --font: "Zen Kaku Gothic New", "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif; --radius: 6px;
  }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: var(--font); font-weight: 500; font-size: 16px; line-height: 1.9; color: var(--ink);
    background: linear-gradient(var(--sky-morning), var(--sky-pale) 420px, var(--cream) 900px); -webkit-font-smoothing: antialiased; }
  a { color: inherit; }
  h1, h2, h3, p, li { word-break: auto-phrase; text-wrap: pretty; }
  img { display: block; max-width: 100%; }
  :focus-visible { outline: 2px solid var(--red); outline-offset: 3px; }
  .wrap { width: min(760px, 100% - 40px); margin-inline: auto; }
  .wide { width: min(1080px, 100% - 40px); margin-inline: auto; }
  .bar { display: flex; justify-content: space-between; align-items: center; padding: 20px 0; }
  .logo { font-weight: 900; font-size: 18px; letter-spacing: .04em; text-decoration: none; }
  .bar nav { display: flex; gap: 24px; font-size: 14px; font-weight: 700; }
  .bar nav a { text-decoration: none; }
  .bar nav a:hover { text-decoration: underline; text-underline-offset: 6px; }
  .crumb { font-size: 13px; color: var(--ink-dim); margin: 24px 0 8px; }
  .crumb a { text-decoration: none; }
  .crumb a:hover { text-decoration: underline; }
  h1 { font-weight: 900; font-size: clamp(26px, 4.2vw, 38px); line-height: 1.4; margin: 0 0 10px; }
  .meta { font-size: 13px; color: var(--ink-dim); }
  .player { position: relative; display: block; aspect-ratio: 16 / 9; width: 100%; margin: 28px 0 0; padding: 0; border: 0;
    border-radius: var(--radius); overflow: hidden; cursor: pointer; background: var(--ink) center / cover no-repeat; }
  .player::after { content: ""; position: absolute; left: 50%; top: 50%; width: 72px; height: 72px; margin: -36px 0 0 -36px;
    border-radius: 50%; background: var(--cream) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M9 7v10l8-5z' fill='%23B8241C'/%3E%3C/svg%3E") center / 40px no-repeat;
    box-shadow: 0 6px 24px rgba(0,0,0,.25); }
  .player:has(iframe)::after { display: none; }
  .player iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; }
  article h2 { font-size: 22px; font-weight: 900; margin: 56px 0 14px; padding-bottom: 8px; border-bottom: 2px solid var(--grass); }
  article p, article ul { margin: 0 0 1.2em; }
  article ul { padding-left: 1.3em; }
  article li { margin-bottom: .4em; }
  .toc { list-style: none; padding: 0; margin: 0; border-top: 1px solid rgba(59,13,9,.15); }
  .toc li { margin: 0; border-bottom: 1px solid rgba(59,13,9,.15); }
  .toc a { display: grid; grid-template-columns: 72px 1fr; gap: 12px; padding: 10px 4px; text-decoration: none; }
  .toc a:hover { background: rgba(255,255,255,.5); }
  .toc .t { font-weight: 700; color: var(--red); font-variant-numeric: tabular-nums; }
  .empty { color: var(--ink-dim); }
  .cta { margin: 64px 0 0; padding: 28px; background: var(--red); color: var(--cream); border-radius: var(--radius); }
  .cta h2 { margin: 0 0 6px; border: 0; padding: 0; font-size: 20px; }
  .cta p { margin: 0 0 18px; color: var(--cream-dim); }
  .btns { display: flex; flex-wrap: wrap; gap: 10px; }
  .btn { display: inline-block; padding: 12px 20px; border-radius: 99px; background: var(--cream); color: var(--ink);
    font-weight: 700; text-decoration: none; }
  .btn.ghost { background: transparent; color: var(--cream); box-shadow: inset 0 0 0 1.5px var(--cream-dim); }
  .btn:hover { background: #fff; color: var(--ink); }
  .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 32px 24px; }
  .card { text-decoration: none; display: block; }
  .card img { aspect-ratio: 16 / 9; object-fit: cover; border-radius: var(--radius); width: 100%; background: var(--sky-pale); }
  .card h3 { font-size: 15px; line-height: 1.6; margin: 12px 0 4px; }
  .card:hover h3 { text-decoration: underline; text-underline-offset: 4px; }
  .related { margin-top: 72px; }
  .related h2 { margin-top: 0; }
  .lead { color: var(--ink-dim); margin: 0 0 40px; max-width: 36em; }
  footer { margin-top: 96px; padding: 40px 0 56px; background: var(--night-deep); color: var(--cream-dim); font-size: 13px; }
  footer .wide { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
  @media (max-width: 760px) {
    .bar nav { display: none; }
    .grid { grid-template-columns: 1fr 1fr; gap: 24px 16px; }
  }
  @media (max-width: 480px) { .grid { grid-template-columns: 1fr; } }
"""

SCRIPT = """
<script>
(() => {
  const box = document.querySelector('.player');
  if (!box) return;
  const id = box.dataset.id;
  const play = (start = 0) => {
    box.innerHTML = `<iframe src="https://www.youtube-nocookie.com/embed/${id}?autoplay=1&start=${start}" title="${box.dataset.title}" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`;
  };
  box.addEventListener('click', () => { if (!box.querySelector('iframe')) play(); });
  document.querySelectorAll('[data-t]').forEach(a => a.addEventListener('click', ev => {
    ev.preventDefault();
    play(Number(a.dataset.t));
    box.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }));
})();
</script>
"""


def head(title, description, url, image="", noindex=False, extra=""):
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{url}">
{'<meta name="robots" content="noindex">' if noindex else ''}
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{url}">
{f'<meta property="og:image" content="{image}">' if image else ''}
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#CDEAF7">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@500;700;900&display=swap" rel="stylesheet">
<style>{STYLE}</style>
{extra}
</head>
<body>
<header class="wide bar">
  <a class="logo" href="/">るるゲーム</a>
  <nav aria-label="サイト内リンク">
    <a href="/">トップ</a>
    <a href="/videos/">攻略ページ一覧</a>
    <a href="{CHANNEL}" target="_blank" rel="noopener">YouTube</a>
  </nav>
</header>
"""


FOOT = """
<footer>
  <div class="wide">
    <span>&copy; るるゲーム ／ <a href="https://www.youtube.com/@RuLgames" target="_blank" rel="noopener">YouTube</a> ／ <a href="https://x.com/Uno_RuL" target="_blank" rel="noopener">X</a></span>
    <span>「にゃんこ大戦争」は株式会社ポノスのゲームです。このサイトは非公式のファン活動として運営しています。</span>
  </div>
</footer>
"""


def card(v, prefix=""):
    return (f'<a class="card" href="{prefix}{v["id"]}.html">'
            f'<img src="https://i.ytimg.com/vi/{v["id"]}/hqdefault.jpg" alt="" loading="lazy">'
            f'<h3>{e(plain_title(v["title"]))}</h3><div class="meta">{day(v["published"])}</div></a>')


def video_page(v, videos):
    chapters, blocks = parse_description(v.get("description", ""))
    has_content = bool(blocks or chapters)
    first_line = blocks[0][0] if blocks else ""
    title = plain_title(v["title"])
    page_title = f"{title}｜にゃんこ大戦争の攻略 るるゲーム"
    desc = (first_line or f"るるゲームの動画「{title}」の内容と目次です。")[:120]
    url = f"{SITE}/videos/{v['id']}.html"
    thumb = f"https://i.ytimg.com/vi/{v['id']}/maxresdefault.jpg"
    label = "配信アーカイブ" if v.get("kind") == "live" else "動画"

    ld = {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": v["title"],
        "description": (" ".join(" ".join(b) for b in blocks) or desc)[:500],
        "thumbnailUrl": [thumb, f"https://i.ytimg.com/vi/{v['id']}/hqdefault.jpg"],
        "uploadDate": v["published"],
        "embedUrl": f"https://www.youtube.com/embed/{v['id']}",
        "contentUrl": f"https://www.youtube.com/watch?v={v['id']}",
        "author": {"@type": "Person", "name": "るる", "url": CHANNEL},
    }
    if chapters:
        ld["hasPart"] = [{
            "@type": "Clip", "name": name, "startOffset": sec,
            "url": f"https://www.youtube.com/watch?v={v['id']}&t={sec}s",
        } for sec, name in chapters]
    extra = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>"

    toc = ""
    if chapters:
        items = "".join(
            f'<li><a href="https://www.youtube.com/watch?v={v["id"]}&amp;t={sec}s" data-t="{sec}">'
            f'<span class="t">{stamp(sec)}</span><span>{e(name)}</span></a></li>' for sec, name in chapters)
        toc = f'<h2>目次</h2>\n<ol class="toc">{items}</ol>'
    body = render_blocks(blocks)
    points = f"<h2>この動画のポイント</h2>\n{body}" if body else (
        "" if chapters else '<p class="empty">この動画の解説は準備中です。動画で確認してください。</p>')

    rel = "".join(card(r) for r in related(v, videos))
    return head(page_title, desc, url, thumb, noindex=not has_content, extra=extra) + f"""
<main class="wrap">
  <article>
    <nav class="crumb" aria-label="現在地"><a href="/">るるゲーム</a> ／ <a href="/videos/">攻略ページ一覧</a></nav>
    <h1>{e(title)}</h1>
    <div class="meta">にゃんこ大戦争の{label}・{day(v["published"])} 公開</div>
    <button class="player" type="button" data-id="{v['id']}" data-title="{e(v['title'])}"
      style="background-image:url({thumb}),url(https://i.ytimg.com/vi/{v['id']}/hqdefault.jpg)"
      aria-label="{e(v['title'])} を再生"></button>
    {points}
    {toc}
    <section class="cta">
      <h2>わからないステージは、生配信で聞いてください</h2>
      <p>るるゲームでは、詰まったステージの編成や立ち回りを、配信でいっしょに考えています。</p>
      <div class="btns">
        <a class="btn" href="{CHANNEL}?sub_confirmation=1" target="_blank" rel="noopener">チャンネル登録する</a>
        <a class="btn ghost" href="{CHANNEL}/streams" target="_blank" rel="noopener">生配信を見る</a>
      </div>
    </section>
  </article>
</main>
<section class="wide related">
  <h2>あわせて見たい動画</h2>
  <div class="grid">{rel}</div>
</section>
{FOOT}
{SCRIPT}
</body>
</html>
"""


def index_page(videos):
    cards = "".join(card(v) for v in videos)
    return head("攻略ページ一覧｜にゃんこ大戦争の攻略 るるゲーム",
                "るるゲームの動画ごとの攻略ページの一覧です。にゃんこ大戦争のステージ攻略や企画をまとめています。",
                f"{SITE}/videos/") + f"""
<main class="wide">
  <nav class="crumb" aria-label="現在地"><a href="/">るるゲーム</a></nav>
  <h1>攻略ページ一覧</h1>
  <p class="lead">動画ごとに、内容と目次をまとめています。目次を押すと、その場面から再生できます。</p>
  <div class="grid">{cards}</div>
</main>
{FOOT}
</body>
</html>
"""


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    videos = [v for v in data.get("videos", []) if not v.get("short")]
    OUT.mkdir(exist_ok=True)
    keep = set()
    indexable = []
    for v in videos:
        name = f"{v['id']}.html"
        (OUT / name).write_text(video_page(v, videos), encoding="utf-8")
        keep.add(name)
        chapters, blocks = parse_description(v.get("description", ""))
        if chapters or blocks:
            indexable.append(v)
    (OUT / "index.html").write_text(index_page(videos), encoding="utf-8")
    keep.add("index.html")
    # 一覧から消えた動画のページは消さずに残す（外部からリンクされている可能性があるため）

    urls = [(f"{SITE}/", None), (f"{SITE}/videos/", None)]
    urls += [(f"{SITE}/videos/{v['id']}.html", v["published"][:10]) for v in indexable]
    items = "".join(
        f"<url><loc>{u}</loc>{f'<lastmod>{d}</lastmod>' if d else ''}</url>" for u, d in urls)
    (ROOT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{items}</urlset>\n',
        encoding="utf-8")
    print(f"{len(videos)} pages ({len(indexable)} indexable)")


if __name__ == "__main__":
    main()
