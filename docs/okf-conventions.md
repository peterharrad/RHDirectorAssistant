# OKF conventions

The bundle targets [OKF v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md).
The spec needs very little: a directory tree of `.md` files, each with YAML
frontmatter containing a `type`. Everything below is this project's own convention
on top of that.

## Bundle layout

```
okf-bundle/                      # entirely generated; never edit by hand
  index.md                       # root listing; carries okf_version: "0.2"
  log.md                         # build history, appended by build_okf.py
  articles/
    index.md
    definitions.md
    company-details.md
    article-04.md … article-44.md
  leases/
    index.md
    sample-lease/
      index.md
      definitions.md
      clause-01.md               # clause with no sub-clauses
      clause-03-02.md            # sub-clause 3.2
      schedule-01.md
    management-lease/
  agreements/
    agency-agreement/
      definitions.md
      clause-03-01.md            # sub-clause 3.1
      appendix-01.md
  guidance/
    rics-code/
      index.md
      definitions.md             # the glossary table
      section-02-01.md
      appendix-b-03.md
  titles/
    freehold-title/
      property-01.md             # register A, entry 1
      proprietorship-01.md       # register B
      charges-01.md              # register C
    leasehold-title/
    land-title/
  legislation/
    index.md
    clra-2002-part-2-chapter-1.md
  building/                      # copied from authored/
```

Each document's folder is its `bundle-path` in `config/manifest.yml`.

## Rules

- **`okf-bundle/` is fully generated.** `build_okf.py` may delete and rebuild it, so an
  edit made there is lost on the next build: change the source, the parse rules, the
  overrides or the manifest instead. `rh-build --check` lists anything that differs.
  Hand-written concepts live in `authored/` and are copied in.
- **Filenames are short, stable slugs.** OKF defines a concept's ID as its path
  without `.md`, and links point at paths. So filenames stay mechanical
  (`article-17.md`) and the readable name goes in `title`. A cross-reference such as
  "article 17" can then be turned into a link without looking anything up.
- **Numbers are zero-padded** so files sort in document order.
- **`index.md` and `log.md` are reserved** by the spec at every level. Never use
  them for concepts.
- **Links are bundle-relative:** `[article 17](/articles/article-17.md)`.

## Frontmatter

| Field | Source | Notes |
|---|---|---|
| `type` | Manifest `concept-type` | Required by OKF |
| `title` | Generated | e.g. "Article 17 – Chairing of directors' meetings" |
| `description` | Generated | One sentence summarising the unit |
| `resource` | Manifest `resource` | Public URL of the source document, where one exists |
| `tags` | Generated / overrides | |
| `sources` | Manifest | List of `{id, title, author, last_modified, resource}` |
| `generated` | Build | `{by, at}`: tool and version, ISO 8601 build time |
| `status` | Manifest / overrides | `draft` until reviewed. Set `status:` on a document in `config/manifest.yml` to mark all its concepts, or per concept under `status:` in its overrides file. Files in `authored/` keep the status they declare |
| `stale_after`, `verified` | Review | Used by the staleness report |
| `part`, `section`, `chapter` | Parse | Project fields: the headings the unit sits under; which of them a document uses is set by `fields` in its parse rules |
| `article_number` (or `article_numbers` for a group) | Parse | Project field: the unit's number; the name is set per document type by `number-field` in its parse rules |
| `source_pages` | Parse | Project field: pages of the source document the unit appears on |

**Every frontmatter field in the bundle is snake_case,** following OKF
(`last_modified`, `stale_after`). Project fields follow the same rule
(`article_number`, `source_pages`). Keys in this repo's own config files (the
manifest, parse rules, overrides and transcripts) are kebab-case (`last-modified`);
`frontmatter.py` maps between them.

### Example

```yaml
---
type: articles clause
title: "Article 17 – Chairing of directors' meetings"
description: "Directors may appoint and remove a chairman, and choose a stand-in if the chairman is late."
resource: "https://find-and-update.company-information.service.gov.uk/company/17149089/filing-history/MzUyMjY0OTQ3OWFkaXF6a2N4/document?format=pdf&download=0"
part: "Part 2 – Directors"
section: "Decision-making by directors"
article_number: 17
source_pages: [5]
sources:
  - id: articles
    title: "Riverside House Reading RTM Company Limited Articles of Association"
    author: "Riverside House Reading RTM Company"
    last_modified: "2026-05-28"
generated:
  by: "rh-director-assistant 0.1.0"
  at: "2026-09-10T12:00:00Z"
status: draft
---
```

## Types

OKF doesn't register type values centrally. Current values, from the manifest:

- `articles clause`
- `lease clause`
- `agreement clause`
- `guidance section`
- `title`
- `definitions` — a document's definitions clause or table
- `legislation` — a reference to an Act, generated from the manifest

Authored concepts:

- `building` — facts about the building
- `building plan` — a diagram, described by a concept file beside the image

_TODO: decide whether to switch to slugs (`articles-clause`), and add types for
definitions, legislation references and authored concepts._
