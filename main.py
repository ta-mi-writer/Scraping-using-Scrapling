"""データを保存する"""

import asyncio

from scrapling.fetchers import Fetcher
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from scripts.get_slugs import get_slugs
from scripts.models import Base, Product

engine = create_engine("sqlite:///ec_site.db")
Base.metadata.create_all(engine)


def save_product_slugs(slugs: list[str]) -> None:
  """指定されたスラッグのリストから新規商品情報をデータベースに保存します。

  Args:
      slugs (list[str]): 保存する商品のスラッグのリスト。
  """
  with Session(engine) as session:
    for slug in slugs:
      existing = session.scalar(select(Product).where(Product.slug == slug))
      if not existing:
        new_product = Product(slug=slug)
        session.add(new_product)
    session.commit()


async def main() -> None:
  """商品一覧から商品ページのURLを取得する。"""
  products_url = "https://www.scrapingcourse.com/ecommerce/"
  slug_list = []

  page = Fetcher.get(products_url)
  slug_list = await get_slugs(page)

  save_product_slugs(slug_list)


if __name__ == "__main__":
  asyncio.run(main())
