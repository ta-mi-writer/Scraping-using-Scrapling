"""データベースモデル定義モジュール

このモジュールには、アプリケーションで使用する。
SQLAlchemy の ORM モデルが定義されています。
各モデルはデータベーステーブルに対応しており、データの永続化と操作を行います。

Classes:
    Base: すべてのORMモデルクラスの基底クラス。
    Product: 商品情報を表すデータベースモデル。
"""

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
