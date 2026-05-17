"""PDF 一括抽出スクリプト.

- 指定フォルダ内の全 PDF を Markdown 形式で抽出
- サブフォルダも再帰的に検索可能

使い方:
    uv run scripts/extract_pdfs.py --input ./pdfs/ --output ./output/
    uv run scripts/extract_pdfs.py --input ./pdfs/73105/ --output ./output/
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pdfplumber

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


def extract_pdf_to_markdown(pdf_path: str, output_path: str | None = None) -> str:
  """PDF を Markdown 形式で抽出"""
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


def main() -> None:
  """メイン関数"""
  parser = argparse.ArgumentParser(
    description="PDF ファイルを Markdown 形式に変換します",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
    使用例:
      uv run scripts/extract_pdfs.py --input ./pdfs/ --output ./output/
      uv run scripts/extract_pdfs.py --input ./pdfs/73105/ --output ./output/
      uv run scripts/extract_pdfs.py --input ./pdfs/file.pdf --output ./output/
            """,
  )
  parser.add_argument(
    "--input",
    "-i",
    required=True,
    help="入力フォルダまたは PDF ファイルのパス",
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

  args = parser.parse_args()

  input_dir = args.input
  output_dir = args.output
  recursive = not args.no_recursive

  if not Path(input_dir).exists():
    print(f"エラー: 入力パスが見つかりません: {input_dir}")
    sys.exit(1)

  pdf_files = find_pdf_files(input_dir, recursive=recursive)

  if not pdf_files:
    print(f"PDF ファイルが見つかりません: {input_dir}")
    sys.exit(0)

  Path(output_dir).mkdir(parents=True, exist_ok=True)

  print(f"入力: {input_dir}")
  print(f"出力: {output_dir}")
  print(f"対象ファイル数: {len(pdf_files)}")
  print()

  success_count = 0
  error_count = 0
  error_files: list[tuple[str, str]] = []

  for pdf_path in pdf_files:
    filename = Path(pdf_path).stem + ".md"
    output_path = str(Path(output_dir) / filename)

    # 同名ファイルがある場合は連番を付与
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

  print()
  print("=" * 50)
  print(f"処理完了: 成功 {success_count} 件, 失敗 {error_count} 件")

  if error_files:
    print("\nエラーが発生したファイル:")
    for path, error in error_files:
      print(f"  - {path}: {error}")


if __name__ == "__main__":
  main()
