# Method

## Granularity is a judgement

Each concept file should hold one unit of independent meaning: something a reader
(or a model) can cite and act on without reading its neighbours. That unit differs by
document type — an article of association, a lease sub-clause, a section of the RICS
code, an entry in a title register. The choice for each type is recorded in
[grain-table.md](grain-table.md).

## Rules and overrides

- **Parse rules** are declarative and generic: patterns, thresholds, locators.
- **Overrides** record judgement: merges, splits and special cases for one document.

Keeping them apart means the generic code can be tested against the committed bundle, and every
document-specific decision is written down in one place.

_TODO: expand._
