r"""PDF 一括抽出スクリプト.

- データベースの pdf_files テーブルから URL を取得してテキスト化
- URL を直接指定して PDF をダウンロードして変換することも可能
- ローカルファイル/フォルダから変換することも可能

使い方:
    # データベースから
    uv run scripts/extract_pdfs.py --from-db --output ./output/

    # URL から直接
    uv run scripts/extract_pdfs.py \\
      --input https://example.com/doc.pdf --output ./output/

    # ローカルファイル/フォルダ
    uv run scripts/extract_pdfs.py --input ./pdfs/ --output ./output/
"""

import argparse
import logging
import sys
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import pdfplumber
from models import PdfFile
from scrapling.fetchers import Fetcher
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
  from pdfplumber.page import Page


def clean_text(text: str | None) -> str:
  """テキストの不要な改行を整形"""
  if not text:
    return ""
  lines = text.split("\n")
  result = []
  for line in lines:
    stripped = line.strip()
    if stripped:
      result.append(stripped)
  return "\n".join(result)


def clean_cell_text(text: str | None) -> str:
  """セル内の不要な改行を除去"""
  if text is None:
    return ""
  return " ".join(str(text).split())


def remove_empty_columns(table: list[list[str | None]]) -> list[list[str | None]]:
  """空の列（全行が空）を除去"""
  if not table:
    return table

  num_cols = len(table[0])
  cols_to_keep = []
  for col_idx in range(num_cols):
    is_empty = all(
      clean_cell_text(row[col_idx]) == "" for row in table if col_idx < len(row)
    )
    if not is_empty:
      cols_to_keep.append(col_idx)

  new_table = []
  for row in table:
    new_row = [row[i] if i < len(row) else "" for i in cols_to_keep]
    new_table.append(new_row)

  return new_table


def table_to_markdown(table: list[list[str | None]]) -> str:
  """テーブルを Markdown 形式に変換"""
  if not table:
    return ""

  table = remove_empty_columns(table)

  lines = []
  for i, row in enumerate(table):
    cells = [clean_cell_text(cell) for cell in row]
    cells = [cell.replace("|", "\\|") for cell in cells]
    lines.append("| " + " | ".join(cells) + " |")

    if i == 0:
      lines.append("| " + " | ".join(["---"] * len(cells)) + " |")

  return "\n".join(lines)


def extract_page_content(page: Page) -> str:
  """1ページ分のコンテンツを抽出"""
  content = []

  text = page.extract_text()
  if text:
    content.append(clean_text(text))

  tables = page.extract_tables()
  for i, table in enumerate(tables):
    if table:
      content.append(f"\n[テーブル {i + 1}]")
      content.append(table_to_markdown(table))

  return "\n".join(content)


def _build_pdf_markdown_header(source_name: str, source_info: str | None) -> list[str]:
  """PDF Markdown ヘッダーを構築"""
  lines = []
  lines.append(f"# {source_name}")
  lines.append("")
  lines.append(f"- 抽出日時: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}")
  if source_info:
    lines.append(f"- ソース: {source_info}")
  lines.append("")
  lines.append("---")
  lines.append("")
  return lines


def _extract_pages_to_markdown(pdf: pdfplumber.pdf.PDF) -> str:
  """PDF ページを Markdown に変換"""
  lines = []
  lines.append(f"**総ページ数: {len(pdf.pages)}**")
  lines.append("")

  for i, page in enumerate(pdf.pages):
    lines.append(f"## ページ {i + 1}")
    lines.append("")

    page_content = extract_page_content(page)
    lines.append(
      page_content
      if page_content.strip()
      else "*(このページには抽出可能なコンテンツがありません)*"
    )

    lines.append("")
    lines.append("---")
    lines.append("")

  return "\n".join(lines)


def extract_pdf_from_bytes(pdf_bytes: bytes, source_name: str) -> str:
  """PDF バイトデータから Markdown を抽出"""
  lines = _build_pdf_markdown_header(source_name, source_name)
  with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
    lines.append(_extract_pages_to_markdown(pdf))
  return "\n".join(lines)


def extract_pdf_to_markdown(pdf_path: str, output_path: str | None = None) -> str:
  """ローカル PDF ファイルを Markdown 形式で抽出"""
  pdf_path_obj = Path(pdf_path)
  if output_path is None:
    output_path = str(pdf_path_obj.with_suffix(".md"))

  lines = _build_pdf_markdown_header(pdf_path_obj.name, pdf_path)
  with pdfplumber.open(pdf_path) as pdf:
    lines.append(_extract_pages_to_markdown(pdf))

  markdown_text = "\n".join(lines)
  Path(output_path).write_text(markdown_text, encoding="utf-8")

  return output_path


def download_pdf_from_url(url: str) -> bytes:
  """URL から PDF をダウンロード (Scrapling 使用)"""
  page = Fetcher.get(url)
  if not page.body:
    msg = f"レスポンスが空です: {url}"
    raise ValueError(msg)

  # Content-Type ヘッダーの確認
  content_type = page.headers.get("content-type", "")
  if "pdf" not in content_type.lower():
    logger.warning(
      "Content-Type が PDF ではありません: %s (URL: %s)", content_type, url
    )

  return page.body


def is_url(path: str) -> bool:
  """文字列が URL かどうかを判定"""
  parsed = urlparse(path)
  return parsed.scheme in ("http", "https")


def find_pdf_files(input_dir: str, *, recursive: bool = True) -> list[str]:
  """PDF ファイルを検索"""
  pdf_files: list[str] = []
  input_path = Path(input_dir)

  if input_path.is_file() and input_path.suffix.lower() == ".pdf":
    return [str(input_path)]

  if recursive:
    pdf_files.extend(str(p) for p in input_path.rglob("*.pdf"))
  else:
    pdf_files.extend(str(p) for p in input_path.glob("*.pdf"))

  return sorted(pdf_files)


def process_from_db(output_dir: str, limit: int | None = None) -> tuple[int, int, list]:
  """データベースの pdf_files テーブルから PDF をテキスト化"""
  engine = create_engine("sqlite:///data/subsidies.db")
  batch_size = 10  # バッチコミット用

  with Session(engine) as session:
    query = select(PdfFile).where(PdfFile.extracted_text_path.is_(None))
    if limit:
      query = query.limit(limit)
    pdfs = session.execute(query).scalars().all()

    total = len(pdfs)
    print(f"データベースから {total} 件の PDF URL を読み込みました")
    print(f"出力: {output_dir}")
    print()

    success_count = 0
    error_count = 0
    error_files = []

    for i, pdf_file in enumerate(pdfs, 1):
      url = pdf_file.url
      print(f"[{i}/{total}] 処理中: {url[:60]}")

      try:
        pdf_bytes = download_pdf_from_url(url)
        source_name = Path(urlparse(url).path).name or "download.pdf"
        markdown_text = extract_pdf_from_bytes(pdf_bytes, source_name)

        filename = Path(urlparse(url).path).stem + ".md"
        output_path = str(Path(output_dir) / filename)

        counter = 1
        while Path(output_path).exists():
          stem = Path(filename).stem
          output_path = str(Path(output_dir) / f"{stem}_{counter}.md")
          counter += 1

        Path(output_path).write_text(markdown_text, encoding="utf-8")

        # extracted_text_path を更新
        pdf_file.extracted_text_path = output_path

        print(f"  完了: {output_path}")
        success_count += 1

        # バッチコミット
        if success_count % batch_size == 0:
          session.commit()
          logger.debug("バッチコミット: %d 件処理済み", success_count)

      except (ValueError, OSError, RuntimeError) as e:
        print(f"  エラー: {e}")
        error_count += 1
        error_files.append((url, str(e)))

    # 最終コミット
    session.commit()

  return success_count, error_count, error_files


def process_from_url(url: str, output_dir: str) -> tuple[int, int, list]:
  """URL から PDF をダウンロードして処理"""
  print(f"URL からダウンロード: {url}")

  success_count = 0
  error_count = 0
  error_files = []

  try:
    pdf_bytes = download_pdf_from_url(url)
    source_name = Path(urlparse(url).path).name or "download.pdf"
    markdown_text = extract_pdf_from_bytes(pdf_bytes, source_name)

    filename = Path(urlparse(url).path).stem + ".md"
    output_path = str(Path(output_dir) / filename)

    Path(output_path).write_text(markdown_text, encoding="utf-8")
    print(f"完了: {output_path}")
    success_count += 1
  except (ValueError, OSError, RuntimeError) as e:
    print(f"エラー: {e}")
    error_count += 1
    error_files.append((url, str(e)))

  return success_count, error_count, error_files


def process_from_local(
  input_dir: str, output_dir: str, *, recursive: bool
) -> tuple[int, int, list]:
  """ローカルファイル/フォルダから処理"""
  if not Path(input_dir).exists():
    print(f"エラー: 入力パスが見つかりません: {input_dir}")
    sys.exit(1)

  pdf_files = find_pdf_files(input_dir, recursive=recursive)

  if not pdf_files:
    print(f"PDF ファイルが見つかりません: {input_dir}")
    sys.exit(0)

  print(f"入力: {input_dir}")
  print(f"出力: {output_dir}")
  print(f"対象ファイル数: {len(pdf_files)}")
  print()

  success_count = 0
  error_count = 0
  error_files = []

  for pdf_path in pdf_files:
    filename = Path(pdf_path).stem + ".md"
    output_path = str(Path(output_dir) / filename)

    counter = 1
    while Path(output_path).exists():
      name = Path(filename).stem
      output_path = str(Path(output_dir) / f"{name}_{counter}.md")
      counter += 1

    print(f"処理中: {pdf_path}")
    try:
      result_path = extract_pdf_to_markdown(pdf_path, output_path)
      print(f"  完了: {result_path}")
      success_count += 1
    except (ValueError, OSError, RuntimeError) as e:
      print(f"  エラー: {e}")
      error_count += 1
      error_files.append((pdf_path, str(e)))

  return success_count, error_count, error_files


def main() -> None:
  """メイン関数"""
  # ロギング設定
  logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  )

  parser = argparse.ArgumentParser(
    description="PDF ファイルを Markdown 形式に変換します",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
使用例:
  # データベースから
  uv run scripts/extract_pdfs.py --from-db --output ./output/

  # URL から直接
  uv run scripts/extract_pdfs.py \\
    --input https://example.com/doc.pdf --output ./output/

  # ローカルファイル/フォルダ
  uv run scripts/extract_pdfs.py --input ./pdfs/ --output ./output/
        """,
  )
  parser.add_argument(
    "--input",
    "-i",
    help="入力フォルダ、PDF ファイルのパス、または URL",
  )
  parser.add_argument(
    "--output",
    "-o",
    default="./output",
    help="出力フォルダのパス (デフォルト: ./output)",
  )
  parser.add_argument(
    "--no-recursive",
    action="store_true",
    help="サブフォルダを検索しない",
  )
  parser.add_argument(
    "--from-db",
    action="store_true",
    help="データベースの pdf_files テーブルから PDF をテキスト化",
  )
  parser.add_argument(
    "--limit",
    type=int,
    default=None,
    help="処理する最大件数(テスト用)",
  )

  args = parser.parse_args()

  if not args.input and not args.from_db:
    parser.error("--input または --from-db のいずれかを指定してください")

  output_dir = args.output
  if args.from_db or (args.input and not is_url(args.input)):
    Path(output_dir).mkdir(parents=True, exist_ok=True)

  success_count = 0
  error_count = 0
  error_files: list[tuple[str, str]] = []

  if args.from_db:
    success_count, error_count, error_files = process_from_db(
      output_dir, limit=args.limit
    )
  elif args.input:
    if is_url(args.input):
      success_count, error_count, error_files = process_from_url(args.input, output_dir)
    else:
      recursive = not args.no_recursive
      success_count, error_count, error_files = process_from_local(
        args.input, output_dir, recursive=recursive
      )

  print()
  print("=" * 50)
  print(f"処理完了: 成功 {success_count} 件, 失敗 {error_count} 件")

  if error_files:
    print("\nエラーが発生したファイル:")
    for path, error in error_files:
      print(f"  - {path}: {error}")


if __name__ == "__main__":
  main()
