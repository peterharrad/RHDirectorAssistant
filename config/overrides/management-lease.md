---
# Structured exceptions, applied by build_okf.py. Guidance for Claude is below.

descriptions:                  # whole clauses: an opening sentence would describe only the first sub-clause
  definitions: "Terms used in the management lease, most of them taking their meaning from the standard form of flat lease."
  "2": "How the lease is to be read: gender and number, persons, references and headings, statutes, negative covenants, and joint and several liability."
  "3": "The lessor grants the manager a 999-year lease of the common parts and grounds, with the rights in the First Schedule and subject to those in the Second, the ground rents staying with the lessor."
  "4": "The manager's obligations: sharing maintenance accounts with the lessor, using the common parts only as such, allowing inspection, not building, altering or assigning without consent, meeting section 146 costs, and handing back in repair."
  "5": "An 80-year perpetuity period, the lessor joining the manager in action against flat lessees, the lessor's right of re-entry after 28 days' notice of a breach, and no third-party rights."
  "6": "The manager's quiet enjoyment, and the lessor's promise to take on the manager's obligations if the manager goes into liquidation or fails to perform them."
  schedule.first: "Rights granted to the manager: running services through the flats, support and protection, communal telecoms apparatus, and passage over the estate roads and footpaths."
  schedule.second: "Rights reserved to the lessor and flat lessees: running services through the common parts, access to repair the flats, and support and shelter."
---
# Management lease (BK401853) — guidance for Claude

## What this document is

A 999-year lease of the common parts and grounds, granted in December 2005 by Peverel
Freeholds Limited to Peverel OM Limited, so that a manager holds and manages everything
at Bear Wharf other than the flats themselves. It sits behind the individual flat leases
and the RTM company's right to manage.

## Grain

One concept per clause and one per schedule, each taken whole: the sub-clauses of a
clause (2.1-2.6) and the paragraphs of a schedule stay together, in order and with their
numbers. The clauses are short and their sub-clauses read as one provision, so splitting
them adds files without adding meaning. The definitions clause becomes `definitions.md`;
each schedule keeps its bracketed description as its first line.

## Not included

Pages 1-2 (the Land Registry notes, the certification stamp and the cover), page 3 (the
contents), page 11 (the execution page, which carries two signatures) and pages 12-13
(the title plans, which are images). The header, parties and recitals on page 4 are read
as front matter and are not made into concepts.

## Transcribing

- Scanned PDF: its OCR text layer is poor ("ISh Jicember 2005" for the date), so work
  from the page images and follow the format in `transcripts/README.md`.
- Clause headings are printed in bold with no number. The numbers 1-6 come from the
  contents page and are added to the headings in the transcript, so that sub-clause
  numbers line up with their clause.
- The definitions are printed in two columns and are written as "the term: meaning".
  Eight terms share one meaning in the original ("all have the same meanings as in the
  Standard Form of Lease"); each gets its own line, wording otherwise unchanged.
- Handwritten amendments are shown in square brackets, including the title number, which
  was struck through and replaced by hand with BK397927.

## Quirks of the deed, kept as they are

- Clause 4 runs 4.1-4.4 and then 4.6-4.8: there is no 4.5.
- The parties are numbered (1) and (3): there is no party (2), though the recitals and
  covenants refer to a Developer.
- The contents lists a clause 7, Certificate of Value, against "Error! Bookmark not
  defined." No such clause appears in the deed.
- Clause 5.3 spells "Manger" for "Manager", and 2.4 "statue" for "statute".
- Clauses 2.5 and 3 refer to "the Lessee", a term the deed never defines; the party is
  the Manager.
