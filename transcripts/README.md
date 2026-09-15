# transcripts/

Transcriptions of scanned PDFs, whose OCR text layer is unreliable. One file per
document, named by its manifest `id` (e.g. `articles.md`). When a transcript exists,
the build reads it instead of the source file.

They are committed so that builds are repeatable and nothing is transcribed twice.

## Format

```
---
source: sources/Articles_Of_Association.pdf
source-sha256: <SHA-256 of the source file>
transcribed-by: ...
transcribed-at: "2026-09-10"
checked-by: null            # who checked it against the page images
---
<!-- page 1 -->
**PART 1**
**Defined terms**
1. (1) In the articles, unless the context requires otherwise:
```

- **One logical line per paragraph, list item or heading.** Line wraps and
  hyphenation caused by the page layout are removed; a heading that wraps onto a
  second line is joined into one.
- **Whole-line bold is marked `**…**`.** The parse rules use this to find headings.
  Typed-in details printed in bold (names, addresses) are not marked.
- **Italics are marked `*…*`.**
- **Page starts are marked `<!-- page n -->`;** page footers are left out.
- **Text is as printed,** including the source's own errors. Only OCR errors are
  corrected.

The build refuses to use a transcript whose `source-sha256` doesn't match the
source file, because the source has changed since it was transcribed.
