"""商品ページからスラッグ情報を取得するためのモジュール.

このスクリプトは eコマースサイトから製品ページへのリンクをスクレイピングし、
各製品ページのURLから「スラッグ」（slug）部分を抽出します。
"""

import asyncio
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from scrapling.engines.toolbelt.custom import Response
from scrapling.fetchers import Fetcher


async def get_slugs(page: Response) -> list[str]:
  """ページ内の製品リンクからスラッグを抽出して返します.

  Args:
      page (Response): スクレイピング対象のページオブジェクト。

  Returns:
      list[str]: 抽出されたスラッグのリスト。
  """
  slugs = []
  products_element = page.css("#product-list .product")
  for product_element in products_element:
    url = product_element.css("a::attr(href)").get()
    match = re.search(r"product\/([a-zA-Z0-9\-]+)", str(url))
    if match:
      slug = match.group(1)
      slugs.append(slug)

  return slugs


async def main() -> None:
  """メイン処理を実行します.

  商品一覧ページを取得し、そこから個別商品ページのスラッグを抽出します。
  """
  products_url = "https://www.scrapingcourse.com/ecommerce/"

  page = Fetcher.get(products_url)
  await get_slugs(page)


if __name__ == "__main__":
  asyncio.run(main())
