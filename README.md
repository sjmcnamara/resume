# resume

Single-source résumé: [`resume.json`](resume.json) → a one-page web version and a
matching print-ready PDF, both published to GitHub Pages.

- **Web:** https://sjmcnamara.github.io/resume/
- **PDF:** https://sjmcnamara.github.io/resume/stephen-mcnamara.pdf

Both are generated from the same file on every push to `master`, so the PDF you
email a recruiter can never drift from the page you link.

## Editing

Edit `resume.json` and push. That's the whole workflow.

The file follows the [JSON Resume](https://jsonresume.org/schema/) v1.0.0 schema,
with two additions the renderer understands:

| Field | Where | Effect |
| --- | --- | --- |
| `x_compact: true` | a `work` entry | Renders as a single dateline under "Earlier career" — no bullets |
| `meta.x_compactHeading` | `meta` | Heading used for the compact block |

Everything is tuned to fit **one page**. The build fails if it doesn't (see below),
so if you add a role, tighten or compact another.

## Building locally

```bash
python3 build.py                 # dist/index.html
python3 build.py --pdf           # + dist/stephen-mcnamara.pdf
python3 build.py --pdf --check   # + fail unless the PDF is exactly one page
```

No npm, no package installs. PDF rendering shells out to headless Chrome, which
is already present on macOS and on the GitHub Actions Ubuntu runner.

Layout lives in [`assets/style.css`](assets/style.css); print rules are in the
`@media print` block and the `@page` rule at the bottom.

## Publishing

`.github/workflows/publish.yml` runs `build.py --pdf --check` and deploys `dist/`
to Pages. `--check` is the guard rail: a change that pushes the résumé onto a
second page fails the build instead of quietly publishing a two-page PDF.

Pages must be set to **GitHub Actions** as its source (Settings → Pages → Build
and deployment → Source).

### Custom domain

Add a `CNAME` file at the repo root containing the bare domain (e.g.
`stephenmcnamara.com`), point a DNS `CNAME`/`ALIAS` at `sjmcnamara.github.io`,
then set the domain under Settings → Pages. Also update `basics.url` in
`resume.json`.

## History

This repo previously pushed `resume.json` to a GitHub Gist and relied on
`registry.jsonresume.org` to render it. That is gone: the registry's PDF endpoint
returns HTTP 400, and it put three third parties (a token, an action, someone
else's server) between an edit and the live page.
