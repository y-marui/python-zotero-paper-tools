# python-zotero-paper-tools

> **このファイルは正本（日本語版）です。**
> 英語版（参照）は [README.md](README.md) を参照してください。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/y-marui/python-zotero-paper-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/y-marui/python-zotero-paper-tools/actions/workflows/ci.yml)
[![Charter Check](https://github.com/y-marui/python-zotero-paper-tools/actions/workflows/dev-charter-check.yml/badge.svg)](https://github.com/y-marui/python-zotero-paper-tools/actions/workflows/dev-charter-check.yml)
[![GitHub Sponsors](https://img.shields.io/github/sponsors/y-marui?style=social)](https://github.com/sponsors/y-marui)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-donate-yellow.svg)](https://www.buymeacoffee.com/y.marui)

| 項目 | 内容 |
|---|---|
| 対象 | Zotero と Obsidian を使う人向けの CLI ツール |
| チーム | 個人 |
| 言語 | 英語（コード・README）／日本語（正本の README と AI_CONTEXT） |
| ライセンス | MIT |
| AI ツール | Claude Code / GitHub Copilot / Gemini CLI |
| 実行環境 | Python 3.11 以上（標準ライブラリのみ）、macOS（Keychain） |

[Zotero](https://www.zotero.org/) の論文と、Obsidian Vault 内のスライド形式の
Markdown 議論ノート（「deck」）をつなぐ小さな CLI ツール群です。

Zotero へは**ローカル API のみ**（`http://localhost:23119`）と
[Better BibTeX](https://retorque.re/zotero-better-bibtex/) の JSON-RPC を通じて
アクセスします。Zotero Web API は使いません。

## Commands

| コマンド | 状態 | 内容 |
| --- | --- | --- |
| `paper-find <query>` | 利用可 | Zotero を検索して citekey を表示（`--json` で `zotero_key` と `pdf_key` も出力） |
| `paper-note <citekey>` | 利用可 | Vault に deck を作成 |
| `paper-link <citekey>` | 利用可 | Zotero のアイテムに `obsidian://` リンクを添付 |

必要なもの: Better BibTeX を入れた Zotero を起動していること。

## Install

~~~sh
uv tool install .
~~~

## Configuration

個人設定はリポジトリの外に置きます。Vault の**ルート**は次の順で解決し、
どれも無ければコマンドは停止します。

1. `--vault DIR`
2. 環境変数 `OBSIDIAN_VAULT_ROOT`
3. `~/.config/zotero-paper-tools/config.toml` の `vault_root`
   （パスは `ZOTERO_PAPER_TOOLS_CONFIG` で変更可能）

Vault の**名前**（`obsidian://` リンクの `vault=`）は次の順で解決します。

1. `--vault-name NAME`（`paper-note`、`paper-link`）
2. 環境変数 `OBSIDIAN_VAULT_NAME`
3. 設定ファイルの `vault_name`（**選んだルートが設定の `vault_root` と同じ場合のみ**。
   `~` の展開とシンボリックリンクの解決後に比較するので、`~/v`、`/Users/me/v/`、
   そのシンボリックリンクは同じルートとみなされます）
4. ルートのディレクトリ名

ルートを上書きしても、別のルート用の名前を黙って使うことはありません。
Obsidian に登録した名前がディレクトリ名と異なる場合は `vault_name` を設定してください。

~~~toml
# ~/.config/zotero-paper-tools/config.toml
vault_root = "~/path/to/vault"   # 相対パスは $HOME 基準
vault_name = "my-vault"          # Obsidian に登録した名前（省略時はディレクトリ名）
~~~

## Usage

~~~sh
paper-find "spike-frequency adaptation"     # citekey・年・筆頭著者・タイトル（タブ区切り）
paper-find --json --limit 5 probabilistic   # JSON 出力

paper-note xu_probabilistic_2025            # --private で private 領域に作成
paper-link xu_probabilistic_2025
~~~

`paper-note` は Vault に `knowledge/research/papers/<citekey>.md`
（`--private` では `private/knowledge/research/papers/<citekey>.md`）を作り、
ファイルパスと `zotero://select/library/items/<itemKey>` を出力します。上書きはせず、
どちらの領域にでも同じ citekey の deck が既にあれば停止します（もう一方の領域には作りません）。

ノートには frontmatter（`citekey`、`zotero-key`、`doi`、`review_status: pending`）、
アイテムへの `zotero://select` リンク、`---` 区切りのスライド（数式は `$...$`）が入ります。
図は `<citekey>-img/` に置き、相対リンクで埋め込みます。雛形には埋め込み方を示す HTML
コメントだけがあり、壊れた画像リンクは含みません。`<citekey>-img/` フォルダは
`paper-note` では作らないので、最初の画像を保存するときに作ってください。表示には
Marp のプラグイン（Marp Inline Preview）を使い、frontmatter に `marp: true` が必要です
（雛形は `paginate` と、文字と図をスライドに収める `style` も設定します）。
Obsidian コアの Slides でも `---` 区切りのスライドを表示できますが、内容があふれやすくなります。

`paper-link` は deck を両方の領域から探し（どちらにも無い、または両方にある場合はエラー）、
アイテムの下に `linked_url` 添付を 1 つだけ保ちます。URL は
`obsidian://open?vault=<name>&file=<Vault 相対パス、拡張子なし>`（スラッシュはエンコードしない）です。
既存の添付とは、タイトルが "Obsidian deck" のもの、または URL が
`obsidian://open?vault=<name>` で始まるものです。URL が同じなら何も書かず（`exists:`）、
異なれば PATCH で更新し（`updated:`。例: deck を領域間で移動した場合）、無ければ作成します
（`created:`）。更新も作成と同じ認可・Keychain のキー・読み戻し確認を使います。出力:

~~~
created: <attachment key>        # または updated: / exists:
item: zotero://select/library/items/<itemKey>
pdf: zotero://open-pdf/library/items/<pdfKey>?page=1   # PDF がちょうど 1 つのときのみ
deck: obsidian://open?vault=...&file=...
~~~

書き込みに失敗した場合は、Zotero に手で貼り付けられるよう URL を出力します。

`paper-find --json` は各結果に `zotero_key` と `pdf_key`（PDF 添付のキー。PDF 添付が
ちょうど 1 つでなければ `null`）を付けます。

終了コード: `0` 成功、`1` 検索結果なし、`2` エラー（Zotero に接続できない、citekey が
見つからない・曖昧、Vault 未解決、ノートが既にある）。

## Notes on Zotero

- `zotero://open-pdf` リンクには PDF 添付のキーが必要です。`paper-find --json` の
  `pdf_key` か `paper-link` の `pdf:` 行から取ってください（`paper-note` は調べません）。
- citekey からアイテムを引く方法は `item.search` だけなので、`paper-note` は検索し、
  citekey の完全一致を要求します。
- ローカル API への書き込み（`POST /api/users/0/items`）には、
  `POST /api/local/authorize`（body `{"appName": ...}`）で得たキーが必要で、どちらの
  呼び出しにも `Zotero-Server-ID` ヘッダ（任意の GET 応答から取得）が必要です。書き込みは
  HTTP 応答が返らないまま成功することがあるため、`paper-link` は失敗やタイムアウトを
  「不明」とみなし、失敗を報告する前にアイテムの子アイテムを読み戻します（最大 5 回、1 秒間隔）。
- キーの保管: `/api/local/authorize` で得たキーは macOS Keychain
  （service `python-zotero-paper-tools`、account `zotero-local-api`）に保管して再利用します。
  表示もファイル保存もしません。Zotero が拒否（401/403）した場合、`paper-link` は再認可して
  置き換えます。Zotero が単回用のキー（`remember: false`）を返した場合は保存せず警告します。
  保管したキーは `paper-link --forget-key` で削除できます。`security` コマンドはキーを
  引数で受け取るため、保存の一瞬だけ `ps` に見えます。
- 初回の認可ダイアログでは「常に許可」を選んでください。キーが有効なまま残り、以後ダイアログは
  出ません。キーはライブラリにもこのツールにも限定されておらず、持っていれば誰でもローカルの
  Zotero API に書き込める点に注意してください。取り消しは Zotero の Settings > Advanced
  （保管されたキーの一覧）で行い、Keychain のコピーは `paper-link --forget-key` で削除します。
- Zotero でリンクをクリックすると、毎回「Obsidian でリンクを開きますか？」の確認が出ます
  （Zotero 10.0.6）。

## Development

~~~sh
make install   # uv sync
make all       # ruff check + mypy（strict）+ pytest
~~~

| コマンド | 内容 |
|---|---|
| `make install` | `uv sync` |
| `make lint` | `ruff check .` |
| `make format` | `ruff format .` |
| `make type` | `mypy src` |
| `make test` | `pytest` |
| `make all` | lint + type + test |
| `make update-charter` | dev-charter の subtree を更新 |

開発フローは [CONTRIBUTING.md](CONTRIBUTING.md)、AI ツール向けの文脈は
[AI_CONTEXT.md](AI_CONTEXT.md) を参照してください。

## License

MIT License — [LICENSE](LICENSE) を参照

---
*この文書には英語版 [README.md](README.md) があります。編集時は同一コミットで更新してください。*
