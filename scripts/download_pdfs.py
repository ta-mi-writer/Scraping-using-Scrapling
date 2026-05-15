"""PDFファイルをダウンロードするスクリプト。

subsidies_output.json に登録されている PDF URL からファイルをダウンロードし、
pdf_files[].path にローカルパスを記録する。
"""

import argparse
import json
import time
from pathlib import Path
from urllib.parse import urlparse

from scrapling.fetchers import Fetcher

INPUT_FILE = Path(__file__).parent.parent / "subsidies_output.json"
OUTPUT_FILE = INPUT_FILE  # 上書き保存
PDF_DIR = Path(__file__).parent.parent / "pdfs"

# リトライ設定
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒


def extract_slug(detail_url: str) -> str:
  """detail_url からスラッグ（最後のパスセグメント）を抽出する。"""
  return detail_url.rstrip("/").split("/")[-1]


def extract_filename(url: str, index: int) -> str:
  """URL からファイル名を抽出する。抽出できない場合は連番のみを返す。"""
  path = urlparse(url).path
  name = Path(path).name
  if name and name.endswith(".pdf"):
    return f"{index:02d}_{name}"
  return f"{index:02d}.pdf"


def download_pdf(url: str, dest: Path) -> bool:
  """PDF ファイルをダウンロードして保存する。

  Args:
      url: ダウンロード元の URL。
      dest: 保存先のファイルパス。

  Returns:
      ダウンロードに成功したかどうか。
  """
  for attempt in range(1, MAX_RETRIES + 1):
    try:
      page = Fetcher.get(url)
      if not page.body:
        print(f"      [リトライ {attempt}/{MAX_RETRIES}] レスポンスが空")
        time.sleep(RETRY_DELAY)
        continue

      dest.write_bytes(page.body)
    except (ConnectionError, TimeoutError, OSError) as e:
      print(f"      [リトライ {attempt}/{MAX_RETRIES}] エラー: {e}")
      if attempt < MAX_RETRIES:
        time.sleep(RETRY_DELAY)

      return True

  return False


def process_entry(entry: dict, index: int, total: int) -> tuple[bool, bool]:
  """1件のエントリを処理する。

  Args:
      entry: 補助金エントリの辞書。
      index: 現在のインデックス（1から始まる）。
      total: 総エントリ数。

  Returns:
      tuple: (成功フラグ, スキップフラグ) のタプル。
  """
  name = entry.get("name", "不明")
  detail_url = entry.get("detail_url", "")

  # pdf_files がない場合はスキップ
  if "pdf_files" not in entry or not entry["pdf_files"]:
    print(f"  [{index}/{total}] スキップ(pdf_filesなし): {name}")
    return (False, True)

  # スラッグからディレクトリを決定
  slug = extract_slug(detail_url)
  dest_dir = PDF_DIR / slug
  dest_dir.mkdir(parents=True, exist_ok=True)

  print(f"  [{index}/{total}] 処理中: {name}")
  print(f"    ディレクトリ: {dest_dir}")

  downloaded_count = 0
  skipped_count = 0
  failed_count = 0

  for i, pdf_file in enumerate(entry["pdf_files"], 1):
    url = pdf_file["url"]

    # 既に path が設定済みならスキップ
    if pdf_file.get("path") is not None:
      skipped_count += 1
      continue

    filename = extract_filename(url, i)
    dest = dest_dir / filename

    print(f"    [{i}] ダウンロード中: {url}")

    if download_pdf(url, dest):
      pdf_file["path"] = str(dest)
      print(f"      ✅ 保存完了: {dest}")
      downloaded_count += 1
    else:
      print(f"      ❌ ダウンロード失敗: {url}")
      failed_count += 1

  print(
    f"    📊 成功: {downloaded_count}, スキップ: {skipped_count}, 失敗: {failed_count}"
  )

  return (failed_count == 0, False)


def parse_args() -> argparse.Namespace:
  """コマンドライン引数を解析する。"""
  parser = argparse.ArgumentParser(
    description="PDFファイルをダウンロードするスクリプト"
  )
  parser.add_argument(
    "--limit",
    type=int,
    default=None,
    help="処理する最大件数(最初のN件)",
  )
  parser.add_argument(
    "--indices",
    type=str,
    default=None,
    help="処理するエントリのインデックス(カンマ区切り、0始まり)",
  )
  return parser.parse_args()


def filter_data(data: list[dict], args: argparse.Namespace) -> list[dict]:
  """コマンドライン引数に基づいてデータをフィルタリングする。"""
  if args.indices:
    indices = [int(i) for i in args.indices.split(",")]
    return [data[i] for i in indices if 0 <= i < len(data)]
  if args.limit:
    return data[: args.limit]
  return data


def main() -> None:
  """メイン処理。"""
  args = parse_args()

  # データ読み込み
  with INPUT_FILE.open("r", encoding="utf-8") as f:
    data = json.load(f)

  # データフィルタリング
  data = filter_data(data, args)

  print(f"読み込み済みエントリ数: {len(data)}")
  print("処理開始: PDFダウンロード")
  print("=" * 60)

  success_count = 0
  skip_count = 0
  fail_count = 0

  for i, entry in enumerate(data, 1):
    success, skipped = process_entry(entry, i, len(data))
    if skipped:
      skip_count += 1
    elif success:
      success_count += 1
    else:
      fail_count += 1

  # 保存
  with OUTPUT_FILE.open("w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

  print()
  print("=" * 60)
  print(f"処理完了: {len(data)}件中")
  print(f"  ✅ 成功: {success_count}件")
  print(f"  ⏭️  スキップ: {skip_count}件")
  print(f"  ❌ 失敗: {fail_count}件")
  print(f"保存先: {OUTPUT_FILE}")


if __name__ == "__main__":
  main()
