"""補助金ポータルから補助金情報を取得するスクリプト。

取得事項:
    - 補助金名
    - 詳細URL
    - 申請期間 (締め切り含む)
    - 上限金額

補助金ポータルの検索結果ページをスクレイピングし、
ページネーション対応で全件の情報を取得する。
"""

from __future__ import annotations

import asyncio
import json
import re
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING

from scrapling.fetchers import Fetcher
from scrapling.parser import Selector

if TYPE_CHECKING:
  from scrapling.engines.toolbelt.custom import Response


# === 設定 ===
BASE_URL = "https://hojyokin-portal.jp/subsidies/list"
QUERY_PARAMS = "pref_id[0]=1&city_id[0]=87&status[0]=2&status[1]=1"
OUTPUT_FILE = Path(__file__).parent.parent / "subsidies_output.json"


def build_url(page: int = 1) -> str:
  """ページ番号に応じたURLを構築する。

  Args:
      page: ページ番号 (1始まり)。

  Returns:
      構築されたURL文字列。
  """
  if page == 1:
    return f"{BASE_URL}?{QUERY_PARAMS}"
  return f"{BASE_URL}?{QUERY_PARAMS}&page={page}"


def parse_amount(text: str) -> int | None:
  """上限金額の文字列から数値(円)を抽出する。

  Args:
      text: 金額を含む文字列 (例: "200万円", "1,000万円")。

  Returns:
      int: 抽出された金額(円単位)。取得できない場合はNone。
  """
  match = re.search(r"([\d,]+)万円", text)
  if match:
    amount_str = match.group(1).replace(",", "")
    return int(amount_str) * 10_000
  return None


def extract_subsidy_items(page: Response) -> list[dict]:
  """ページから補助金アイテムを抽出する。

  Scrapling の Selector で HTML をパースし、
  BeautifulSoup なしで全フィールドを抽出する。

  HTML構造: 各補助金カードは <div class="c-card-hojokin"> で囲まれている。
  - 補助金名: <h3 class="c-card-hojokin__title"> 内のテキスト
  - 詳細URL: <a class="c-card-hojokin__wrap" href="..."> の href
  - 公募ステータス: <div class="c-card-hojokin__status"> span 内のテキスト
  - 申請期間: <div class="c-card-hojokin__date"> span 内のテキスト
  - 上限金額: <span class="num"> 内の数値

  Args:
      page: ScraplingのResponseオブジェクト。

  Returns:
      補助金情報の辞書リスト。
  """
  html = page.html_content
  if not html:
    print("  [警告] HTMLコンテンツを取得できませんでした。")
    return []

  sel = Selector(html)
  cards = sel.css("div.c-card-hojokin")

  results: list[dict] = []

  for card in cards:
    # --- 詳細URL ---
    detail_url = card.css("a.c-card-hojokin__wrap::attr(href)").get()
    if detail_url and not detail_url.startswith("http"):
      detail_url = f"https://hojyokin-portal.jp{detail_url}"

    # --- 補助金名 ---
    name_raw = card.css("h3.c-card-hojokin__title::text").get()
    name = re.sub(r"\s+", "", name_raw.strip()) if name_raw else None

    # --- ステータス ---
    status_raw = card.css("div.c-card-hojokin__status span::text").get()
    status = None
    if status_raw:
      status_text = status_raw.strip()
      m = re.search(
        r"(公開中|公募中|公募予定|募集終了|締め切り済み|終了|受付中|公開予定)",
        status_text,
      )
      status = m.group(1) if m else status_text

    # --- 申請期間 ---
    application_period = None
    date_spans = card.css("div.c-card-hojokin__date span::text").getall()
    for span_text in date_spans:
      t = span_text.strip()
      if "~" in t or "202" in t:
        application_period = t
        break

    # --- 上限金額 ---
    upper_limit_yen = None
    price_raw = card.css("div.c-card-hojokin__price span.num::text").get()
    if price_raw:
      cleaned = price_raw.replace(",", "").strip()
      with suppress(ValueError):
        upper_limit_yen = int(cleaned) * 10_000

    results.append(
      {
        "name": name,
        "detail_url": detail_url,
        "application_period": application_period,
        "upper_limit_yen": upper_limit_yen,
        "status": status,
      }
    )

  return results


def extract_total_pages(page: Response) -> int:
  """ページネーションから最終ページ番号を取得する。"""
  candidates = page.css(".page-numbers::text").getall()

  if not candidates:
    html = page.html_content
    if html:
      matches = re.findall(r'class="page-numbers"[^>]*>([^<]*)</', html)
      candidates = matches

  try:
    page_numbers = [int(str(p).strip()) for p in candidates if str(p).strip().isdigit()]
    return max(page_numbers) if page_numbers else 1
  except ValueError:
    return 1


async def scrape_all_pages() -> list[dict]:
  """全ページの補助金情報を取得する。"""
  first_url = build_url(page=1)
  print(f"最初のページを取得中: {first_url}")
  first_page = Fetcher.get(first_url)

  total_pages = extract_total_pages(first_page)
  print(f"総ページ数: {total_pages}")

  all_results: list[dict] = []
  all_results.extend(extract_subsidy_items(first_page))
  print(f"  ページ 1/{total_pages}: {len(all_results)}件")

  for page_num in range(2, total_pages + 1):
    url = build_url(page=page_num)
    print(f"  ページ {page_num}/{total_pages} を取得中...")
    page = Fetcher.get(url)
    items = extract_subsidy_items(page)
    print(f"    {len(items)}件取得")
    all_results.extend(items)

  return all_results


def main() -> None:
  """メイン処理。"""
  results = asyncio.run(scrape_all_pages())

  print(f"\n{'=' * 60}")
  print(f"取得完了: 合計 {len(results)}件")
  print(f"{'=' * 60}\n")

  for i, item in enumerate(results, 1):
    print(f"[{i}] {item['name']}")
    print(f"    詳細URL   : {item['detail_url']}")
    print(f"    申請期間   : {item['application_period']}")
    upper_limit = (
      f"{item['upper_limit_yen']:,}円" if item["upper_limit_yen"] else "未掲載"
    )
    print(f"    上限金額   : {upper_limit}")
    print(f"    ステータス : {item['status']}")
    print()

  with OUTPUT_FILE.open("w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
  print(f"結果を {OUTPUT_FILE} に保存しました。")


if __name__ == "__main__":
  main()
