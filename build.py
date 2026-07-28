#!/usr/bin/env python3
"""Render resume.json to a single-page HTML sheet and a print-ready PDF.

    python3 build.py            # HTML only  -> dist/index.html
    python3 build.py --pdf      # HTML + PDF -> dist/stephen-mcnamara.pdf
    python3 build.py --emit-cards   # project cards for the MkDocs landing page

PDF generation shells out to headless Chrome; no npm dependencies, nothing to
install on either macOS or the GitHub Actions ubuntu runner.

The published site puts the sheet under /resume/ and the PDF at the site root,
so --out and --pdf-out can point at different directories; the download link is
worked out relative to whichever pair is in play.
"""

import argparse
import html
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent
DIST = ROOT / "dist"
CARDS = ROOT / "docs" / ".generated" / "projects.md"
PDF_NAME = "stephen-mcnamara.pdf"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome-stable",
    "google-chrome",
    "chromium-browser",
    "chromium",
]


def esc(text):
    return html.escape(str(text or ""))


def month_year(date):
    """'2021-08-31' -> 'Aug 2021'. Bare years pass through."""
    if not date:
        return ""
    parts = str(date).split("-")
    if len(parts) >= 2:
        return f"{MONTHS[int(parts[1]) - 1]} {parts[0]}"
    return parts[0]


def year(date):
    return str(date).split("-")[0] if date else ""


def span(job, years_only=False):
    fmt = year if years_only else month_year
    start = fmt(job.get("startDate"))
    end = fmt(job.get("endDate")) if job.get("endDate") else "Present"
    return f"{start} – {end}" if start else end


def role_block(job, compact=False):
    """One work entry. Compact entries are a single dateline, no bullets."""
    meta = span(job, years_only=compact)
    if job.get("location") and not compact:
        meta = f"{esc(job['location'])} &nbsp;·&nbsp; {meta}"

    org = esc(job.get("name"))
    if job.get("url"):
        org = f'<a href="{esc(job["url"])}">{org}</a>'

    out = [
        '<div class="role">',
        '  <div class="role-head">',
        f'    <div class="role-title"><span class="role-org">{org}</span>'
        f'<span class="role-pos">{esc(job.get("position"))}</span></div>',
        f'    <div class="role-meta">{meta}</div>',
        "  </div>",
    ]

    highlights = job.get("highlights") or []
    if highlights and not compact:
        out.append('  <ul class="highlights">')
        out += [f"    <li>{esc(h)}</li>" for h in highlights]
        out.append("  </ul>")
    out.append("</div>")
    return "\n".join(out)


def render(resume, css, pdf_href=PDF_NAME):
    def visible(items):
        """Entries carrying x_hidden stay in resume.json but leave the page."""
        return [i for i in items if not i.get("x_hidden")]

    basics = resume.get("basics", {})
    work = visible(resume.get("work", []))
    meta = resume.get("meta", {})

    full = [j for j in work if not j.get("x_compact")]
    compact = [j for j in work if j.get("x_compact")]

    def shorten(url):
        return url.replace("https://www.", "").replace("https://", "").rstrip("/")

    contact = []
    if basics.get("email"):
        contact.append(f'<a href="mailto:{esc(basics["email"])}">{esc(basics["email"])}</a>')
    if basics.get("phone"):
        contact.append(esc(basics["phone"]))
    for profile in basics.get("profiles", []):
        url = profile.get("url", "")
        contact.append(f'<a href="{esc(url)}">{esc(shorten(url))}</a>')

    # Site rides on the location line. A fourth contact row grows the masthead
    # and costs a line of body copy; widening a row squeezes the label into
    # wrapping. Pairing with the short location line avoids both.
    last = []
    if basics.get("url"):
        last.append(f'<a href="{esc(basics["url"])}">{esc(shorten(basics["url"]))}</a>')
    if basics.get("location", {}).get("address"):
        last.append(esc(basics["location"]["address"]))
    if last:
        contact.append(" &nbsp;·&nbsp; ".join(last))

    parts = [
        '<div class="sheet">',
        '<header class="masthead">',
        "  <div>",
        f'    <h1>{esc(basics.get("name"))}</h1>',
        f'    <div class="label">{esc(basics.get("label"))}</div>',
        "  </div>",
        f'  <div class="contact">{"<br>".join(contact)}</div>',
        "</header>",
    ]

    if basics.get("summary"):
        parts.append(f'<p class="summary">{esc(basics["summary"])}</p>')

    parts += ["<section>", "<h2>Experience</h2>"]
    parts += [role_block(j) for j in full]
    parts.append("</section>")

    if compact:
        parts += [
            '<section class="earlier">',
            f'<h2>{esc(meta.get("x_compactHeading", "Earlier career"))}</h2>',
        ]
        parts += [role_block(j, compact=True) for j in compact]
        parts.append("</section>")

    projects = visible(resume.get("projects", []))
    if projects:
        parts += ["<section>", f'<h2>{esc(meta.get("x_projectsHeading", "Projects"))}</h2>']
        for proj in projects:
            name = esc(proj.get("name"))
            if proj.get("url"):
                name = f'<a href="{esc(proj["url"])}">{name}</a>'
            parts += [
                '<div class="role">',
                f'  <div class="proj"><span class="role-org">{name}</span>'
                f'<span class="role-pos">{esc(proj.get("description"))}</span></div>',
                "</div>",
            ]
        parts.append("</section>")

    tail = []
    for edu in visible(resume.get("education", [])):
        degree = " ".join(x for x in [edu.get("studyType"), edu.get("area")] if x)
        tail.append(
            "<div>"
            f'<div class="line">{esc(degree)}</div>'
            f'<div class="sub">{esc(edu.get("institution"))} &nbsp;·&nbsp; '
            f"{esc(year(edu.get('startDate')))}–{esc(year(edu.get('endDate')))}</div>"
            "</div>"
        )
    langs = ", ".join(
        f"{l.get('language')} ({l.get('fluency')})" if l.get("fluency") else l.get("language", "")
        for l in visible(resume.get("languages", []))
    )
    if langs:
        tail.append(f'<div><div class="line">Languages</div><div class="sub">{esc(langs)}</div></div>')

    if tail:
        parts += ["<section>", "<h2>Education</h2>", '<div class="tail">'] + tail + ["</div>", "</section>"]

    parts.append("</div>")
    # Screen-only footer: back to the landing page on the left, PDF on the right.
    # The home link is absolute so it still points somewhere useful when the
    # sheet is opened straight off disk out of dist/.
    home = esc(basics.get("url") or "/")
    parts.append(
        '<div class="actions">'
        f'<a class="back" href="{home}">← sjmcnamara.com</a>'
        f'<a href="{esc(pdf_href)}" download>Download PDF</a>'
        "</div>"
    )

    body = "\n".join(parts)
    title = f'{basics.get("name", "Resume")} — {basics.get("label", "")}'.strip(" —")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(basics.get('summary', '')[:180])}">
<style>
{css}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def emit_cards(resume, path=CARDS):
    """Write the landing page's project grid from resume.json.

    Every project lands here, including the ones carrying x_hidden — that flag
    keeps an entry off the one-page sheet, not off the site.
    """
    # Markdown, not HTML: quotes and apostrophes have to survive as themselves
    # rather than as entities, so only the tag-forming characters get escaped.
    def md(text):
        return html.escape(str(text or ""), quote=False)

    cards = ['<div class="grid cards" markdown>', ""]
    for proj in resume.get("projects", []):
        name = md(proj.get("name"))
        if proj.get("url"):
            name = f'[{name}]({proj["url"]})'
        cards.append(f"-   __{name}__")
        cards.append("")
        cards.append(f'    {md(proj.get("description", ""))}')
        tagline = proj.get("x_tagline") or " · ".join(proj.get("keywords", [])[:3])
        if tagline:
            cards.append("")
            cards.append(f'    <span class="card-tags">{md(tagline)}</span>')
        cards.append("")
    cards.append("</div>")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(cards) + "\n")
    print(f"wrote {path}")


def find_chrome():
    for candidate in CHROME_CANDIDATES:
        resolved = candidate if pathlib.Path(candidate).exists() else shutil.which(candidate)
        if resolved:
            return resolved
    return None


def make_pdf(html_path, pdf_path):
    chrome = find_chrome()
    if not chrome:
        sys.exit("error: no Chrome/Chromium binary found for PDF rendering")
    subprocess.run(
        [
            chrome,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            html_path.resolve().as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    print(f"wrote {pdf_path}  ({pdf_path.stat().st_size // 1024} KB)")


def page_count(pdf_path):
    data = pdf_path.read_bytes()
    return len(re.findall(rb"/Type\s*/Page[^s]", data))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", action="store_true", help="also render the PDF")
    ap.add_argument("--check", action="store_true",
                    help="with --pdf, exit non-zero unless the PDF is exactly one page")
    ap.add_argument("--out", default=DIST, type=pathlib.Path,
                    help="directory for index.html (default: dist/)")
    ap.add_argument("--pdf-out", default=None, type=pathlib.Path,
                    help="directory for the PDF (default: same as --out)")
    ap.add_argument("--emit-cards", action="store_true",
                    help="write the landing page's project grid and stop")
    args = ap.parse_args()

    resume = json.loads((ROOT / "resume.json").read_text())

    # MkDocs needs the snippet on disk before it builds, so this runs on its own
    # ahead of the site build as well as alongside every ordinary sheet render.
    emit_cards(resume)
    if args.emit_cards:
        return

    css = (ROOT / "assets" / "style.css").read_text()
    out = args.out
    pdf_dir = args.pdf_out or out

    out.mkdir(parents=True, exist_ok=True)
    html_path = out / "index.html"
    pdf_path = pdf_dir / PDF_NAME
    pdf_href = os.path.relpath(pdf_path, out)
    html_path.write_text(render(resume, css, pdf_href))
    print(f"wrote {html_path}")

    if args.pdf:
        pdf_dir.mkdir(parents=True, exist_ok=True)
        make_pdf(html_path, pdf_path)
        pages = page_count(pdf_path)
        print(f"page count: {pages}")
        if args.check and pages != 1:
            sys.exit(f"error: resume rendered to {pages} pages; it must fit on one")


if __name__ == "__main__":
    main()
