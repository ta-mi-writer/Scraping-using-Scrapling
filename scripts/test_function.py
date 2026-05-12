"""Scraplingを使用した簡単なスクレイピングコードを作成する。"""

import asyncio

from scrapling.fetchers import Fetcher


async def the_function_you_want_to_test() -> str:
  """スクレイピングを実行します。"""
  products_url = "https://www.scrapingcourse.com/ecommerce/"

  page = Fetcher.get(products_url)
  h1_text = page.css("h1::text").get()
  return str(h1_text)


async def main() -> None:
  """メイン関数"""
  await the_function_you_want_to_test()


if __name__ == "__main__":
  asyncio.run(main())
