"""データベースからデータ取得する"""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

engine = create_engine("sqlite:///ec_site.db")


class Base(DeclarativeBase):
  """すべてのORMモデルクラスの基底クラス。

  このクラスを継承することで、SQLAlchemyの宣言的モデルシステムを使用できるようになります。
  """


class Product(Base):
  """商品モデルクラス"""

  __tablename__ = "products"
  id: Mapped[int] = mapped_column(primary_key=True)
  slug: Mapped[str] = mapped_column()
  name: Mapped[str | None]
  description: Mapped[str | None]
  price: Mapped[int | None]
  is_detailed_scraped: Mapped[bool]


def display_products() -> None:
  """データベースからすべての商品情報を取得して表示します。

  この関数はProductテーブルのすべてのカラムの値を取得し、
  それぞれを標準出力に表示します。
  """
  with Session(engine) as session:
    statement = select(Product)

    products = session.execute(statement).scalars().all()

    print(f"--- ec_site.db の中身 (計 {len(products)} 件) ---")
    for product in products:
      print(f"ID: {product.id}")
      print(f"Slug: {product.slug}")
      print(f"Name: {product.name}")
      print(f"Description: {product.description}")
      print(f"Price: {product.price}")
      print(f"Detailed Scraped: {product.is_detailed_scraped}")
      print("-" * 30)


if __name__ == "__main__":
  display_products()
