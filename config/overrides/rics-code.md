---
# Structured exceptions, applied by build_okf.py. Guidance for Claude is below.

descriptions:
  definitions: "Terms defined in the RICS code, from the glossary table at the front of the document."
---
# RICS Service Charge Residential Management Code — guidance for Claude

## Grain

One concept per numbered section (1.1, 1.2 …). Sub-sections (1.2.1) stay inside their
section as sub-headings: they are short and only make sense in context. Appendix B's
entries (B1–B16) each become a concept, because each describes a separate statutory
right. Appendices A, C and D have no numbered sections, so each becomes one concept.

## Not included

The front matter is skipped: the cover, acknowledgements, contents, the RICS standards
framework, document definitions and the "Building Safety Act 2022 glossary" note (which
says those terms are defined in section 9). Only the main glossary table is taken, into
`definitions.md`.

## Reading the PDF

- Headings are found by font size, not bold: 32pt chapter, 16pt section, 14pt
  sub-section, 11pt body. Bold is used inside sentences for emphasis and for bullet
  glyphs, so it says nothing about structure.
- Chapter and section titles often wrap over two lines; the extractor joins lines of the
  same size that sit close together, so a wrapped heading arrives as one line.
- Tables inside chapters are read as plain text and may read oddly.

## Descriptions

Sections have no hand-written descriptions: there are too many. Each falls back to its
own opening sentence. Add a `descriptions:` entry above for any where that reads badly.
