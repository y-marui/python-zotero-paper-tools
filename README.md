# python-zotero-paper-tools

> **This is the reference (English) version.**
> The canonical (Japanese) version is [README-jp.md](README-jp.md).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/y-marui/python-zotero-paper-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/y-marui/python-zotero-paper-tools/actions/workflows/ci.yml)
[![Charter Check](https://github.com/y-marui/python-zotero-paper-tools/actions/workflows/dev-charter-check.yml/badge.svg)](https://github.com/y-marui/python-zotero-paper-tools/actions/workflows/dev-charter-check.yml)
[![GitHub Sponsors](https://img.shields.io/github/sponsors/y-marui?style=social)](https://github.com/sponsors/y-marui)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-donate-yellow.svg)](https://www.buymeacoffee.com/y.marui)

| Field | Value |
|---|---|
| Target | CLI tools for Zotero and Obsidian users |
| Team | Solo |
| Language | English |
| License | MIT |
| AI Tools | Claude Code / GitHub Copilot / Gemini CLI |
| Runtime | Python ^3.11 (standard library only), macOS (Keychain) |

Small CLI tools that connect papers in [Zotero](https://www.zotero.org/) with
slide-style Markdown discussion notes (a "deck") in an Obsidian vault.

Zotero is accessed **only through its local API** (`http://localhost:23119`)
and the [Better BibTeX](https://retorque.re/zotero-better-bibtex/) JSON-RPC
endpoint. The Zotero Web API is never used. Python 3.11+, standard library only.

## Commands

| Command | Status | What it does |
| --- | --- | --- |
| `paper-find <query>` | available | Search Zotero and print citekeys (`--json` adds `zotero_key` and `pdf_key`) |
| `paper-note <citekey>` | available | Create the deck in the vault |
| `paper-link <citekey>` | available | Attach an `obsidian://` link to the Zotero item |

Requirements: Zotero running with Better BibTeX installed.

## Install

~~~sh
uv tool install .
~~~

## Configuration

Personal settings are kept outside the repository. The vault **root** is resolved
in this order, and the command stops if none is found:

1. `--vault DIR`
2. environment variable `OBSIDIAN_VAULT_ROOT`
3. `vault_root` in `~/.config/zotero-paper-tools/config.toml`
   (override the path with `ZOTERO_PAPER_TOOLS_CONFIG`)

The vault **name** (the `vault=` part of `obsidian://` links) is resolved in this
order:

1. `--vault-name NAME` (`paper-note`, `paper-link`)
2. environment variable `OBSIDIAN_VAULT_NAME`
3. `vault_name` in the config, **only if the selected root is the config's
   `vault_root`** (compared after `~` expansion and resolving symlinks, so
   `~/v`, `/Users/me/v/` and a symlink to it count as the same root)
4. the directory name of the selected root

So overriding the root never silently reuses a name registered for another root.
Set `vault_name` when the name registered in Obsidian differs from the directory name.

~~~toml
# ~/.config/zotero-paper-tools/config.toml
vault_root = "~/path/to/vault"   # relative paths are taken from $HOME
vault_name = "my-vault"          # name registered in Obsidian; defaults to the directory name
~~~

## Usage

~~~sh
paper-find "spike-frequency adaptation"     # citekey, year, first author, title (tab separated)
paper-find --json --limit 5 probabilistic   # JSON output

paper-note xu_probabilistic_2025            # add --private for the private area
paper-link xu_probabilistic_2025
~~~

`paper-note` writes `knowledge/research/papers/<citekey>.md` in the vault (with
`--private`: `private/knowledge/research/papers/<citekey>.md`), then prints the file
path and `zotero://select/library/items/<itemKey>`. It refuses to overwrite, and
stops if a deck for the citekey already exists in either area (it never creates
the other one).

The note has frontmatter (`citekey`, `zotero-key`, `doi`, `review_status: pending`),
a `zotero://select` link to the item, and
slides separated by `---` lines (math as `$...$`). Figures go into `<citekey>-img/` and
are embedded by relative link; the template only has an HTML comment showing how,
so it contains no broken image links. The `<citekey>-img/` folder is not created by
`paper-note`; create it when saving the first image. It is displayed by a Marp plugin (Marp Inline Preview), which needs `marp: true`
in the frontmatter (the template also sets `paginate` and a `style` that keeps
text and figures on the slide). Obsidian's core Slides also shows the `---`
separated slides, but content overflows more easily.

`paper-link` looks for the deck in both areas (an error if it is in neither or
both) and keeps one `linked_url` attachment under the item, pointing to
`obsidian://open?vault=<name>&file=<vault-relative path, no extension>` (slashes
are not encoded). The existing attachment is the one titled "Obsidian deck" or whose
URL starts with `obsidian://open?vault=<name>`. If its URL is the same nothing is
written (`exists:`); if it differs the URL is updated with PATCH (`updated:`, e.g.
after moving the deck between areas); if there is none it is created (`created:`).
Updates use the same authorization, Keychain key and read-back verification as
creation. Output:

~~~
created: <attachment key>        # or updated: / exists:
item: zotero://select/library/items/<itemKey>
pdf: zotero://open-pdf/library/items/<pdfKey>?page=1   # only if exactly one PDF
deck: obsidian://open?vault=...&file=...
~~~

If writing fails, the URL is printed so it can be pasted into Zotero by hand.

`paper-find --json` gives each result `zotero_key` and `pdf_key` (the PDF
attachment key, `null` unless exactly one PDF attachment exists).

Exit codes: `0` success, `1` no search results, `2` error (Zotero unreachable,
citekey not found or ambiguous, vault unresolved, note exists).

## Notes on Zotero

- `zotero://open-pdf` links need the PDF attachment's key: take `pdf_key` from
  `paper-find --json` or the `pdf:` line of `paper-link` (`paper-note` does not
  look it up).
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
make install   # uv sync
make all       # ruff check + mypy (strict) + pytest
~~~

| Command | Description |
|---|---|
| `make install` | `uv sync` |
| `make lint` | `ruff check .` |
| `make format` | `ruff format .` |
| `make type` | `mypy src` |
| `make test` | `pytest` |
| `make all` | lint + type + test |
| `make update-charter` | Update the dev-charter subtree |

See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow and
[AI_CONTEXT.md](AI_CONTEXT.md) for AI tool context.

## License

MIT License — see [LICENSE](LICENSE)

---
*This document has a Japanese canonical version [README-jp.md](README-jp.md). Update both in the same commit when editing.*
