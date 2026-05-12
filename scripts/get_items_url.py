"""Scraplingでスクレイピングをする。

scrapingcourseから要素を取得する。
"""

import asyncio
import re

from scrapling.fetchers import Fetcher


async def main() -> None:
  """商品一覧から商品ページのURLを取得する。"""
  products_url = "https://www.scrapingcourse.com/ecommerce/"

  page = Fetcher.get(products_url)
  items_element = page.css("#product-list .product")

  for item in items_element:
    url = item.css("a::attr(href)").get()

    if url:
      match = re.search(r"product\/([a-zA-Z0-9\-]+)", url)
      if match:
        slug = match.group(1)
        print(slug)


if __name__ == "__main__":
  asyncio.run(main())
