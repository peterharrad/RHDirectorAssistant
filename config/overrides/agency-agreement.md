---
# Structured exceptions, applied by build_okf.py. Guidance for Claude is below.

groups:                        # clauses kept whole: their sub-clauses are list items
  - file: clause-04            # 4.1-4.6 are fragments of one list, e.g. "Its name and legal status;"
    title: "Clause 4 – Compliance with the Provision of Services Regulations 2009 (as amended)"
    units: ["4", "4.1", "4.2", "4.3", "4.4", "4.5", "4.6"]

descriptions:
  clause-04: "The information the manager has given the client under the Provision of Services Regulations 2009."
  definitions: "Terms used in the management agency agreement between the company and Common Ground."
  appendix.1: "The management fee, what it covers, and the prices of additional services."
  appendix.2: "The services included in the management fee, listed."
  appendix.3: "Examples of work charged as additional services rather than covered by the fee."
  appendix.4: "What the outgoing and incoming managers must hand over on takeover and handover."
  appendix.5: "The steps the manager takes to enforce lease covenants, and what each stage costs."
  appendix.6: "The stages of recovering service charge arrears, from reminder to legal action."
  appendix.7: "Points to the separate schedule of fees, updated each 31 March."
  appendix.8: "The manager's insurance commissions, their range, and how they are disclosed."
  appendix.9: "The caretaker's duties, and the split of responsibility between manager and client."
---
# Management agency agreement — guidance for Claude

## Grain

One concept per sub-clause (3.1, 3.2 …), titled "Clause 3.1 – Services to be provided
by the Manager" so the clause it belongs to travels with it. Third-level sub-clauses
(2.2.1) stay inside their sub-clause. A clause with no sub-clauses, such as 16 Waiver,
becomes a single concept. Each appendix is one concept, taken as it stands.

Where a clause's sub-clauses are items of a single list introduced by its opening words,
so that no sub-clause means anything on its own, the whole clause is kept in one concept
(see `groups` above). Clause 4 is the only one: 4.1-4.6 are fragments such as "Its name
and legal status;". I checked every other clause with sub-clauses; in all of them each
sub-clause is a complete provision.

Where a clause has opening words and sub-clauses that do stand alone, the opening words
become their own concept marked "(opening words)".

## Not included

- **The front matter:** cover page, contents, the parties and the recitals.
- **Page 10, the signature block** (names, positions, email addresses and a signature
  image), and **page 23, the Adobe audit trail** (email addresses, timestamps and a
  transaction ID). Both are personal data and neither states any term of the agreement.
  The build fails if those pages no longer contain the text it expects, so a reissued
  PDF can't quietly slip them in.

## Reading the PDF

- Clause headings are 13pt, appendix headings 16pt with the appendix title on the line
  below, body text 10pt. Bold marks emphasis and sub-headings inside appendices, not
  structure.
- Appendix 7 has no title of its own: it is a single line saying the schedule of fees
  is a separate document.
- Appendix 1 contains a fee table, which is converted to a markdown table.

## Descriptions

Sub-clauses have no hand-written descriptions; each falls back to its own opening
sentence. Add a `descriptions:` entry above for any where that reads badly.
