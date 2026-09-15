# RHDirectorAssistant

Tools for turning the governing documents of Riverside House Reading RTM Company
(articles, leases, title registers, the RICS service charge code, agency agreements)
into an [Open Knowledge Format](docs/okf-conventions.md) bundle: one concept file per
unit of independent meaning, with provenance in the frontmatter and links between them.
The same concepts are also written as [single files](docs/single-file-conventions.md),
one per document, for tools that limit how many files can be loaded.

> **This is the public repo.** It holds the code, the parse rules and the method, but
> not the real source documents: several hold personal data or are confidential or
> copyright. See [NOTICE.md](NOTICE.md). Instead it holds redacted versions, with their
> structure kept and body text replaced with lorem ipsum, and `okf-bundle/` and
> `single-files/` are built from those. Only the Articles of Association are real.

## Method

Generic parser code does the mechanical work. Each document gets:

- **parse rules** (`config/parse-rules/*.yml`) — declarative: patterns, thresholds,
  locators for headings, clauses and definitions;
- **overrides** (`config/overrides/*.md`) — judgement only: merges, splits and special
  cases the rules can't express.

The grain (article, clause, section…) is chosen per document type — see
[docs/method.md](docs/method.md) and [docs/grain-table.md](docs/grain-table.md).

Posts describing the approach: _TODO: links_

## Layout

| Path | Contents |
|---|---|
| `src/parse/` | **Shared.** Reading sources and finding structure: transcripts, PDF layout, Word numbering, headings, clauses, definitions, title registers |
| `src/assemble.py` | **Shared.** Applies parse rules and overrides to decide what each document's concepts are, with no output format |
| `src/build_okf.py` | **OKF output.** Writes the assembled concepts as OKF concept files, indexes and build log |
| `src/frontmatter.py` | **OKF output.** Frontmatter, with provenance from the manifest |
| `src/validate/` | **OKF output.** Link and schema checks on the bundle |
| `src/build_single.py` | **Single-file output.** Writes each document's concepts as one markdown file |
| `src/redact/` | Makes the redacted copies of the sources (`rh-redact`) |
| `config/manifest.yml` | Provenance and pointers for every source document (no prose) |
| `config/redaction.yml` | How each source document is redacted |
| `authored/` | Hand-written concepts, copied into the bundle at build time |
| `okf-bundle/` | The OKF bundle — fully generated, see [docs/okf-conventions.md](docs/okf-conventions.md) |
| `single-files/` | One file per document — fully generated, see [docs/single-file-conventions.md](docs/single-file-conventions.md) |
| `transcripts/` | Committed transcriptions of scanned PDFs, so builds are repeatable |
| `tests/fixtures/` | Short hand-written snippets for the unit tests |
| `sources/` | Redacted copies of the source documents; the Articles are real |
| `work/` | Intermediate extraction output for inspection — not committed |
| `INSTRUCTIONS.md` | Instructions for an AI assistant (a Claude project or Gemini Gem) loaded with `single-files/` |
| `test_scenarios.md` | Questions for trying out the assistant |

## Getting started

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env      # then add your Anthropic API key to .env
rh-build                    # build okf-bundle/ from sources/
rh-build --check            # report what a build would change, without writing
rh-build-single             # build single-files/ (also takes --check)
pytest
```

Scanned PDFs are read from their committed transcripts in `transcripts/`. A new
transcript is made with Claude, in a Claude Code session or through the API (which
needs `ANTHROPIC_API_KEY` in `.env` or the environment).

## Source documents

`sources/` holds redacted versions of the real documents: the headings, numbering,
defined terms and cross-references are kept and the body text is lorem ipsum, so they
parse into the same concepts as the real ones. `okf-bundle/` and `single-files/` are
built from them, so their text is lorem ipsum too, apart from the hand-written
descriptions in `config/overrides/`. The management lease is scanned: its redacted
transcript is in `transcripts/`, with a stand-in PDF in `sources/`. The Articles of
Association are real. See [NOTICE.md](NOTICE.md) for what is and isn't included.

To build from your own copies of the real documents, replace the files in `sources/`,
keeping the file names given in `config/manifest.yml`. A scanned document also needs a
transcript made from it in `transcripts/`.

## Redacted copies

The redacted copies are made in the private repo, which holds the real documents, by
`rh-redact`, as set out in `config/redaction.yml`. It is included here so the method can
be seen and reused; run here, it would only redact the copies again. `rh-redact --check`
rebuilds the redacted copies and compares their concept names, titles and positions with
the real documents'. It needs `pip install -e ".[redact]"` (reportlab).

## Using the files with an AI assistant

Load the files in `single-files/` into a Claude project or a Gemini Gem as its knowledge, and
use `INSTRUCTIONS.md` as its instructions: the assistant then answers from those documents
only, citing the clause, article, register entry or section each statement comes from.
`test_scenarios.md` has questions to try it out with. In this repo the documents are
redacted, so the assistant can show how it finds and cites things but not what the real
documents say.

## Licence

Code: MIT — see [LICENSE](LICENSE). Third-party content is not covered; see
[NOTICE.md](NOTICE.md).
