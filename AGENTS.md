プログラミングコード作成時：

- まずは詳細なコーディングのプランを立てる
  - プランを立て終わったら、一旦ユーザーにターンを回す
- コードはRuffのlintに準拠する（`pyproject.toml`を参考にする）
- 基本的にはPythonの標準モジュールを使用する
- スクレイピングにはScraplingというライブラリを使用する
  - https://github.com/D4Vinci/Scrapling
- コードが完成したらRuffのエラーを確認する
- コードを実行するときは`uv run`を使用する
