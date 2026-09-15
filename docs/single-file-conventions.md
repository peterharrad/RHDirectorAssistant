# Single-file conventions

`single-files/` holds one markdown file per source document, for tools that limit how
many files can be loaded (a Gemini Gem, a Claude project). It is built by
`rh-build-single` from the same concepts as the [OKF bundle](okf-conventions.md), so the
two never disagree about what a document says. The intent is in `single-file-defaults`
in `config/Processing_Prompts.yml`.

## Files

```
single-files/                    # entirely generated; never edit by hand
  articles.md                    # one per manifest document, named by its id
  sample-lease.md
  management-lease.md
  agency-agreement.md
  rics-code.md
  land-title.md                  # the three title registers stay separate
  freehold-title.md
  leasehold-title.md
  legislation.md                 # the manifest's legislation references
  building.md                    # authored/building/, without the layout diagram
```

## Inside a file

The file starts with frontmatter naming the document and its provenance: `title`,
`sources` (as in the OKF bundle) and `generated_by`. There is no timestamp, so an
unchanged document rebuilds byte for byte.

Each OKF concept becomes a section, in document order:

```markdown
<a id="article-17"></a>

# Article 17 – Chairing of directors' meetings

- title: Article 17 – Chairing of directors' meetings
- description: Directors may appoint and remove a chairman, and choose a stand-in if the chairman is late.
- article_number: 17

(1) The directors may appoint a director to chair their meetings.
```

- **The anchor** is the concept's OKF name, so a link to it is the same as the OKF
  file name without folder or `.md`.
- **The fields** are the title, the description and the reference: whichever of
  `article_number(s)`, `clause_number(s)`, `paragraph_number`, `section_number` or
  `register` the concept has. Empty values are left out.
- **The heading** is a heading 1. Headings inside the concept keep their levels (2 and
  below), so nothing is renumbered.
- **Cross-references** are links to the anchor: `[article 26](#article-26)`. A link to
  something not in the file is a build error.
- **The heading comes first,** so a tool that splits a file at its headings keeps each
  section's fields with that section.

Authored files lose their own heading 1 (the title takes its place) and any embedded
image. A heading 2 section that embeds an image, such as the layout's "Diagram", is left
out whole, since the rest of it describes the image. Bundle paths in links become
anchors.
