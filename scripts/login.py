"""Scraplingでスクレイピングをする。

scrapingcourseにログインする。
"""

import asyncio
import os
from typing import TYPE_CHECKING

from scrapling.fetchers import AsyncStealthySession

if TYPE_CHECKING:
  from playwright.async_api import Page


# 環境変数を取得
username = os.getenv("SCRAPING_USERNAME") or ""
password = os.getenv("SCRAPING_PASSWORD") or ""


async def login_to_scrapingcourse(page: Page) -> Page:
  """ScrapingCourseサイトにログインする処理を行う。

  Parameters:
  ----------
  page : Page
    Playwrightのページオブジェクト。操作対象のブラウザページを指定する。

  Returns:
  -------
  Page
    ログイン後のページオブジェクト。

  Raises:
  ------
  Exception
    ログイン処理中に問題が発生した場合（例：要素が見つからない、タイムアウトなど）。
  """
  await page.fill('input[name="email"]', username)
  await page.fill('input[name="password"]', password)

  await page.click('button[type="submit"]')

  await page.wait_for_load_state(state="networkidle")

  return page


async def main() -> None:
  """メイン処理を実行し、ScrapingCourseサイトへのログインとダッシュボード取得を行う。

  Parameters:
  ----------
  None
    引数なし。

  Returns:
  -------
  None
    返り値なし。ログイン後のページタイトルを表示する。

  Raises:
  ------
  Exception
    ログイン処理やページ遷移中に問題が発生した場合。
  """
  async with AsyncStealthySession(headless=True, solve_cloudflare=True) as session:
    await session.fetch(
      "https://www.scrapingcourse.com/login", page_action=login_to_scrapingcourse
    )

    page = await session.fetch("https://www.scrapingcourse.com/dashboard")

    first_item = page.css("#product-grid .product-item").first

    print(first_item)


if __name__ == "__main__":
  asyncio.run(main())
