"""ECサイトのページネーション情報取得スクリプト

このスクリプトはECサイトからページネーション情報を取得し、
最終ページ番号を表示します。
"""

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from scrapling.engines.toolbelt.custom import Response
from scrapling.fetchers import Fetcher

products_url = "https://www.scrapingcourse.com/ecommerce/"


async def get_last_page(page: Response) -> int:
  """ECサイトから最終ページ番号を取得して表示します。

  この関数は指定されたECサイトのURLからページを取得し、
  ページネーション要素から最終ページ番号を抽出して表示します。
  """
  last_page_elements = page.css("ul.page-numbers li:nth-last-child(2) a::text").get()

  try:
    last_page = int(last_page_elements) if last_page_elements else 1
  except ValueError, TypeError:
    last_page = 1

  page_transition_result = page.css("#result-count::text").get()
  page_transition_result = (
    page_transition_result.strip() if page_transition_result else None
  )

  print(f"最終ページ: {last_page}")
  print(f"ページリザルト: {page_transition_result}")

  return last_page


async def page_crawl(last_page: int) -> None:
  """ページをクロールします。

  この関数は指定されたページをクロールし、商品情報を抽出します。
  """
  results = []

  for i in range(2, last_page + 1):
    url = f"{products_url}page/{i}/"
    page_data = Fetcher.get(url)

    result = page_data.css("#result-count::text").get()
    if result:
      results.append({"page": i, "result": result.strip()})

  print(f"クロール結果: {results}")


async def main() -> None:
  """メイン処理を実行します。

  商品一覧ページを取得し、最終ページ番号を解析します。
  """
  page = Fetcher.get(products_url)
  last_page = await get_last_page(page)
  await page_crawl(last_page)


if __name__ == "__main__":
  asyncio.run(main())
