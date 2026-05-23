"""SQLAlchemy モデル定義.

subsidies テーブル: 補助金の基本情報
  - id: 主キー（自動採番）
  - name: 補助金名
  - description: 簡単な説明文
  - detail_url: 詳細ページURL（一意）
  - application_period: 応募期間
  - upper_limit_yen: 上限金額（円）
  - status: ステータス
  - official_url: 公式URL
  - created_at: 作成日時
  - updated_at: 更新日時

pdf_files テーブル: PDF ファイル情報（subsidies と関連）
  - id: 主キー（自動採番）
  - subsidy_id: subsidies テーブルへの外部キー
  - url: PDFファイルのURL
  - extracted_text_path: 抽出テキストファイルのパス
  - created_at: 作成日時

purposes テーブル: 目的
  - id: 主キー（自動採番）
  - name: 目的名

target_expenses テーブル: 対象経費
  - id: 主キー（自動採番）
  - name: 対象経費名

target_businesses テーブル: 対象事業者
  - id: 主キー（自動採番）
  - name: 対象事業者名
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
  description: Mapped[str | None] = mapped_column(Text)
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
  purposes: Mapped[list[Purpose]] = relationship(
    secondary="subsidy_purposes", back_populates="subsidies"
  )
  target_expenses: Mapped[list[TargetExpense]] = relationship(
    secondary="subsidy_target_expenses", back_populates="subsidies"
  )
  target_businesses: Mapped[list[TargetBusiness]] = relationship(
    secondary="subsidy_target_businesses", back_populates="subsidies"
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


class Purpose(Base):
  """目的を格納するテーブル."""

  __tablename__ = "purposes"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

  subsidies: Mapped[list[Subsidy]] = relationship(
    secondary="subsidy_purposes", back_populates="purposes"
  )

  def __repr__(self) -> str:
    """デバッグ用の文字列表現."""
    return f"<Purpose(id={self.id}, name='{self.name}')>"


class TargetExpense(Base):
  """対象経費を格納するテーブル."""

  __tablename__ = "target_expenses"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

  subsidies: Mapped[list[Subsidy]] = relationship(
    secondary="subsidy_target_expenses", back_populates="target_expenses"
  )

  def __repr__(self) -> str:
    """デバッグ用の文字列表現."""
    return f"<TargetExpense(id={self.id}, name='{self.name}')>"


class TargetBusiness(Base):
  """対象事業者を格納するテーブル."""

  __tablename__ = "target_businesses"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
  name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

  subsidies: Mapped[list[Subsidy]] = relationship(
    secondary="subsidy_target_businesses", back_populates="target_businesses"
  )

  def __repr__(self) -> str:
    """デバッグ用の文字列表現."""
    return f"<TargetBusiness(id={self.id}, name='{self.name}')>"


class SubsidyPurpose(Base):
  """補助金と目的の関連テーブル."""

  __tablename__ = "subsidy_purposes"

  subsidy_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("subsidies.id"), primary_key=True
  )
  purpose_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("purposes.id"), primary_key=True
  )


class SubsidyTargetExpense(Base):
  """補助金と対象経費の関連テーブル."""

  __tablename__ = "subsidy_target_expenses"

  subsidy_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("subsidies.id"), primary_key=True
  )
  target_expense_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("target_expenses.id"), primary_key=True
  )


class SubsidyTargetBusiness(Base):
  """補助金と対象事業者の関連テーブル."""

  __tablename__ = "subsidy_target_businesses"

  subsidy_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("subsidies.id"), primary_key=True
  )
  target_business_id: Mapped[int] = mapped_column(
    Integer, ForeignKey("target_businesses.id"), primary_key=True
  )
