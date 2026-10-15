# AI_CONTEXT.md

> このファイルは Claude Code・GitHub Copilot など AI ツールが唯一参照するコンテキストファイルです。
> セッション開始時に必ず読み込んでください。

---

## AI Reference Order

AI はタスク開始時に以下の順で参照する:

1. `README.md`（概要・セットアップ・使い方）
2. `CONTRIBUTING.md`（PR・Issue ルール・開発フロー）

必要に応じて以下を参照する（順不同）:

- `docs/architecture.md`（モジュール構造・データフロー）
- `docs/file-map.md`（ファイルレベルの依存関係 ※古い場合は探索して更新する）
- `docs/specification.md`（コマンド仕様・終了コード・Zotero API の扱い）
- `docs/ui-design.md`（CLI のため UI 設計は該当なし）

---

## Project Overview

**目的:** ChatGPT などで行った論文の議論を Obsidian の Markdown（スライド形式の
「deck」）に保存し、その deck への `obsidian://` リンクを Zotero のアイテムに
添付する CLI ツール群（`paper-find` / `paper-note` / `paper-link`）。

**チーム規模:** 個人開発（1 人）。

**技術スタック:**

| 項目 | 内容 |
|---|---|
| 言語 | Python 3.11 以上（標準ライブラリのみ。実行時の依存なし） |
| パッケージ管理 | uv（`uv.lock` をコミットする） |
| Lint / Format | ruff（line-length 88） |
| 型チェック | mypy（strict） |
| テスト | pytest（`tests/unit/`、`tests/integration/`） |
| ビルド | hatchling |

バージョン管理・パッケージ管理・Lint/Format・型チェックの一般方針は
[docs/dev-charter/topics/python/PYTHON_DEV_ENV.md](docs/dev-charter/topics/python/PYTHON_DEV_ENV.md)
を、CLI の実装方針は
[docs/dev-charter/topics/python/PYTHON_CLI.md](docs/dev-charter/topics/python/PYTHON_CLI.md)
を参照。

**主要ディレクトリ:**

~~~
src/zotero_paper_tools/   # パッケージ本体
tests/unit/               # 単体テスト（偽の Zotero サーバーを立てて検証する）
tests/integration/        # 統合テスト（現状なし）
docs/                     # 仕様書・ナレッジベース
docs/dev-charter/         # 開発憲章（git subtree、full ブランチ）
~~~

**モジュール一覧:**

| モジュール | 役割 |
|---|---|
| `find` | `paper-find`: 検索して citekey を表示 |
| `note` | `paper-note`: Vault に deck（Markdown）を作成 |
| `link` | `paper-link`: Zotero のアイテムに `obsidian://` 添付を作成・更新 |
| `zotero` | Better BibTeX JSON-RPC による読み取り（citekey の解決） |
| `localapi` | Zotero ローカル API（`/api`）の読み取りと認可付き書き込み |
| `keystore` | macOS Keychain への API キー保管（`security` コマンド経由） |
| `config` | 個人設定と Vault の解決 |

**AI コンテキスト優先順位:**
1. タスクコンテキスト（Issue / Pull Request）
2. プロジェクトコンテキスト（`AI_CONTEXT.md`・プロジェクトドキュメント）
3. 開発憲章（`docs/dev-charter/`）
4. グローバルコンテキスト

---

## Applied Charter Principles

### Pre-Coding Checklist

不明・未定の項目があれば**作業前に 1 回でまとめて**質問する。推測で進めない。

**確認必須:** ゴール（完了条件）／言語・FW・バージョン制約／新規 or 既存コード修正／
テストの要否／影響範囲

**確認不要（既存コードに合わせて進める）:** コードスタイル／ファイル配置／軽微な実装詳細

### Development Philosophy（`docs/dev-charter/topics/SOFTWARE_DESIGN_PRINCIPLES.md`）

- まず小さなツールを構築する（段階的に拡張する）
- ローカルファーストを優先する（外部サービス依存を避ける）
- 最小限の依存関係（新規依存の追加前に既存の依存で解決できないか検討する）

### Code Design Principles（`docs/dev-charter/PRINCIPLES.md`）

- 変更範囲は必要最小限（Over-engineering しない）
- YAGNI: 今必要ない機能は実装しない
- DRY の判断: 2 回の重複では抽象化しない、3 回目で検討
- TODO/FIXME を残さない: 実装するか、Issue として記録する
- 既存コードのパターンに従う

### Coding Rules

- 可読性優先。関数は 50 行以内、単一責務
- コメントは「なぜそうするか」のみ
- 型注釈は mypy strict を通す

### Git Workflow

- Conventional Commits 形式（`feat` / `fix` / `refactor` / `docs` / `chore`）
- WIP 禁止: 動作しないコードはコミットしない
- 詳細は [CONTRIBUTING.md](CONTRIBUTING.md) を参照

### Work Stance

- スコープ厳守: 会話の主題・タスク・ゴールを AI が勝手に変更しない
- 重要な情報不足や曖昧さは質問する。軽微な不足は合理的な仮定で補い、仮定を明示する
- 大きな変更前に方針を説明してから着手する

### Document Sync Rule

仕様・ルール・構成に変更が生じたとき、変更と同じ作業内で関連ドキュメントを更新する。
対象は `docs/` 内のファイルに限らず、`AI_CONTEXT.md`・`README.md` 等のルートファイルも含む。

### dev-charter Modification Rules

`docs/dev-charter/` 配下のファイルを**直接編集しない**。

- 変更が必要な場合は dev-charter リポジトリ本体に Issue を立て、`git subtree pull` で取り込む
- `make update-charter` で最新化できる（`full` ブランチを自動判定する）
- このプロジェクト固有のルールは、`AI_CONTEXT.md` または専用ファイルに記載する

### Charter Lookup

憲章参照: `docs/dev-charter/CHARTER_INDEX.md` でトピックを特定してから該当ファイルのみ読む。
全ファイルを検索せず、特定した 1〜2 件のみ読み、参照後にユーザーへ提案・確認を行う。

### Error & Debug Handling

- エラー発生時は **原因分析 → 修正方針説明 → 実装** の順で進める
- エラーログ・スタックトレースは全文確認してから対応する（推測で修正しない）
- デバッグ用の `print` 文は残さない

### Task Workflows

**バグ修正:** 再現確認 → 原因特定 → 最小修正 → テスト追加

**機能実装:** `docs/specification.md` で仕様確認 → `docs/architecture.md` で構造確認 →
最小変更で実装 → テスト追加

**テスト作成:** 仕様を確認 → 正常系・異常系・境界値を洗い出す → fixture は
`tests/conftest.py` に定義 → テスト名は `test_<対象>_<条件>_<期待結果>`

### Review Checklist

- 仕様準拠
- テスト存在
- 可読性
- 依存関係問題なし

---

## Project-Specific Rules

### Zotero Access Policy

- Zotero へは**ローカル API のみ**を使う（`http://localhost:23119` と Better BibTeX の
  JSON-RPC）。Zotero Web API（`api.zotero.org`）は使わない。外部ネットワークへ通信しない
- 書き込みは `POST /api/local/authorize` で得たキーを用いる。キーは macOS Keychain
  （`security` コマンド）にのみ保管し、ファイル・ログ・標準出力・リポジトリへ出力しない
- 書き込みは失敗や無応答でも成功している場合があるため、子アイテムを読み戻して確認する
  （仕様は `docs/specification.md`）

### Personal Settings

- Vault のパス・名前などの個人設定は、リポジトリの外（`--vault`、環境変数、
  `~/.config/zotero-paper-tools/config.toml`）に置く。コード・テスト・ドキュメントに
  個人の絶対パス、ホスト名、アカウント固有の値を書かない（公開リポジトリのため）
- テストは一時ディレクトリと偽のサーバーを使い、実際の Zotero・Keychain・Vault に触れない

### Issue / PR Operation

- 作業は Issue を起点にし、`feature/*` などのブランチで進める。`main` へ直接コミットしない
- PR は最初から draft で開き、ローカルで `make all` と pre-commit を通してから ready にする
- PR の説明は `.github/pull_request_template.md` に従う

### Monetization Policy

- 独自の課金システムは原則禁止。OSS として Buy Me a Coffee + GitHub Sponsors のみ使用する

### Language Policy

このプロジェクトは **OSS** のため、コード・コメント・コミットメッセージ・
`README.md` は**英語**。`README-jp.md` を日本語の正本とし、英語版は日本語版に合わせて
更新する（同一コミットで両方更新する）。`AI_CONTEXT.md` は日本語。

### docs/ Role

| ディレクトリ | 役割 | AI の編集 |
|---|---|---|
| `docs/` | 人間・AI 共用の詳細仕様書 | 更新可。仕様・設計判断の変更は、依頼または提案への承認を経て記述する |
| `docs/dev-charter/` | 開発憲章（git subtree） | **禁止**（直接編集しない） |

### CI / Local Development Commands

~~~sh
make install        # uv sync
make lint           # ruff check .
make format         # ruff format .
make type           # mypy src
make test           # pytest
make all            # lint + type + test
make update-charter # dev-charter を最新化
~~~

CI（GitHub Actions）は push / PR のたびに `security`（pre-commit）→ `lint`（ruff / mypy）→
`test`（pytest、Python 3.11〜3.14）→ `build` の順で実行する。別に `dev-charter-check.yml` が
憲章のバージョンを確認する。

### Pre-commit Hooks (.pre-commit-config.yaml)

gitleaks（`.gitleaks.toml`）・秘密鍵検出・`.env` ブロック・ローカル絶対パスのブロック・
憲章関連のチェック（`scripts/check-*.sh`）が走る。`main` 上でのコミットも拒否される。

---

## AI Tool Assignments

- **使用ツール**：Claude Code、GitHub Copilot、Gemini CLI
- **標準担当の正本**：`docs/dev-charter/AI_COLLABORATION_RULES.md` の「AI Tool Responsibilities」と「Rules for Multi-AI Usage」
- **このリポジトリ固有の上書き**：なし

---

## Prohibited Actions

### Security Constraints

- シークレット・API キー・パスワード・トークンをコードに書かない（Zotero のキーは Keychain のみ）
- `.env` ファイルをコミットしない
- ローカル絶対パス（`/Users/...` など）をコードにハードコードしない
- 500 KB を超えるファイルをコミットしない
- AI との会話ログをリポジトリにコミットしない
- `--no-verify` でフックを回避しない
- AI が生成したコードは必ずレビューしてからコミットする

### Prohibited Out-of-Scope Changes

- 依存追加禁止（標準ライブラリのみの方針。必要な場合は Issue を作成する）
- Zotero Web API の利用禁止
- 大規模リファクタ・ディレクトリ構造の変更は、明示的に依頼された場合を除き禁止
- WIP コミット禁止
- `docs/dev-charter/` 配下を AI が直接編集しない
