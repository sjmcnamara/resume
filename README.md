# resume

Single-source résumé: [`resume.json`](resume.json) → a one-page web version and a
matching print-ready PDF, both published to GitHub Pages.

- **Web:** https://sjmcnamara.com
- **PDF:** https://sjmcnamara.com/stephen-mcnamara.pdf

`www.sjmcnamara.com` and the old `sjmcnamara.github.io/resume/` both redirect to
the apex, so links shared before the domain move still work.

Both are generated from the same file on every push to `master`, so the PDF you
email a recruiter can never drift from the page you link.

## Editing

Edit `resume.json` and push. That's the whole workflow.

The file follows the [JSON Resume](https://jsonresume.org/schema/) v1.0.0 schema,
with three additions the renderer understands:

| Field | Where | Effect |
| --- | --- | --- |
| `x_compact: true` | a `work` entry | Renders as a single dateline under "Earlier career" — no bullets |
| `x_hidden: true` | a `work`, `education` or `languages` entry | Kept in the file, left off the page |
| `meta.x_compactHeading` | `meta` | Heading used for the compact block |

`x_hidden` is how the education and languages entries are parked: the data stays
here, it just doesn't earn its space on the page. Flip the flag to bring it back.

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

`sjmcnamara.com` is registered at name.com and serves the site over HTTPS
(enforced; the certificate covers the apex and `www`).

DNS at name.com — all four A records are required, since Pages load-balances
across them and a partial set fails intermittently:

```
A      @      185.199.108.153
A      @      185.199.109.153
A      @      185.199.110.153
A      @      185.199.111.153
AAAA   @      2606:50c0:8000::153
AAAA   @      2606:50c0:8001::153
AAAA   @      2606:50c0:8002::153
AAAA   @      2606:50c0:8003::153
CNAME  www    sjmcnamara.github.io.
```

The domain lives in the [`CNAME`](CNAME) file at the repo root, and **`build.py`
copies it into `dist/`** on every build. That copy is the part that matters: the
workflow publishes `dist/`, so a `CNAME` sitting only at the repo root never
reaches Pages and the custom domain silently fails to apply.

To change domains: edit `CNAME`, update `basics.url` in `resume.json`, repoint
DNS, and set the new domain under Settings → Pages.

## History

This repo previously pushed `resume.json` to a GitHub Gist and relied on
`registry.jsonresume.org` to render it. That is gone: the registry's PDF endpoint
returns HTTP 400, and it put three third parties (a token, an action, someone
else's server) between an edit and the live page.
