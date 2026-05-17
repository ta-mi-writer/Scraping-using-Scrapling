r"""PDF 一括抽出スクリプト.

- 指定フォルダ内の全 PDF を Markdown 形式に変換
- URL を直接指定して PDF をダウンロードして変換することも可能
- サブフォルダも再帰的に検索可能

使い方:
    # ローカルファイル/フォルダ
    uv run scripts/extract_pdfs.py --input ./pdfs/ --output ./output/
    uv run scripts/extract_pdfs.py --input ./pdfs/73105/ --output ./output/

    # URL から直接
    uv run scripts/extract_pdfs.py \\
      --input https://example.com/doc.pdf --output ./output/

    # subsidies_output.json の pdf_files から一括処理
    uv run scripts/extract_pdfs.py --from-json subsidies_output.json --output ./output/
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import pdfplumber
from scrapling.fetchers import Fetcher

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


def extract_pdf_from_bytes(pdf_bytes: bytes, source_name: str) -> str:
  """PDF バイトデータから Markdown を抽出"""
  lines = []
  lines.append(f"# {source_name}")
  lines.append("")
  lines.append(f"- 抽出日時: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}")
  lines.append(f"- ソース: {source_name}")
  lines.append("")
  lines.append("---")
  lines.append("")

  with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
    lines.append(f"**総ページ数: {len(pdf.pages)}**")
    lines.append("")

    for i, page in enumerate(pdf.pages):
      lines.append(f"## ページ {i + 1}")
      lines.append("")

      page_content = extract_page_content(page)
      if page_content.strip():
        lines.append(page_content)
      else:
        lines.append("*(このページには抽出可能なコンテンツがありません)*")

      lines.append("")
      lines.append("---")
      lines.append("")

  return "\n".join(lines)


def extract_pdf_to_markdown(pdf_path: str, output_path: str | None = None) -> str:
  """ローカル PDF ファイルを Markdown 形式で抽出"""
  pdf_path_obj = Path(pdf_path)
  if output_path is None:
    output_path = str(pdf_path_obj.with_suffix(".md"))

  lines = []
  lines.append(f"# {pdf_path_obj.name}")
  lines.append("")
  lines.append(f"- 抽出日時: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}")
  lines.append(f"- ファイルパス: {pdf_path}")
  lines.append("")
  lines.append("---")
  lines.append("")

  with pdfplumber.open(pdf_path) as pdf:
    lines.append(f"**総ページ数: {len(pdf.pages)}**")
    lines.append("")

    for i, page in enumerate(pdf.pages):
      lines.append(f"## ページ {i + 1}")
      lines.append("")

      page_content = extract_page_content(page)
      if page_content.strip():
        lines.append(page_content)
      else:
        lines.append("*(このページには抽出可能なコンテンツがありません)*")

      lines.append("")
      lines.append("---")
      lines.append("")

  markdown_text = "\n".join(lines)
  Path(output_path).write_text(markdown_text, encoding="utf-8")

  return output_path


def download_pdf_from_url(url: str) -> bytes:
  """URL から PDF をダウンロード (Scrapling 使用)"""
  page = Fetcher.get(url)
  if not page.body:
    msg = f"レスポンスが空です: {url}"
    raise ValueError(msg)
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


def extract_pdf_urls_from_json(json_path: str) -> list[dict]:
  """subsidies_output.json から PDF URL を抽出"""
  with Path(json_path).open("r", encoding="utf-8") as f:
    data = json.load(f)

  results = []
  for entry in data:
    if "pdf_files" not in entry or not entry["pdf_files"]:
      continue
    for pdf_file in entry["pdf_files"]:
      url = pdf_file.get("url")
      if url:
        results.append(
          {
            "url": url,
            "name": entry.get("name", "不明"),
            "detail_url": entry.get("detail_url", ""),
          }
        )
  return results


def process_from_json(json_path: str, output_dir: str) -> tuple[int, int, list]:
  """JSON から PDF URL を読み込んで一括処理"""
  pdf_entries = extract_pdf_urls_from_json(json_path)
  print(f"JSON から {len(pdf_entries)} 件の PDF URL を読み込みました")
  print(f"出力: {output_dir}")
  print()

  success_count = 0
  error_count = 0
  error_files = []

  for i, entry in enumerate(pdf_entries, 1):
    url = entry["url"]
    name = entry["name"]
    print(f"[{i}/{len(pdf_entries)}] 処理中: {name}")
    print(f"  URL: {url}")

    try:
      pdf_bytes = download_pdf_from_url(url)
      markdown_text = extract_pdf_from_bytes(pdf_bytes, name)

      filename = Path(urlparse(url).path).stem + ".md"
      if not filename.endswith(".md"):
        filename = f"{name[:50]}.md"
      output_path = str(Path(output_dir) / filename)

      counter = 1
      while Path(output_path).exists():
        stem = Path(filename).stem
        output_path = str(Path(output_dir) / f"{stem}_{counter}.md")
        counter += 1

      Path(output_path).write_text(markdown_text, encoding="utf-8")
      print(f"  完了: {output_path}")
      success_count += 1
    except (ValueError, OSError, RuntimeError) as e:
      print(f"  エラー: {e}")
      error_count += 1
      error_files.append((url, str(e)))

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
  parser = argparse.ArgumentParser(
    description="PDF ファイルを Markdown 形式に変換します",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
使用例:
  # ローカルファイル/フォルダ
  uv run scripts/extract_pdfs.py --input ./pdfs/ --output ./output/
  uv run scripts/extract_pdfs.py --input ./pdfs/73105/ --output ./output/

  # URL から直接
  uv run scripts/extract_pdfs.py \\
    --input https://example.com/doc.pdf --output ./output/

  # subsidies_output.json の pdf_files から一括処理
  uv run scripts/extract_pdfs.py --from-json subsidies_output.json --output ./output/
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
    "--from-json",
    type=str,
    help="subsidies_output.json から PDF URL を読み込んで一括処理",
  )

  args = parser.parse_args()

  if not args.input and not args.from_json:
    parser.error("--input または --from-json のいずれかを指定してください")

  output_dir = args.output
  Path(output_dir).mkdir(parents=True, exist_ok=True)

  success_count = 0
  error_count = 0
  error_files: list[tuple[str, str]] = []

  if args.from_json:
    success_count, error_count, error_files = process_from_json(
      args.from_json, output_dir
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
