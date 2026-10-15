# python-zotero-paper-tools

Small CLI tools that connect papers in [Zotero](https://www.zotero.org/) with
slide-style Markdown discussion notes (a "deck") in an Obsidian vault.

Zotero is accessed **only through its local API** (`http://localhost:23119`)
and the [Better BibTeX](https://retorque.re/zotero-better-bibtex/) JSON-RPC
endpoint. The Zotero Web API is never used. Python 3.11+, standard library only.

## Commands

| Command | Status | What it does |
| --- | --- | --- |
| `paper-find <query>` | available | Search Zotero and print citekeys |
| `paper-note <citekey>` | available | Create the deck and its image folder in the vault |
| `paper-link <citekey>` | planned | Attach an `obsidian://` link to the Zotero item |

Requirements: Zotero running with Better BibTeX installed.

## Install

~~~sh
uv tool install .
~~~

## Configuration

Personal settings are kept outside the repository. The vault is resolved in this
order, and the command stops if none is found:

1. `--vault DIR`
2. environment variable `OBSIDIAN_VAULT_ROOT`
3. `vault_root` in `~/.config/zotero-paper-tools/config.toml`
   (override the path with `ZOTERO_PAPER_TOOLS_CONFIG`)

~~~toml
# ~/.config/zotero-paper-tools/config.toml
vault_root = "~/path/to/vault"   # relative paths are taken from $HOME
vault_name = "my-vault"          # name registered in Obsidian; defaults to the directory name
~~~

## Usage

~~~sh
paper-find "spike-frequency adaptation"     # citekey, year, first author, title (tab separated)
paper-find --json --limit 5 probabilistic   # JSON output

paper-note xu_probabilistic_2025
~~~

`paper-note` writes `private/knowledge/<citekey>.md` and an empty
`private/knowledge/<citekey>-img/` folder in the vault, then prints the file path
and its `obsidian://open` URI. It refuses to overwrite an existing note.

The note has frontmatter (`citekey`, `zotero-key`, `doi`, `review_status: pending`),
a `zotero://select` link to the item, and
slides separated by `---` lines (math as `$...$`, figures as relative links into
`<citekey>-img/`). It renders with Obsidian's core Slides plugin.

Exit codes: `0` success, `1` no search results, `2` error (Zotero unreachable,
citekey not found or ambiguous, vault unresolved, note exists).

## Notes on Zotero

- `zotero://open-pdf` links need the PDF attachment's key, which `paper-note`
  does not look up yet; add them by hand in the deck for now.
- `item.search` is the only way to map a citekey to an item, so `paper-note`
  searches and requires an exact citekey match.
- Writes to the local API need an authorization dialog and may not return a
  response even when they succeed. `paper-link` (planned) will verify by reading
  back and avoid duplicate attachments on re-runs.

## Development

~~~sh
uv sync
uv run ruff check . && uv run ruff format --check .
uv run pytest
~~~

## License

MIT
