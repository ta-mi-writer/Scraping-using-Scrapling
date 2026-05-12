"""関数をテストする"""

from tryke import expect, test

from scripts.test_function import the_function_you_want_to_test


@test
async def test_scraping_result_content() -> None:
  """戻り値を検証する"""
  result = await the_function_you_want_to_test()
  expect(result).to_equal("Shop")
