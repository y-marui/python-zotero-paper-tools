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
| `paper-note <citekey>` | available | Create the deck in the vault |
| `paper-link <citekey>` | available | Attach an `obsidian://` link to the Zotero item |

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
paper-link xu_probabilistic_2025
~~~

`paper-note` writes `private/knowledge/<citekey>.md` in the vault, then prints the file path
and its `obsidian://open` URI. It refuses to overwrite an existing note.

The note has frontmatter (`citekey`, `zotero-key`, `doi`, `review_status: pending`),
a `zotero://select` link to the item, and
slides separated by `---` lines (math as `$...$`). Figures go into `<citekey>-img/` and
are embedded by relative link; the template only has an HTML comment showing how,
so it contains no broken image links. The `<citekey>-img/` folder is not created by
`paper-note`; create it when saving the first image. It renders with Obsidian's core Slides plugin.

`paper-link` requires the deck written by `paper-note` to exist. It adds one
`linked_url` attachment titled "Obsidian deck" under the item, pointing to
`obsidian://open?vault=<name>&file=private/knowledge/<citekey>` (vault-relative
path, no extension, URL-encoded). Output is `created:` or `exists:` followed by
the attachment key and the URL. Re-running is safe: if an attachment with the
same URL already exists, nothing is written (and no authorization is requested).
If writing fails, the URL is printed so it can be pasted into Zotero by hand.

Exit codes: `0` success, `1` no search results, `2` error (Zotero unreachable,
citekey not found or ambiguous, vault unresolved, note exists).

## Notes on Zotero

- `zotero://open-pdf` links need the PDF attachment's key, which `paper-note`
  does not look up yet; add them by hand in the deck for now.
- `item.search` is the only way to map a citekey to an item, so `paper-note`
  searches and requires an exact citekey match.
- Writes to the local API (`POST /api/users/0/items`) need a key from
  `POST /api/local/authorize` (body `{"appName": ...}`), and both calls need the
  `Zotero-Server-ID` header (taken from any GET response). A write may succeed
  without ever returning an HTTP response, so `paper-link` treats a failed or
  timed-out write as unknown and reads the item's children back (up to 5 times,
  1 s apart) before reporting failure.
- Key storage: the key from `/api/local/authorize` is kept in the macOS Keychain
  (service `python-zotero-paper-tools`, account `zotero-local-api`) and reused.
  It is never printed or written to a file. If Zotero rejects it (401/403),
  `paper-link` authorizes again and replaces it. If Zotero returns a single-use
  key (`remember: false`), it is not stored and a warning is shown. Delete the
  stored key with `paper-link --forget-key`.
- Choose "always allow" in the authorization dialog the first time. The key then
  stays valid, so no dialog appears again. Note that the key is not scoped to a
  library or to this tool: anyone holding it can write to your local Zotero API.
  Revoke it in Zotero under Settings > Advanced (the stored key list), and run
  `paper-link --forget-key` to drop the Keychain copy. The `security` command
  takes the key as an argument, so it is visible in `ps` for an instant while
  saving.
- Clicking the link in Zotero shows an "Open the obsidian link with Obsidian?"
  confirmation each time (Zotero 10.0.6).

## Development

~~~sh
uv sync
uv run ruff check . && uv run ruff format --check .
uv run pytest
~~~

## License

MIT
