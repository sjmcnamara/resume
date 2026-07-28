# sjmcnamara.com

A landing page and a single-source résumé, published together to GitHub Pages.

- **Landing:** https://sjmcnamara.com
- **Résumé:** https://sjmcnamara.com/resume/
- **PDF:** https://sjmcnamara.com/stephen-mcnamara.pdf

`www.sjmcnamara.com` and the old `sjmcnamara.github.io/resume/` both redirect to
the apex, so links shared before the domain move still work. The PDF has kept its
path since before the landing page existed, so anything already emailed to a
recruiter still resolves.

Everything comes from [`resume.json`](resume.json) — bio, roles, project list —
so the PDF you send can never drift from the page you link.

## Two renderers, one site

The landing page is [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/).
The résumé is not: [`build.py`](build.py) renders it to a self-contained HTML
sheet with its CSS inlined, and headless Chrome turns that into the PDF.

Keeping them apart is deliberate. Material ships its own stylesheet and print
rules; running the sheet through it reflows the layout and quietly costs the
one-page guarantee. So MkDocs builds `site/`, and then `build.py` *writes into*
that directory:

```
python3 build.py --emit-cards                                # docs/.generated/projects.md
mkdocs build --strict                                        # site/
python3 build.py --pdf --check --out site/resume --pdf-out site
```

`--emit-cards` goes first because MkDocs needs the generated snippet on disk
before it builds. The PDF is written to the site root while the sheet goes to
`site/resume/`; `build.py` works out the download link between the two.

```
mkdocs.yml            docs/index.md          landing page copy
requirements.txt      docs/assets/home.css   landing page styling
build.py              docs/assets/headshot.jpg
resume.json           docs/CNAME             custom domain
assets/style.css      docs/.generated/       cards, generated, gitignored
```

## Editing

Edit `resume.json` and push. That's still the whole workflow — a new project
appears on the landing page and, unless hidden, on the résumé too.

The file follows the [JSON Resume](https://jsonresume.org/schema/) v1.0.0 schema,
with a few additions the renderers understand:

| Field | Where | Effect |
| --- | --- | --- |
| `x_compact: true` | a `work` entry | Renders as a single dateline under "Earlier career" — no bullets |
| `x_hidden: true` | a `work`, `education`, `languages` or `projects` entry | Kept in the file, left off the **résumé**. Projects still appear on the landing page |
| `x_tagline` | a `projects` entry | The small caps line under a landing-page card; falls back to the first three `keywords` |
| `x_repo` | a `projects` entry | `owner/name` on GitHub, for reference |
| `meta.x_compactHeading` | `meta` | Heading used for the compact block |

`x_hidden` does double duty. On education and languages it parks data that
doesn't earn its space. On projects it's the release valve for the page budget:
all four projects show on the landing page, only Whistle is on the sheet.

The résumé is tuned to fit **one page** and the build fails if it doesn't, so if
you add a role, tighten or compact another.

Landing page copy lives in [`docs/index.md`](docs/index.md); its styling is in
[`docs/assets/home.css`](docs/assets/home.css). The résumé's layout is in
[`assets/style.css`](assets/style.css), with print rules in the `@media print`
block and the `@page` rule at the bottom.

## The landing page

A mac window. Material's header is restyled into the title bar — traffic lights,
rounded top corners, theme toggle — and the content area becomes the window body,
with the hero, portrait and project cards sitting on it as rounded panels.

Things that are load-bearing rather than decorative, and will break if changed
without care:

- **`.md-header` is `position: static`.** That's what lets the header sit inside
  the window instead of over it. It also removed the positioning context the
  palette's `position: absolute` radio inputs relied on, which sent them to the
  foot of the document — clicking the toggle then scrolled the page down 1200px.
  `.md-header__option` carries `position: relative` to re-anchor them.
- **`[data-md-color-primary] .md-header`** beats a bare `.md-header`, so the
  background reset needs the doubled selector or the header paints a coloured
  band across the desktop behind the window.
- **Material's own footer is hidden.** It's a dark full-bleed bar that sits
  below the window and breaks the frame. `extra.social` went with it, since
  those icons only ever rendered there.
- **`font: false`.** Naming fonts in `theme.font` makes Material fetch them from
  `fonts.googleapis.com` and `fonts.gstatic.com` on every visit. The system stack
  is the same `-apple-system` family the résumé sheet uses, so the two pages
  match and nothing third-party is requested.
- **Dark is the default.** Neither palette entry carries a `media` key, so the
  first one wins regardless of system preference. The toggle still remembers.
- **`plugins: []`** turns off search. One page has nothing to search, and the
  empty box cluttered the bar it turns into.

### The phone breakpoint is written twice

`home.css` hides the portrait below `44.9375em`; `docs/index.md` hands the same
width a 43-byte transparent GIF through `<picture>`.

Both are needed. `display: none` alone still downloads the 160KB JPEG, and
`loading="lazy"` does not help — a hidden image is fetched anyway (measured, in
Chrome). `<picture>` alone leaves an empty panel where the photo was.

CSS can't read a value out of the markup, so `build.py` compares the two on every
build and exits non-zero if they drift. A mismatch fails the build instead of
shipping a missing photo.

## Building locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

python3 build.py --emit-cards    # regenerate the cards from resume.json
.venv/bin/mkdocs serve           # landing page at localhost:8000, live reload

python3 build.py                 # dist/index.html — the sheet on its own
python3 build.py --pdf           # + dist/stephen-mcnamara.pdf
python3 build.py --pdf --check   # + fail unless the PDF is exactly one page
```

`mkdocs serve` won't show `/resume/`, since the sheet isn't built by MkDocs. To
see the whole site as it deploys, run the three-step sequence above and serve
`site/`.

`build.py` still needs nothing but a stdlib Python and a Chrome binary, which is
already present on macOS and on the GitHub Actions Ubuntu runner. MkDocs is the
site's only dependency, pinned in [`requirements.txt`](requirements.txt) below
2.0 — that release drops the plugin system and rewrites theming with no
migration path.

`docs/.generated/` is gitignored. Run `--emit-cards` after editing `resume.json`
or `mkdocs serve` will fail on the missing snippet.

## Publishing

`.github/workflows/publish.yml` runs the three build steps above and deploys
`site/` to Pages. `--check` is the guard rail: a change that pushes the résumé
onto a second page fails the build instead of quietly publishing a two-page PDF.

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

The domain lives in [`docs/CNAME`](docs/CNAME), which MkDocs copies verbatim into
`site/`. That copy is the part that matters: the workflow publishes `site/`, so a
`CNAME` sitting anywhere else never reaches Pages and the custom domain silently
fails to apply.

To change domains: edit `docs/CNAME`, update `basics.url` in `resume.json` and
`site_url` in `mkdocs.yml`, repoint DNS, and set the new domain under
Settings → Pages.

## History

This repo previously pushed `resume.json` to a GitHub Gist and relied on
`registry.jsonresume.org` to render it. That is gone: the registry's PDF endpoint
returns HTTP 400, and it put three third parties (a token, an action, someone
else's server) between an edit and the live page.

The résumé also used to be the site root. It moved to `/resume/` when the landing
page arrived; nothing 404s, since `/resume/` is a new address rather than a
renamed one.
