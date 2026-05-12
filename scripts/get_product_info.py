"""商品情報を取得して、DBに保存する。"""

import asyncio

from scrapling.fetchers import Fetcher
from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

engine = create_engine("sqlite:///ec_site.db")


class Base(DeclarativeBase):
  """すべてのORMモデルクラスの基底クラス。

  このクラスを継承することで、SQLAlchemyの宣言的モデルシステムを使用できるようになります。
  """


class Product(Base):
  """商品情報を表すデータベースモデル。

  Attributes:
      id (int): 商品の一意な識別子。
      slug (str): 商品のURLスラッグ。一意である必要があります。
      name (str | None): 商品の名前。
      description (str | None): 商品の説明。
      price (int | None): 商品の価格。
      is_detailed_scraped (bool): 詳細情報がスクレイピングされたかどうか。
  """

  __tablename__ = "products"

  id: Mapped[int] = mapped_column(primary_key=True)
  slug: Mapped[str] = mapped_column(String(100), unique=True)
  name: Mapped[str | None] = mapped_column(String(100))
  description: Mapped[str | None] = mapped_column(String(200))
  price: Mapped[int | None] = mapped_column()
  is_detailed_scraped: Mapped[bool] = mapped_column(default=False)


async def main() -> None:
  """データベースからスラッグを取得し、各商品の詳細情報をスクレイピングして表示します。

  データベースから未取得の商品スラッグを取得し、対応するURLから商品情報をスクレイピングします。
  スクレイピングした情報はリストに格納され、内容が表示されます。

  Args:
      なし

  Returns:
      なし (商品情報は標準出力に表示されます)

  Raises:
      なし
  """
  with Session(engine) as session:
    statement = select(Product.slug)
    slugs = session.execute(statement).scalars().all()

  print(f"--- 取得したスラッグ一覧 (計 {len(slugs)} 件) ---")

  products_list = []

  for slug in slugs:
    with Session(engine) as session:
      statement = select(Product).where(Product.slug == slug)
      result = session.execute(statement).scalar_one_or_none()

      if result and result.is_detailed_scraped:
        print(f"スラッグ '{slug}' は既に詳細情報を取得済みです。スキップします。")
        continue

    product_url = f"https://www.scrapingcourse.com/ecommerce/product/{slug}/"

    page = Fetcher.get(product_url)

    name = page.css("h1::text").get()
    description = page.css(
      ".woocommerce-product-details__short-description p::text"
    ).get()
    price = page.css(".price bdi::text").get()

    products_list.append(
      {
        "slug": slug,
        "name": str(name),
        "description": str(description),
        "price": str(price),
      }
    )

  with Session(engine) as session:
    for product_data in products_list:
      statement = select(Product).where(Product.slug == product_data["slug"])
      result = session.execute(statement).scalar_one_or_none()

      if result:
        result.name = product_data["name"]
        result.description = product_data["description"]
        result.price = product_data["price"]
        result.is_detailed_scraped = True
    session.commit()


if __name__ == "__main__":
  asyncio.run(main())
