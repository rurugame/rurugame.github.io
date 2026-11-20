"""るるゲーム（メイン）のチャンネル登録者数を、YouTubeのチャンネルページから読んで data/subs.json に記録する。

GitHub Actions（.github/workflows/update-videos.yml）から1時間ごとに実行される。
記録は1日1件。同じ日のうちは、最新の値で上書きする。
YouTubeの公開表示（例「2.62万人」）は上3桁に丸められているので、正確な人数ではない。
取得に失敗しても（YouTubeがGitHubのサーバーからの取得を止めた場合など）、エラーにはせずに終わる。

出力の形:
  {"history": [{"date": "2026-11-21", "label": "2.62万人", "subs": 26200, "views": 30818743}, ...]}
"""
import datetime
import json
import pathlib
import re
import urllib.request

URL = "https://www.youtube.com/channel/UCI4sJGfpJaa15xWM8D78pAg/about?hl=ja&gl=JP"
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "subs.json"
JST = datetime.timezone(datetime.timedelta(hours=9))


def fetch():
    req = urllib.request.Request(URL, headers={
        "User-Agent": "Mozilla/5.0 (rurugame-site-updater)",
        "Accept-Language": "ja",
    })
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read().decode("utf-8", "replace")


def to_number(label):
    """「2.62万人」→ 26200、「9,870人」→ 9870"""
    m = re.search(r"([\d.,]+)\s*(万)?", label)
    if not m:
        return None
    n = float(m.group(1).replace(",", ""))
    return round(n * 10000) if m.group(2) else round(n)


def read_counts(html):
    """チャンネル情報の欄から、登録者数の表示と総再生回数を読む。
    ページにはおすすめのサブチャンネルの登録者数も出るので、総再生回数と並んでいるものだけを使う"""
    m = re.search(r'"subscriberCountText":"チャンネル登録者数 ([^"]+)","viewCountText":"([\d,]+) ?回視聴"', html)
    if m:
        return m.group(1), int(m.group(2).replace(",", ""))
    # 見つからないときは、ページ上部の見出しにある表示を使う
    m = re.search(r'"content":"チャンネル登録者数 ([^"]+)"', html)
    return (m.group(1), None) if m else (None, None)


def main():
    try:
        label, views = read_counts(fetch())
    except Exception as e:  # 通信エラーなど。動画の更新は止めない
        # 「::warning::」で始まる行は、GitHub Actions の実行ページ上部に注意書きとして出る（ログインなしで見られる）
        print(f"::warning title=登録者数::取得できませんでした: {e}")
        return
    subs = to_number(label) if label else None
    if not subs:
        print("::warning title=登録者数::ページの中に登録者数が見つかりませんでした")
        return

    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"history": []}
    history = data["history"]
    today = datetime.datetime.now(JST).date().isoformat()
    entry = {"date": today, "label": label, "subs": subs}
    if views:
        entry["views"] = views
    if history and history[-1]["date"] == today:
        history[-1] = entry
    else:
        history.append(entry)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"::notice title=登録者数::{today} {label}（{subs}人）を記録しました")


if __name__ == "__main__":
    main()
