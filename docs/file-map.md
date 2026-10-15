# File Map

ファイルレベルの依存関係を記録するドキュメント。

## File Dependency Map

~~~
src/zotero_paper_tools/
  __init__.py
    - exports: (なし)

  config.py
    - imports: (標準ライブラリのみ)
    - used by: note, link

  zotero.py
    - imports: (標準ライブラリのみ)
    - used by: find, note, link, localapi

  keystore.py
    - imports: (標準ライブラリのみ)
    - used by: link

  localapi.py
    - imports: zotero
    - used by: find, link

  find.py   (paper-find)
    - imports: localapi, zotero

  note.py   (paper-note)
    - imports: config, zotero
    - used by: link (find_decks, _SAFE_CITEKEY)

  link.py   (paper-link)
    - imports: keystore, config, localapi, note, zotero

tests/
  conftest.py     - 偽の Zotero サーバー（Better BibTeX RPC と /api）の fixture
  unit/           - 各モジュール・CLI の単体テスト
  integration/    - （現状なし）
~~~
