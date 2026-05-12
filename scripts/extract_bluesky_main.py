"""Blueskyのメインコンテンツを取得し、分析するためのスクリプト。

このスクリプトは、保存済みのブラウザプロファイルを使用して
Blueskyにアクセスし、ログイン後のメインコンテンツ（<main>タグ内）を抽出します。
"""

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from playwright.async_api import Error as PlaywrightError
from scrapling.fetchers import AsyncStealthySession

if TYPE_CHECKING:
  from playwright.async_api import Page

# 保存済みのセッションディレクトリ
my_bluesky_data_dir = (
  r"C:\Users\j\Documents\Scraping\scrapling-first-step\my_bluesky_data"
)


async def extract_main_content(page: Page) -> None:
  """ページ読み込み後に実行されるアクション。"""
  print("Waiting for userAvatarImage to appear...")
  try:
    # 1. ログイン・読み込み完了を待機
    await page.wait_for_selector('[data-testid="userAvatarImage"]', timeout=30000)
    print("Login confirmed: userAvatarImage found.")

    # 2. ネットワークの静止を待機 (コンテンツの完全な読み込みを待つ)
    print("Waiting for network to become idle...")
    await page.wait_for_load_state("networkidle")
    print("Network is idle. Content should be loaded.")

    # 念のため、さらに短い待機時間を設けてレンダリングを確実にする
    await asyncio.sleep(2)

    # 3. <main>タグのHTMLを取得
    main_element = await page.query_selector("main")
    if main_element:
      main_html = await main_element.inner_html()

      # 分析しやすいようにファイルに保存
      # async関数内でブロッキングなファイル操作を避けるため asyncio.to_thread を使用
      output_path = Path("bluesky_main_content.html")
      await asyncio.to_thread(output_path.write_text, main_html, encoding="utf-8")

      print(f"Successfully extracted <main> content to {output_path}")
    else:
      print("Error: <main> tag not found on the page.")

  except (TimeoutError, PlaywrightError) as e:
    print(f"A scraping error occurred during page action: {e}")


async def main() -> None:
  """メイン処理。"""
  print(f"Using session data from: {my_bluesky_data_dir}")

  try:
    async with AsyncStealthySession(
      user_data_dir=my_bluesky_data_dir, headless=True
    ) as session:
      # page_action を使用して、ページ読み込み後に extract_main_content を実行させる
      await session.fetch("https://bsky.app/", page_action=extract_main_content)

  except (TimeoutError, PlaywrightError) as e:
    print(f"A connection error occurred: {e}")


if __name__ == "__main__":
  asyncio.run(main())
