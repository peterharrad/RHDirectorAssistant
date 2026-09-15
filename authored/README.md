# authored/

Hand-written concept files that don't come from parsing a source document — for
example a building overview. `build_okf.py` copies them into `okf-bundle/` at the same
relative path, so `authored/building/riverside-house.md` becomes the concept
`/building/riverside-house`.

Write them as full OKF concepts: frontmatter with at least `type`, then a markdown
body. See [docs/okf-conventions.md](../docs/okf-conventions.md).

Non-markdown files (images, for example) are copied too. Each needs a concept file
beside it that describes it and links to it, e.g. `building/layout.md` for
`building/layout.png`; otherwise nothing in the bundle leads an agent to it.
