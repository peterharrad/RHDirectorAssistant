---
# Structured exceptions, applied by build_okf.py. Guidance for Claude is below.

groups:                        # clauses kept whole, sub-clauses and all
  - file: clause-03
    title: "Clause 3 – Demise"
    units: ["3", "3.1", "3.2", "3.3", "3.4"]
  - file: clause-04
    title: "Clause 4 – The lessee's covenants"
    units: ["4", "4.1", "4.2", "4.3"]
  - file: clause-05
    title: "Clause 5 – Covenants by the lessor and the developer"
    units: ["5.1", "5.2"]

descriptions:
  clause-03: "The demise of the flat for the term at the rent, the review of the rent every twenty-one years, and the lessee's share of the maintenance expenses payable as further rent."
  clause-04: "The lessee's covenants with the developer and lessor, with the manager, and with the other lessees, set out in the Eighth Schedule."
  clause-05: "The lessor's and developer's covenants in the Ninth Schedule, and the developer's indemnity to the lessor."
  definitions: "Terms used in the flat lease, from the definitions table in clause 1."
  particulars: "The lease's particulars: the parties, the flat and parking space, the rent, term and premium, and the lessee's share of each part of the service charge."
---
# Individual flat lease — guidance for Claude

## What this document is

A sample of the long lease of a flat at Riverside House (originally Bear Wharf), made
between the developer, the lessor, the manager and the lessee in 2002. The flat, the
lessee's name, the premium, the declared value and the service charge proportions have
been replaced by placeholders such as "Plot No XX", "XXXX XXXX", "Some Money
(£000000.00)" and "0.00%".

## Grain

- One concept per sub-clause (2.1, 7.12 …), titled "Clause 7.12 – Agreements and
  declarations". A clause with no sub-clauses is one concept. Words of a clause outside
  its sub-clauses go in one concept marked "(general words)".
- Clauses 3, 4 and 5 are kept whole (see `groups` above), in document order: clause 3's
  demise, its rent review sub-clauses 3.1-3.4 and then its closing "AND ALSO paying…"
  words; clause 4's opening words and the three covenants they introduce; and clause 5's
  two sub-clauses. Splitting them would separate words that only make sense together.
- One concept per numbered paragraph of each schedule, or of each part of a schedule,
  with its sub-paragraphs (1.1, 1.2 …) kept inside it. A part with a single unnumbered
  paragraph (Parts B, C and E of the Sixth Schedule) is one concept.
- The definitions table in clause 1 becomes `definitions.md`, and the particulars table on
  the cover becomes `particulars.md`.

## Not included

The cover heading and the paragraphs before clause 2 other than the two tables: the
"SAVE THAT" note on the proportions, the parties clause and the recitals.

## Reading the document

- Word generates every clause, sub-clause and paragraph number from the Heading 1 and
  Heading 2 styles; none is typed. The docx reader recomputes them. Its output was checked
  against LibreOffice's rendering: all 257 paragraphs matched, in order.
- The one typed number is "1" in the First Schedule; clause 1's "1. In this Deed…" is
  typed too, but sits before the first generated clause, which is why generated numbering
  starts at 2 (an empty Heading 1 paragraph at the top of the document takes 1).
- In the clauses, Heading 1 is a clause heading; in the schedules it is a paragraph. Clause
  headings are told apart by being in capitals.
- The part headings are typed inconsistently: PART “A", "PART "D", “PART E”, PART "F''.

## Quirks of the lease, kept as they are

- There are ten schedules, not eight.
- Clause 7.12 refers to "Clause 7.10 or 7.'11" (a stray apostrophe).
- The Seventh Schedule's paragraph 2 refers to "Paragraph I of Part "3 " of the Sixth
  Schedule", which has no Part 3.
- "refuse shutes" for "refuse chutes" in the particulars and the Sixth Schedule.
