"""Blueskyへのログインおよびセッション情報の永続化を行うスクリプト。

このスクリプトは、PlaywrightとScraplingライブラリを利用してBlueskyへの自動ログイン
を実行し、その認証状態（セッション）をローカルディレクトリに保存します。
環境変数 `BLUESKY_USERNAME` および `BLUESKY_PASSWORD` を使用して認証を行い、
指定されたパスにブラウザプロファイルを生成・保存することで、次回以降の実行時に
ログイン状態を維持したままスクレイピングを開始することが可能になります。
"""

import asyncio
import os
from typing import TYPE_CHECKING

from scrapling.fetchers import AsyncStealthySession

if TYPE_CHECKING:
  from playwright.async_api import Page


# 環境変数を取得
username = os.getenv("BLUESKY_USERNAME") or ""
password = os.getenv("BLUESKY_PASSWORD") or ""

my_bluesky_data_dir = (
  r"C:\Users\j\Documents\Scraping\scrapling-first-step\my_bluesky_data"
)


async def login_to_bluesky(page: Page) -> Page:
  """Blueskyにログインする。

  Args:
      page (Page): PlaywrightのPageオブジェクト。

  Returns:
      Page: ログイン後のPageオブジェクト。
  """
  await page.wait_for_selector('button[aria-label="Sign in"]')

  print("サインインボタンを押す前に 3秒待機中")
  await page.wait_for_timeout(3000)

  await page.click('button[aria-label="Sign in"]')

  print("サインインボタン押下 10秒待機中")
  await page.wait_for_timeout(10000)

  await page.wait_for_selector('input[data-testid="loginUsernameInput"]')
  await page.fill('input[data-testid="loginUsernameInput"]', username)
  await page.fill('input[data-testid="loginPasswordInput"]', password)

  await page.click('button[data-testid="loginNextButton"]')

  await page.wait_for_load_state(state="networkidle")

  print("ログイン完了 10秒待機中")
  await page.wait_for_timeout(10000)

  return page


async def main() -> None:
  """Blueskyにログインし、セッション情報を保存する。

  以下の処理を実行する：
  1. ログイン：資格情報を使用してBlueskyにログインします。
  2. セッション情報の保存：ログイン状態を維持するためセッション情報を保存します。
  """
  async with AsyncStealthySession(
    user_data_dir=my_bluesky_data_dir, headless=False
  ) as session:
    await session.fetch(
      "https://bsky.app/search?q=bluesky", page_action=login_to_bluesky
    )


if __name__ == "__main__":
  asyncio.run(main())
