"""個別補助金ページから「公式公募ページのURL」を取得し、

subsidies_output.json に追加するスクリプト。

subscrapies_output.json の各エントリの detail_url にアクセスし、
「公式公募ページ」のリンクを抽出して official_url として保存する。
"""

import json
import re
import time
from pathlib import Path

from scrapling.fetchers import Fetcher
from scrapling.parser import Selector

INPUT_FILE = Path(__file__).parent.parent / "subsidies_output.json"
OUTPUT_FILE = INPUT_FILE  # 上書き保存

# リトライ設定
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒

# リクエスト間のウェイト（秒）
REQUEST_INTERVAL = 2


def extract_official_url(html: str) -> str | None:
  """個別補助金ページのHTMLから「公式公募ページ」のURLを抽出する。

  HTML構造:
      <tr><th>公式公募ページ</th>
          <td>
              <a href="https://..." target="_blank">...</a>
          </td>
      </tr>
  """
  sel = Selector(html)

  # テーブルの全行を走査
  rows = sel.css("table.p-subsidy__table tr")
  for row in rows:
    th = row.css("th::text").get()
    if th and "公式公募ページ" in th:
      link = row.css("td a::attr(href)").get()
      if link:
        return link

  # CSSセレクタで見つからなかった場合、テキスト検索でフォールバック
  if "公式公募ページ" in html:
    # <th>公式公募ページ</th>...<a href="URL"> のパターン
    match = re.search(
      r'公式公募ページ.*?<a\s+href="([^"]+)"',
      html,
      re.DOTALL,
    )
    if match:
      return match.group(1)

  return None


def process_entry(entry: dict, index: int, total: int) -> bool:
  """1件のエントリを処理する。成功したらTrue、スキップしたらFalseを返す。"""
  name = entry.get("name", "不明")
  detail_url = entry.get("detail_url")

  # 既に official_url があればスキップ
  if entry.get("official_url"):
    print(f"  [{index}/{total}] スキップ(既に取得済み): {name}")
    return False

  if not detail_url:
    print(f"  [{index}/{total}] detail_url がないためスキップ: {name}")
    return False

  print(f"  [{index}/{total}] 取得中: {name}")
  print(f"    URL: {detail_url}")

  # リトライ付きで取得
  for attempt in range(1, MAX_RETRIES + 1):
    try:
      page = Fetcher.get(detail_url)
      html = page.html_content

      if not html:
        print(f"    [リトライ {attempt}/{MAX_RETRIES}] HTMLが空")
        time.sleep(RETRY_DELAY)
        continue

      official_url = extract_official_url(html)

      if official_url:
        entry["official_url"] = official_url
        print(f"    ✅ official_url: {official_url}")
      else:
        entry["official_url"] = None
        print("    ⚠️  official_urlが見つかりませんでした")

    except (ConnectionError, TimeoutError) as e:
      print(f"    [リトライ {attempt}/{MAX_RETRIES}] 通信エラー: {e}")
      if attempt < MAX_RETRIES:
        time.sleep(RETRY_DELAY)
      else:
        entry["official_url"] = None
        print(f"    ❌ 全リトライ失敗: {e}")
        return False
    else:
      return True

  return False


def main() -> None:
  """メイン処理。subsidies_output.json の各エントリに official_url を追加する。"""
  # データ読み込み
  with INPUT_FILE.open("r", encoding="utf-8") as f:
    data = json.load(f)

  print(f"読み込み済みエントリ数: {len(data)}")
  print(f"処理開始: {INPUT_FILE.name}")
  print("=" * 60)

  success_count = 0
  skip_count = 0
  fail_count = 0

  for i, entry in enumerate(data, 1):
    result = process_entry(entry, i, len(data))
    if result is True:
      success_count += 1
    elif result is False:
      # スキップ or 失敗
      if entry.get("official_url") is not None and entry.get("official_url") != "":
        # スキップした場合（既に取得済み）
        skip_count += 1
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
  print(f"  ✅ 取得成功: {success_count}件")
  print(f"  ⏭️  スキップ: {skip_count}件")
  print(f"  ❌ 失敗: {fail_count}件")
  print(f"保存先: {OUTPUT_FILE}")


if __name__ == "__main__":
  main()
