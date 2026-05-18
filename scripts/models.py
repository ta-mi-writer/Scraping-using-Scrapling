"""SQLAlchemy モデル定義.

subsidies テーブル: 補助金の基本情報
pdf_files テーブル: PDF ファイル情報（subsidies と関連）
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
  """全モデルの基底クラス."""



class Subsidy(Base):
  """補助金情報を格納するテーブル."""

  __tablename__ = "subsidies"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  name: Mapped[str] = mapped_column(Text, nullable=False)
  detail_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
  application_period: Mapped[str | None] = mapped_column(Text)
  upper_limit_yen: Mapped[int | None] = mapped_column(Integer)
  status: Mapped[str | None] = mapped_column(Text)
  official_url: Mapped[str | None] = mapped_column(Text)
  created_at: Mapped[datetime] = mapped_column(
    DateTime, default=lambda: datetime.now(UTC)
  )
  updated_at: Mapped[datetime] = mapped_column(
    DateTime,
    default=lambda: datetime.now(UTC),
    onupdate=lambda: datetime.now(UTC),
  )

  # リレーションシップ
  pdf_files: Mapped[list[PdfFile]] = relationship(
    back_populates="subsidy", cascade="all, delete-orphan"
  )

  def __repr__(self) -> str:
    """デバッグ用の文字列表現."""
    return f"<Subsidy(id={self.id}, name='{self.name[:30]}...')>"


class PdfFile(Base):
  """PDF ファイル情報を格納するテーブル."""

  __tablename__ = "pdf_files"
  __table_args__ = (UniqueConstraint("subsidy_id", "url", name="uq_subsidy_pdf_url"),)

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  subsidy_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("subsidies.id"), nullable=False
  )
  url: Mapped[str] = mapped_column(Text, nullable=False)
  extracted_text_path: Mapped[str | None] = mapped_column(Text)
  created_at: Mapped[datetime] = mapped_column(
    DateTime, default=lambda: datetime.now(UTC)
  )

  # リレーションシップ
  subsidy: Mapped[Subsidy] = relationship(back_populates="pdf_files")

  def __repr__(self) -> str:
    """デバッグ用の文字列表現."""
    return f"<PdfFile(id={self.id}, url='{self.url[:50]}...')>"
