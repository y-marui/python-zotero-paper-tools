# Specification

使い方と設定の説明は [README.md](../README.md) を参照。ここでは動作の定義を記す。

## Commands

| コマンド | 動作 |
|---|---|
| `paper-find <query>` | Better BibTeX で検索し、`citekey`・年・筆頭著者・タイトルをタブ区切りで出力。`--json` では `zotero_key` と `pdf_key` も出力 |
| `paper-note <citekey>` | citekey を完全一致で解決し、Vault に deck を作成してパスと `zotero://select` を出力 |
| `paper-link <citekey>` | deck を探し、Zotero のアイテムに `linked_url` 添付を 1 つ保つ |

## Exit Codes

| コード | 意味 |
|---|---|
| `0` | 成功 |
| `1` | 検索結果なし（`paper-find`） |
| `2` | エラー（Zotero に接続できない、citekey が見つからない・曖昧、Vault 未解決、deck が既にある など） |

## Vault Resolution

- ルート: `--vault` → 環境変数 `OBSIDIAN_VAULT_ROOT` → 設定ファイルの `vault_root`。
  いずれも無い場合は停止する
- 名前（`obsidian://` の `vault=`）: `--vault-name` → `OBSIDIAN_VAULT_NAME` →
  設定ファイルの `vault_name`（選んだルートが設定の `vault_root` と同一の場合のみ）→
  ルートのディレクトリ名

## Deck

- 保存先: `knowledge/research/papers/<citekey>.md`、`--private` では
  `private/knowledge/research/papers/<citekey>.md`
- 既存の deck があれば（どちらの領域でも）上書きせず停止する。もう一方の領域には作らない
- frontmatter: `citekey`、`zotero-key`、`doi`、`review_status: pending`、`marp: true` など
- 本文: `---` 区切りのスライド。図は `<citekey>-img/` に置き相対リンクで埋め込む
  （フォルダは `paper-note` では作らない）

## Zotero Local API

- 読み取りは `GET /api/...`、citekey の解決は Better BibTeX の `item.search`
- 書き込み（`POST` / `PATCH /api/users/0/items`）は、`POST /api/local/authorize`
  （body `{"appName": ...}`）で得たキーを使う。両方の呼び出しに `Zotero-Server-ID`
  ヘッダ（任意の GET 応答から取得）が必要
- 書き込みは応答が返らないまま成功することがあるため、失敗・タイムアウトは「不明」として
  扱い、子アイテムを最大 5 回、1 秒間隔で読み戻して確認してから失敗を報告する
- キーは macOS Keychain（service `python-zotero-paper-tools`、account
  `zotero-local-api`）に保管して再利用する。401/403 のときは再認可して置き換える。
  単回用のキー（`remember: false`）は保存せず警告する。`paper-link --forget-key` で削除する
- 書き込みに失敗した場合は、手で貼り付けられるよう URL を出力する

## paper-link Attachment Rules

- 添付は `obsidian://open?vault=<name>&file=<Vault 相対パス（拡張子なし）>`（スラッシュは
  エンコードしない）を指す `linked_url`
- 既存の添付とは、タイトルが "Obsidian deck" のもの、または URL が
  `obsidian://open?vault=<name>` で始まるもの
- URL が同じなら何も書かない（`exists:`）、異なれば PATCH で更新（`updated:`）、
  無ければ作成（`created:`）
- deck は通常領域と private の両方から探す。どちらにも無い、または両方にある場合はエラー
- PDF 添付がちょうど 1 つあるときだけ `zotero://open-pdf/...` を出力する
