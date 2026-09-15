---
# Structured exceptions, applied by build_okf.py. Guidance for Claude is below.

groups:                        # units merged into one concept instead of one each
  - file: company-details
    title: "Company details"
    units: [2, 3]
    include-front-matter: true # the title block before Part 1

headings:                      # articles printed without a heading of their own
  4: "Objects"
  5: "Powers"
  6: "Application of income"

definitions:
  notes-heading: "Other words and expressions"   # for 1(2), after the list of terms
  defined-elsewhere:           # terms defined inside another article
    - { term: "the 1987 Act", unit: 5, ref: "article 5(e)" }
    - { term: "eligible directors", unit: 13, ref: "article 13(3)" }
    - { term: "permitted causes", unit: 19, ref: "article 19(4)" }
    - { term: "authorised person", unit: 40, ref: "article 40(4)" }
    - { term: "relevant director", unit: 43, ref: "articles 43(3) and 44(2)" }
    - { term: "relevant loss", unit: 44, ref: "article 44(2)" }

descriptions:
  definitions: "Meanings of the terms used in the Articles of Association, with pointers to terms defined in other articles."
  company-details: "The company's name, registered office and legal form."
  4: "The company exists to acquire and exercise the Right to Manage the Premises under the 2002 Act."
  5: "The objects are to be read widely, and the company has every power an RTM company may have, from managing leases and collecting service charges to insuring the Premises and borrowing money."
  6: "The company's income may be used only to promote its objects and cannot be distributed to members, except on a winding up."
  7: "Each member's liability is limited to £1, payable if the company is wound up while they are a member or within a year of leaving."
  8: "Subject to the articles, the directors manage the company's business and may exercise all its powers."
  9: "Members can direct the directors by special resolution, without invalidating anything the directors have already done."
  10: "The directors may delegate their powers to any person or committee on terms they choose, and may revoke or alter the delegation."
  11: "Committees must follow procedures based on the articles' rules for directors' decision-making."
  12: "Directors' decisions must be majority decisions at a meeting or unanimous decisions under article 13, unless the company has only one director."
  13: "A unanimous decision is taken when all eligible directors indicate that they share a common view, provided they would have formed a quorum."
  14: "Any director may call a directors' meeting by giving every director notice of the date, time, place and how remote participants will communicate."
  15: "Directors take part in a meeting when it has been properly called and they can all communicate with each other, wherever they are."
  16: "The quorum for directors' meetings is two unless the directors fix a higher number, and it can never be fewer than two."
  17: "The directors may appoint and remove a chairman, and must choose a stand-in if the chairman has not joined within ten minutes."
  18: "The chairman has a casting vote when votes are tied, unless the chairman is not counted for quorum or voting purposes."
  19: "A director with an interest in a transaction with the company is not counted for quorum or voting except in permitted cases; the chairman rules on disputes."
  20: "The company must keep a written record of every unanimous or majority decision of the directors for at least ten years."
  21: "The directors may make further rules about how they take and record decisions."
  22: "A director may be appointed by ordinary resolution or by the directors, or by the last member's personal representatives if all members and directors have died."
  23: "The events on which a person stops being a director, including disqualification, bankruptcy, incapacity and resignation."
  24: "Directors are unpaid unless the company in general meeting agrees remuneration and its amount."
  25: "The company may pay directors' reasonable expenses of attending meetings and carrying out their duties."
  26: "Qualifying tenants, and landlords once the right to manage is acquired, may apply in the set form to become members; membership cannot be transferred."
  27: "Membership ends when a member no longer qualifies or withdraws by notice, with rules for deaths, bankruptcies and joint members."
  28: "When a person can speak and vote at a general meeting, including when those attending are not in the same place."
  29: "The quorum for a general meeting is 20 per cent of members entitled to vote, or two such members if that is greater."
  30: "The chairman of the directors chairs general meetings; otherwise the directors present, or the meeting, appoint someone."
  31: "Directors may attend and speak at general meetings, and the chairman of the meeting may allow non-members to."
  32: "When a general meeting must or may be adjourned, and the notice needed for the adjourned meeting."
  33: "How votes are allocated between flats, non-residential parts and landlord members, and who casts them."
  34: "Objections to a person's right to vote must be raised at the meeting and are decided finally by the chairman of the meeting."
  35: "Who may demand a poll, when, and how a demand may be withdrawn."
  36: "What a proxy notice must contain, and how it is treated if it gives no voting instructions."
  37: "A member keeps the right to attend despite appointing a proxy, and may revoke the appointment by notice before the meeting starts."
  38: "How ordinary and special resolutions may be amended at a general meeting."
  39: "Documents may be sent by any means the Companies Acts allow, or by a method a director has asked for."
  40: "A common seal may be used only with the directors' authority, and a sealed document must also be signed by an authorised person before a witness."
  41: "Members may inspect and copy the company's books and records on reasonable notice, subject to confidentiality exclusions."
  42: "The directors may make provision for employees if the company's business ceases or is transferred."
  43: "Directors may be indemnified out of the company's assets against liabilities incurred as directors, so far as the law allows."
  44: "The company may buy insurance for directors against losses relating to their duties."
---
# Articles of Association — guidance for Claude

Use this when transcribing the document again or checking the built output. The
structured exceptions above are applied by the build; this section is prose.

## Transcribing

- The PDF is a scan. Its OCR text layer has no bold information, has misread
  characters, and has lines missing or moved to the bottom of the page. Work from
  the page images and follow the format in `transcripts/README.md`.
- Join Part 1's title, which wraps over two lines, into one line. Part 6's title is
  printed on the same line as "PART 6"; keep it there.
- The company name, registered office and the Premises address are typed in bold
  monospace across several lines. Join them into the surrounding sentence with
  commas, without bold.
- Keep the source's own errors, for example "Companies Act 2006(5)",
  "Companies Acts 2006" in 23(a), "if—" in 38(1), and "the register kept by the
  registrar section 1080" in 33(4).
- OCR errors seen in the text layer, to check against: "4l" for "41", "RGl" for
  "RG1", "l" or "f1" for "£1"; in article 5 the list labels (m), (l), (o), (p), (q),
  (r), (i) and (j) are misread; displaced lines in 5, 5(v), 14(4), 22(2), 28(3),
  40(3), 44(1) and 44(2)(b).

## Checking the output

- There should be 44 articles: article 1 in `definitions.md`, articles 2–3 with the
  title block in `company-details.md`, and one file each for articles 4–44.
- Parts 3 and 5 have no section heading; their articles have no `section` field.
- "chairman", "chairman of the meeting", "participate" and "proxy notice" are
  defined in article 1 by reference to other articles, so they are not repeated
  under `defined-elsewhere`.
