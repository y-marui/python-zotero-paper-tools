# Architecture

## Overview

標準ライブラリのみで動く 3 つの CLI（`paper-find` / `paper-note` / `paper-link`）。
Zotero のローカル API だけを使い、Obsidian Vault のファイルを読み書きする。

## Modules

| モジュール | 責務 |
|---|---|
| `find` | 検索結果の整形出力（`--json` では `zotero_key` と `pdf_key` を付ける） |
| `note` | deck（Marp 形式の Markdown）の生成と Vault への保存。上書き禁止 |
| `link` | deck の場所の特定、`obsidian://` URL の生成、添付の作成・更新・読み戻し確認 |
| `zotero` | Better BibTeX JSON-RPC による検索と citekey の解決（読み取り専用） |
| `localapi` | `/api` の読み取りと、認可キーを用いた書き込み。`Zotero-Server-ID` ヘッダの扱い |
| `keystore` | macOS Keychain へのキーの保存・取得・削除（`security` コマンド） |
| `config` | `--vault` / 環境変数 / 設定ファイルによる Vault ルートと名前の解決 |

## Dependency Direction

~~~
find / note / link  ->  localapi / zotero / config / keystore
~~~

逆依存・循環依存は禁止。`zotero` は `localapi` に依存しない（`localapi` が `zotero` の
定数とエラー型を使う）。

## Data Flow

1. `paper-note`: citekey を Better BibTeX で解決 → Vault 内に deck が無いことを確認 →
   `knowledge/research/papers/<citekey>.md`（`--private` では `private/` 配下）を作成
2. `paper-link`: citekey を解決 → deck を通常領域と private の両方から探す →
   アイテムの子アイテムを読む → 既存の添付を更新 / 新規作成 → 読み戻して確認

## Design Decisions

- Zotero Web API は使わない（ローカルのみ）。理由: 認証情報をネットワークに出さないため
- 実行時の依存を持たない。理由: 配布と保守を単純に保つため
- API キーは Keychain のみ。理由: ファイルやログに残さないため
