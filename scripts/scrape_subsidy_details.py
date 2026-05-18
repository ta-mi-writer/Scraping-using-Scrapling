"""個別補助金ページから「公式公募ページのURL」を取得し、

subsidies テーブルの official_url に保存するスクリプト。

subsidies テーブルの各レコードの detail_url にアクセスし、
「公式公募ページ」のリンクを抽出して official_url として保存する。
"""

import re
import time

from models import Subsidy
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

  # CSSセレクタで見つからなかった場合、正規表現でフォールバック
  if "公式公募ページ" in html:
    match = re.search(
      r'公式公募ページ.*?<a\s+href="([^"]+)"',
      html,
      re.DOTALL,
    )
    if match:
      return match.group(1)

  return None


def process_subsidy(subsidy: Subsidy, index: int, total: int) -> bool:
  """1件の補助金レコードを処理する。成功したらTrue、スキップしたらFalseを返す。"""
  name = subsidy.name
  detail_url = subsidy.detail_url

  # 既に official_url があればスキップ
  if subsidy.official_url:
    print(f"  [{index}/{total}] スキップ(既に取得済み): {name[:40]}")
    return False

  if not detail_url:
    print(f"  [{index}/{total}] detail_url がないためスキップ: {name[:40]}")
    return False

  print(f"  [{index}/{total}] 取得中: {name[:40]}")
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
        subsidy.official_url = official_url
        print(f"    ✅ official_url: {official_url}")
      else:
        subsidy.official_url = None
        print("    ⚠️  official_urlが見つかりませんでした")

    except (ConnectionError, TimeoutError) as e:
      print(f"    [リトライ {attempt}/{MAX_RETRIES}] 通信エラー: {e}")
      if attempt < MAX_RETRIES:
        time.sleep(RETRY_DELAY)
      else:
        subsidy.official_url = None
        print(f"    ❌ 全リトライ失敗: {e}")
        return False
    else:
      return True

  return False


def main() -> None:
  """メイン処理。subsidies テーブルの各レコードに official_url を追加する。"""
  engine = create_engine(f"sqlite:///{DB_PATH}")

  with Session(engine) as session:
    # official_url が未設定のレコードを取得
    subsidies = (
      session.execute(select(Subsidy).where(Subsidy.official_url.is_(None)))
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
      result = process_subsidy(subsidy, i, total)
      if result is True:
        success_count += 1
      elif result is False:
        if subsidy.official_url is not None:
          skip_count += 1
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
  print(f"  ✅ 取得成功: {success_count}件")
  print(f"  ⏭️  スキップ: {skip_count}件")
  print(f"  ❌ 失敗: {fail_count}件")


if __name__ == "__main__":
  main()
