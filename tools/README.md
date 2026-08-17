# tools

`build-report-page.py` regenerates [`/report/`](https://vibeward.ai/sample-report/) and
[`/es/informe/`](https://vibeward.ai/es/informe-de-ejemplo/) from a vibeward report.

Nothing on vibeward.ai runs Python. The published pages are plain static HTML; this only exists so
that refreshing the sample report for a new version is a command rather than rewriting the renderer.

## Regenerating

```bash
python3 tools/build-report-page.py --emit-demo /tmp/demo
cd /tmp/demo && python3 -m http.server 8099 &

npx vibeward@latest http://localhost:8099/ --yes
npx vibeward@latest http://localhost:8099/ --yes --lang es

python3 tools/build-report-page.py --build vibeward-report-localhost_8099.md informe-localhost_8099.md
```

Then **rescan the deployed site** before considering it done:

```bash
npx vibeward@latest https://vibeward.ai --yes
```

## Three things that are not arbitrary

**The bearer token on the page is a placeholder.** `--emit-demo` writes a real 48-hex value so the
scan has something to find, but the page prints `PUT_ANY_48_HEX_CHARACTERS_HERE`. This is not
squeamishness. With the real value rendered inside a `<pre>`, **vibeward.ai reports itself** with a
high-severity `hardcoded_bearer` — correctly, because a literal that reaches an `Authorization`
header is exactly what the rule matches and it cannot tell a demo from a deployment. And there is no
way out through configuration: `vibeward.json` can only suppress `kind: "web"` ids, never security
findings. That is deliberate, and it applies to its own author's website too.

**The report's headings are demoted one level** at render time. The page owns the only `<h1>`;
letting the report keep its own would put two on the page, which is a finding vibeward reports.
The build asserts this rather than trusting it.

**Fonts and palette are read out of `index.html`** at build time instead of being copied here, so
the report page cannot drift from the landing page it is supposed to belong to.

## After regenerating

The pages are self-contained, but three things outside them refer to the report and are maintained
by hand: the nav link in `index.html` and `es/index.html`, the entry in `llms.txt`, and the two
`<loc>` blocks in `sitemap.xml` (update `lastmod`).
