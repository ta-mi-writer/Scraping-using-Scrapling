"""BlueskyのHTMLから投稿データを構造化して抽出する最終スクリプト。

このスクリプトは、保存済みのHTMLファイルを解析し、
[ユーザー名, ハンドル名, 投稿時間, 本文] というパターンの繰り返しを検知して
データをリスト形式で抽出します。
"""

import json
import re
from pathlib import Path

from scrapling import Selector

# ハンドル名の最大文字数の定数
MAX_HANDLE_LENGTH = 50


def extract_bluesky_posts() -> list:
  """BlueskyのHTMLから投稿データを構造化して抽出します。

  保存済みのHTMLファイルを解析し、[ユーザー名, ハンドル名, 投稿時間, 本文]
  というパターンの繰り返しを検知してデータをリスト形式で抽出します。

  Returns:
      list: 抽出された投稿データの辞書を格納したリスト。
  """
  file_path = Path("bluesky_main_content.html")
  try:
    with file_path.open(encoding="utf-8") as f:
      html_content = f.read()
  except FileNotFoundError:
    print(f"Error: {file_path} not found. Please run the extraction script first.")
    return []

  # ScraplingのSelectorでHTMLを解析
  selector = Selector(html_content)

  # 2. 「dir="auto"」属性を持つすべての要素からテキストを抽出する
  all_texts = selector.css('[dir="auto"]').xpath("text()").getall()

  # 空白文字のみの要素を除去し、さらに不可視文字を完全に除去する
  clean_texts = []
  for t in all_texts:
    # \u2000-\u200F などの方向制御文字や、その他の非表示文字を広範囲に除去
    cleaned = re.sub(r"[\u2000-\u200F\u202A-\u202E\uFEFF]", "", t).strip()
    if cleaned:
      clean_texts.append(cleaned)

  print(f"Total clean texts: {len(clean_texts)}")

  posts = []
  i = 0

  # 3. 抽出したテキストリストを走査し、投稿のパターンを検知する
  while i < len(clean_texts):
    text = clean_texts[i]

    # ハンドル名（@が含まれる）を「投稿の開始地点」の目印として利用する
    if "@" in text and (text.startswith("@") or len(text) < MAX_HANDLE_LENGTH):
      try:
        # --- パターンの解析 ---
        # [i-1] : ハンドル名の直前にあるはずの「ユーザー名」
        user_name = clean_texts[i - 1] if i > 0 else "Unknown User"

        # [i]   : 現在の要素である「ハンドル名」
        handle = text

        # [i+1] : ハンドル名の直後にあるはずの「投稿時間」 (例: 12h, 1d)
        post_time = clean_texts[i + 1] if i + 1 < len(clean_texts) else "Unknown Time"

        # [i+2] : 時間の直後にあるはずの「投稿本文」
        content = clean_texts[i + 2] if i + 2 < len(clean_texts) else "No Content"

        # 抽出したデータを辞書形式で保存
        post_data = {
          "user_name": user_name,
          "handle": handle,
          "time": post_time,
          "content": content,
        }
        posts.append(post_data)

        # 次の投稿を探すため、インデックスを進める
        i += 4

      except IndexError:
        break
    else:
      i += 1

  return posts


if __name__ == "__main__":
  print("Starting Bluesky post extraction (Final Fixed version)...\n")
  results = extract_bluesky_posts()

  if results:
    print(f"Successfully extracted {len(results)} posts:\n")

    for idx, post in enumerate(results, 1):
      print(f"--- Post {idx} ---")
      print(f"User:    {post['user_name']}")
      print(f"Handle:  {post['handle']}")
      print(f"Time:    {post['time']}")
      print(f"Content: {post['content']}")
      print()

    with Path("extracted_posts.json").open("w", encoding="utf-8") as f:
      json.dump(results, f, ensure_ascii=False, indent=2)
    print("Results saved to extracted_posts.json")
  else:
    print("No posts were extracted. Please check the HTML content.")
