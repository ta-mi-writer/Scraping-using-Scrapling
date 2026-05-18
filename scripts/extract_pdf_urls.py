"""PDF URLを抽出するスクリプト。

subsidies テーブルの official_url からページを取得し、
ページ内に存在するPDFファイルのURLを抽出して pdf_files テーブルに保存する。
"""

import time
from urllib.parse import urljoin

from models import PdfFile, Subsidy
from scrapling.fetchers import Fetcher
from scrapling.parser import Selector
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

# データベースパス
DB_PATH = "data/subsidies.db"

# リトライ設定
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒

# リクエスト間のウェイト（秒）
REQUEST_INTERVAL = 2


def extract_pdf_urls(html: str, base_url: str) -> list[str]:
  """HTMLからPDFファイルのURLを抽出する。

  Args:
      html: ページのHTMLコンテンツ。
      base_url: 相対パスを絶対パスに変換するためのベースURL。

  Returns:
      抽出されたPDF URLのリスト（重複なし）。
  """
  sel = Selector(html)
  pdf_urls = set()

  # 全てのリンクからPDF URLを抽出
  for link in sel.css("a::attr(href)").getall():
    if link and ".pdf" in link.lower():
      # 相対パスを絶対パスに変換
      absolute_url = urljoin(base_url, link)
      pdf_urls.add(absolute_url)

  return sorted(pdf_urls)


def process_subsidy(
  subsidy: Subsidy, index: int, total: int, session: Session
) -> tuple[bool, bool]:
  """1件の補助金レコードを処理する。

  Args:
      subsidy: 補助金レコード。
      index: 現在のインデックス（1から始まる）。
      total: 総レコード数。
      session: SQLAlchemy セッション。

  Returns:
      tuple: (成功フラグ, スキップフラグ) のタプル。
  """
  name = subsidy.name
  official_url = subsidy.official_url

  # official_url がない場合はスキップ
  if not official_url:
    print(f"  [{index}/{total}] スキップ(official_urlなし): {name[:40]}")
    return (False, True)

  # 既に pdf_files が存在する場合はスキップ
  if subsidy.pdf_files:
    print(f"  [{index}/{total}] スキップ(既に処理済み): {name[:40]}")
    return (False, True)

  print(f"  [{index}/{total}] 取得中: {name[:40]}")
  print(f"    URL: {official_url}")

  # リトライ付きで取得
  for attempt in range(1, MAX_RETRIES + 1):
    try:
      page = Fetcher.get(official_url)
      html = page.html_content

      if not html:
        print(f"    [リトライ {attempt}/{MAX_RETRIES}] HTMLが空")
        time.sleep(RETRY_DELAY)
        continue

      pdf_urls = extract_pdf_urls(html, official_url)

      # pdf_files テーブルに保存
      for url in pdf_urls:
        pdf_file = PdfFile(
          subsidy_id=subsidy.id,
          url=url,
        )
        session.add(pdf_file)

      if pdf_urls:
        print(f"    ✅ PDF数: {len(pdf_urls)}件")
      else:
        print("    ⚠️  PDFが見つかりませんでした")

    except (ConnectionError, TimeoutError) as e:
      print(f"    [リトライ {attempt}/{MAX_RETRIES}] 通信エラー: {e}")
      if attempt < MAX_RETRIES:
        time.sleep(RETRY_DELAY)
      else:
        print(f"    ❌ 全リトライ失敗: {e}")
        return (False, False)
    else:
      return (True, False)

  return (False, False)


def main() -> None:
  """メイン処理。"""
  engine = create_engine(f"sqlite:///{DB_PATH}")

  with Session(engine) as session:
    # official_url が設定されているレコードを取得
    subsidies = (
      session.execute(select(Subsidy).where(Subsidy.official_url.is_not(None)))
      .scalars()
      .all()
    )

    total = len(subsidies)
    print(f"処理対象: {total}件")
    print("=" * 60)

    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, subsidy in enumerate(subsidies, 1):
      success, skipped = process_subsidy(subsidy, i, total, session)
      if skipped:
        skip_count += 1
      elif success:
        success_count += 1
      else:
        fail_count += 1

      # リクエスト間ウェイト
      if i < total:
        time.sleep(REQUEST_INTERVAL)

    # コミット
    session.commit()

  print()
  print("=" * 60)
  print(f"処理完了: {total}件中")
  print(f"  ✅ 成功: {success_count}件")
  print(f"  ⏭️  スキップ: {skip_count}件")
  print(f"  ❌ 失敗: {fail_count}件")


if __name__ == "__main__":
  main()
