"""PDF URLを抽出するスクリプト。

official_url が保存されている各補助金エントリのページから、
ページ内に存在するPDFファイルのURLを抽出して pdf_urls フィールドとして追加する。
"""

import json
import time
from pathlib import Path
from urllib.parse import urljoin

from scrapling.fetchers import Fetcher
from scrapling.parser import Selector

INPUT_FILE = Path(__file__).parent.parent / "subsidies_output.json"
OUTPUT_FILE = INPUT_FILE  # 上書き保存

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


def process_entry(entry: dict, index: int, total: int) -> tuple[bool, bool]:
  """1件のエントリを処理する。

  Args:
      entry: 補助金エントリの辞書。
      index: 現在のインデックス（1から始まる）。
      total: 総エントリ数。

  Returns:
      tuple: (成功フラグ, スキップフラグ) のタプル。
          - 成功フラグ: PDF URL抽出が成功したかどうか。
          - スキップフラグ: スキップだったかどうか。
  """
  name = entry.get("name", "不明")
  official_url = entry.get("official_url")

  # official_urlがない場合はスキップ
  if not official_url:
    print(f"  [{index}/{total}] スキップ(official_urlなし): {name}")
    return (False, True)

  # 既に pdf_urls があればスキップ
  if "pdf_urls" in entry:
    print(f"  [{index}/{total}] スキップ(既に処理済み): {name}")
    return (False, True)

  print(f"  [{index}/{total}] 取得中: {name}")
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
      entry["pdf_urls"] = pdf_urls

      if pdf_urls:
        print(f"    ✅ PDF数: {len(pdf_urls)}件")
      else:
        print("    ⚠️  PDFが見つかりませんでした")

    except (ConnectionError, TimeoutError) as e:
      print(f"    [リトライ {attempt}/{MAX_RETRIES}] 通信エラー: {e}")
      if attempt < MAX_RETRIES:
        time.sleep(RETRY_DELAY)
      else:
        entry["pdf_urls"] = []
        print(f"    ❌ 全リトライ失敗: {e}")
        return (False, False)
    else:
      return (True, False)

  return (False, False)


def main() -> None:
  """メイン処理。subsidies_output.json の各エントリに pdf_urls を追加する。"""
  # データ読み込み
  with INPUT_FILE.open("r", encoding="utf-8") as f:
    data = json.load(f)

  print(f"読み込み済みエントリ数: {len(data)}")
  print("処理開始: subsidies_output.json")
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

    # リクエスト間ウェイト
    if i < len(data):
      time.sleep(REQUEST_INTERVAL)

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
