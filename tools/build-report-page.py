#!/usr/bin/env python3
"""Regenerates /sample-report/ and /es/informe-de-ejemplo/ from a vibeward report.

The published pages are plain static HTML — nothing on vibeward.ai runs Python.
This exists so the next version of the report is a command rather than a rewrite.

    python3 tools/build-report-page.py --emit-demo /tmp/demo
    cd /tmp/demo && python3 -m http.server 8099 &
    npx vibeward@latest http://localhost:8099/ --yes
    npx vibeward@latest http://localhost:8099/ --yes --lang es
    python3 tools/build-report-page.py --build <en.md> <es.md>

See tools/README.md for why the token on the page is a placeholder. It is not
cosmetic: with a real value printed there, vibeward.ai reports itself.
"""

import argparse
import html
import os
import re
import secrets
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --------------------------------------------------------------------------
# The demo app. Broken on purpose, and the fixture the report comes from.
# --------------------------------------------------------------------------

DEMO_INDEX = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Nimbus Invoices</title>
</head>
<body>
<h1>Nimbus Invoices</h1>
<p>Send invoices in seconds. Built in a weekend.</p>
<a href="app.html">Open the app</a>
<img src="logo.png">
<script src="assets/app.js"></script>
</body>
</html>"""

DEMO_APP = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Nimbus Invoices</title>
</head>
<body>
<h1>Dashboard</h1>
<div id="root"></div>
<script src="assets/app.js"></script>
</body>
</html>"""

# `%s` is the bearer value: a real 48-hex fixture when emitting the app to scan,
# a placeholder when rendering the page. Same file, two audiences.
DEMO_JS = """//# sourceMappingURL=app.js.map
var SUPABASE_URL = "https://abcdefghijklmnop.supabase.co";
var SUPABASE_ANON_KEY = "sb_publishable_9f2c1d4e7a8b3c5d6e0f1a2b";
var B = "%s";
function api(p) {
  return fetch(SUPABASE_URL + p, {
    headers: { apikey: SUPABASE_ANON_KEY, Authorization: "Bearer ".concat(B) }
  });
}
window.api = api;"""

DEMO_MAP = (
    '{"version":3,"file":"app.js","sources":["../src/app.ts"],'
    '"sourcesContent":["const B = process.env.BILLING_TOKEN;\\n'
    'export function api(p: string) { return fetch(p); }\\n"],'
    '"names":[],"mappings":"AAAA"}'
)

PLACEHOLDER = "PUT_ANY_48_HEX_CHARACTERS_HERE"


def emit_demo(target):
    os.makedirs(os.path.join(target, "assets"), exist_ok=True)
    write = lambda p, s: open(os.path.join(target, p), "w", encoding="utf-8").write(s)
    write("index.html", DEMO_INDEX)
    write("app.html", DEMO_APP)
    # Generated, never committed: a literal here would be a credential-shaped
    # string in a public repository, which is the thing this app exists to find.
    write(os.path.join("assets", "app.js"), DEMO_JS % secrets.token_hex(24))
    write(os.path.join("assets", "app.js.map"), DEMO_MAP)
    print(f"demo app written to {target}")


# --------------------------------------------------------------------------
# Markdown, restricted to what a vibeward report actually emits
# --------------------------------------------------------------------------

SEV = {"🔴": "crit", "🟠": "high", "🟡": "med", "⚪": "low", "✅": "ok", "❌": "no"}


def sev_class(line):
    for mark, name in SEV.items():
        if mark in line:
            return name
    return ""


def inline(t):
    """Escape first, then apply inline markdown — the report prints <title> as text."""
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])_([^_]+)_(?![\w*])", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
               r'<a href="\2" rel="noopener noreferrer nofollow">\1</a>', t)
    t = re.sub(r"&lt;(https?://[^&\s]+)&gt;",
               r'<a href="\1" rel="noopener noreferrer nofollow">\1</a>', t)
    return t


def convert(md):
    out, i, lines = [], 0, md.split("\n")
    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        if line.startswith("---") and set(line.strip()) == {"-"}:
            out.append("<hr>")
            i += 1
            continue

        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            # Demoted one level: the page owns the only <h1>, and two of them is
            # a finding this very tool reports.
            lvl = min(len(m.group(1)) + 1, 6)
            cls = sev_class(m.group(2))
            attr = f' class="f {cls}"' if cls and lvl >= 4 else ""
            out.append(f"<h{lvl}{attr}>{inline(m.group(2))}</h{lvl}>")
            i += 1
            continue

        if line.startswith(">"):
            body = []
            while i < len(lines) and lines[i].startswith(">"):
                body.append(lines[i].lstrip("> ").rstrip())
                i += 1
            out.append(f'<blockquote>{inline(" ".join(body))}</blockquote>')
            continue

        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1]):
            head = [c.strip() for c in line.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            th = "".join(f"<th>{inline(c)}</th>" for c in head)
            tb = ""
            for r in rows:
                td = "".join(f"<td>{inline(c)}</td>" for c in r)
                tb += f'<tr class="{sev_class(" ".join(r))}">{td}</tr>'
            out.append(f'<div class="tw"><table><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>')
            continue

        if re.match(r"^[-*]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i]):
                items.append("<li>" + inline(re.sub(r"^[-*]\s+", "", lines[i])) + "</li>")
                i += 1
            out.append(f'<ul>{"".join(items)}</ul>')
            continue

        para = []
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,4}\s|\||>|---|[-*]\s)", lines[i]):
            para.append(lines[i].strip())
            i += 1
        if para:
            out.append(f'<p>{inline(" ".join(para))}</p>')

    return "\n".join(out)


# --------------------------------------------------------------------------
# The page
# --------------------------------------------------------------------------

def base_css():
    """Fonts and palette come from the landing page, so the two cannot drift."""
    src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    style = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
    faces = re.findall(r"@font-face\s*\{.*?\}", style, re.S)
    root = re.search(r":root\s*\{.*?\}", style, re.S).group(0)
    return "\n".join(faces) + "\n" + root


PAGE_CSS = """
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:'Instrument Sans',system-ui,-apple-system,sans-serif;
  font-size:16px;line-height:1.62;-webkit-font-smoothing:antialiased}
a{color:var(--clay-deep)}
.wrap{max-width:820px;margin:0 auto;padding:0 22px}
header.top{border-bottom:1px solid var(--line-soft);padding:18px 0;position:sticky;top:0;
  background:color-mix(in srgb,var(--paper) 92%,transparent);backdrop-filter:blur(8px);z-index:5}
header.top .wrap{display:flex;align-items:center;justify-content:space-between;gap:16px}
.brand{font-family:'IBM Plex Mono',monospace;font-weight:600;letter-spacing:-.02em;
  color:var(--ink);text-decoration:none;font-size:15px}
.brand span{color:var(--clay)}
.navr{display:flex;gap:18px;align-items:center;font-size:14px}
.navr a{color:var(--ink);opacity:.72;text-decoration:none}
.navr a:hover{opacity:1}
.intro{padding:54px 0 6px}
.k{font-family:'IBM Plex Mono',monospace;font-size:11.5px;letter-spacing:.14em;
  text-transform:uppercase;color:var(--clay);display:block;margin-bottom:14px}
h1.page{font-family:'Newsreader',Georgia,serif;font-weight:500;font-size:clamp(30px,5vw,46px);
  line-height:1.1;letter-spacing:-.02em;margin:0 0 18px}
.lead{font-size:17.5px;color:color-mix(in srgb,var(--ink) 82%,transparent);margin:0 0 20px}
.note{border:1px solid var(--clay-line);background:var(--clay-wash);border-radius:10px;
  padding:18px 20px;margin:26px 0 0}
.note h3{font-family:'IBM Plex Mono',monospace;font-size:12px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--clay-deep);margin:0 0 10px}
.note p{margin:0 0 12px;font-size:15px}
.note p:last-child{margin-bottom:0}
.report{margin:44px 0 0;padding:34px 0 0;border-top:1px solid var(--line)}
.report h2:first-child{font-family:'Newsreader',Georgia,serif;font-weight:500;font-size:28px;margin:0 0 22px;border:0;padding:0}
.report h3{font-family:'Newsreader',Georgia,serif;font-weight:500;font-size:24px;
  margin:44px 0 14px;padding-bottom:8px;border-bottom:1px solid var(--line-soft)}
.report h4{font-size:17px;margin:34px 0 12px;font-weight:600;letter-spacing:-.01em}
.report h5{font-size:15.5px;margin:26px 0 10px;font-weight:600}
.report h4.f,.report h5.f{padding-left:13px;border-left:3px solid var(--line)}
.report .crit{border-left-color:var(--crit)}
.report .high{border-left-color:var(--clay)}
.report .med{border-left-color:var(--amber)}
.report .low{border-left-color:#6b6355}
.report p{margin:0 0 12px;font-size:15.5px}
.report ul{margin:0 0 14px;padding-left:20px}
.report li{margin:0 0 6px;font-size:15.5px}
.report hr{border:0;border-top:1px solid var(--line-soft);margin:34px 0}
.report blockquote{margin:0 0 18px;padding:14px 18px;border-left:3px solid var(--clay);
  background:var(--paper-warm);border-radius:0 8px 8px 0;font-size:16px}
code{font-family:'IBM Plex Mono',monospace;font-size:.88em;background:var(--term-bg);
  border:1px solid var(--line-soft);border-radius:5px;padding:1px 5px;word-break:break-word}
.tw{overflow-x:auto;margin:0 0 20px;border:1px solid var(--line);border-radius:9px}
table{border-collapse:collapse;width:100%;font-size:14.5px;min-width:420px}
th{text-align:left;font-family:'IBM Plex Mono',monospace;font-size:11.5px;letter-spacing:.08em;
  text-transform:uppercase;color:color-mix(in srgb,var(--ink) 62%,transparent);
  padding:11px 14px;background:var(--paper-warm);border-bottom:1px solid var(--line)}
td{padding:11px 14px;border-bottom:1px solid var(--line-soft);vertical-align:top}
tbody tr:last-child td{border-bottom:0}
pre{font-family:'IBM Plex Mono',monospace;background:var(--term-bg);border:1px solid var(--line);
  border-radius:9px;padding:16px 18px;overflow-x:auto;font-size:13px;line-height:1.55;margin:0 0 16px}
.repro{margin:52px 0 0;padding:30px 0 0;border-top:1px solid var(--line)}
.repro h2{font-family:'Newsreader',Georgia,serif;font-weight:500;font-size:23px;margin:0 0 12px}
.repro p{font-size:15.5px;color:color-mix(in srgb,var(--ink) 84%,transparent)}
.fname{font-family:'IBM Plex Mono',monospace;font-size:11.5px;letter-spacing:.06em;
  color:var(--clay);margin:20px 0 7px}
footer.btm{margin:60px 0 0;border-top:1px solid var(--line-soft);padding:26px 0 60px;
  font-size:14px;color:color-mix(in srgb,var(--ink) 60%,transparent)}
footer.btm a{color:color-mix(in srgb,var(--ink) 78%,transparent)}
@media (max-width:640px){.intro{padding-top:34px}.report h3{font-size:21px}}
"""

T = {
    "en": {
        "out": "sample-report/index.html",
        "home": "/",
        "canon": "https://vibeward.ai/sample-report/",
        "alt": "/es/informe-de-ejemplo/",
        "altlabel": "ES",
        "title": "Sample report · vibeward",
        "desc": "A complete, unedited vibeward report, produced by scanning a deliberately broken demo app. See what the tool prints before installing anything.",
        "k": "Sample report",
        "h1": "What it actually prints",
        "lead": "This is a complete report, unedited. It came from scanning a deliberately broken demo app served on <code>localhost</code> — not somebody's live site, which is why the address in it says so. Every competing scanner shows you a screenshot of a dashboard; this is the artefact you would hand a client.",
        "noteh": "Two things worth reading closely",
        "notes": [
            "The <strong>hardcoded bearer token</strong> is found by its <em>use</em>, not its shape. After minification the variable is a single letter and the value has no vendor prefix, so there is nothing to pattern-match: what gives it away is a literal that ends up behind <code>Bearer</code>. A token the client obtains at login is an identifier with no literal, and stays silent.",
            "The Supabase <strong>publishable key three lines above it is reported as nothing at all.</strong> It belongs in the client by design, and a scanner that flags it is training you to ignore the scanner. Six of eight findings on a real corpus used to be exactly that kind of noise.",
            "The website section is scored on its own scale. It never affects the security verdict, the SARIF file or the exit code — a missing favicon is not a finding next to a leaked credential.",
        ],
        "reproh": "The app that produces it",
        "reprop": "Four files, broken on purpose. Nothing here is a real credential: the Supabase key is a syntactically valid value that points nowhere, and the bearer token is written as a placeholder — put any 48 hex characters there and you get the report above. <strong>The placeholder is not squeamishness, it is the tool working.</strong> With the real value printed here, this very page scanned as a hardcoded bearer token in client code, because a literal that reaches an <code>Authorization</code> header is exactly what the rule looks for and it cannot tell a demo from a deployment. A placeholder is not credential-shaped, so it stays silent — and security findings cannot be suppressed by config, by design.",
        "cmd": "python3 -m http.server 8099\nnpx vibeward@latest http://localhost:8099/ --yes",
        "foot": "Generated by vibeward. It detects and reports; it never fixes.",
    },
    "es": {
        "out": "es/informe-de-ejemplo/index.html",
        "home": "/es/",
        "canon": "https://vibeward.ai/es/informe-de-ejemplo/",
        "alt": "/sample-report/",
        "altlabel": "EN",
        "title": "Informe de ejemplo · vibeward",
        "desc": "Un informe completo de vibeward, sin editar, generado escaneando una app rota a propósito. Mira lo que imprime la herramienta antes de instalar nada.",
        "k": "Informe de ejemplo",
        "h1": "Lo que imprime de verdad",
        "lead": "Este es un informe completo, sin editar. Salió de escanear una app rota a propósito servida en <code>localhost</code> — no el sitio en vivo de nadie, y por eso la dirección que aparece dentro lo dice. Todos los escáneres de la competencia te enseñan la captura de un panel; esto es el entregable que le pasarías a un cliente.",
        "noteh": "Dos cosas que conviene leer despacio",
        "notes": [
            "El <strong>token bearer hardcodeado</strong> se detecta por su <em>uso</em>, no por su forma. Tras minificar, la variable es una sola letra y el valor no tiene prefijo de proveedor, así que no hay patrón que buscar: lo que lo delata es un literal que acaba detrás de <code>Bearer</code>. Un token que el cliente obtiene al hacer login es un identificador sin literal, y se queda callado.",
            "La clave <strong>publishable de Supabase que está tres líneas más arriba no se reporta en absoluto.</strong> Va en el cliente por diseño, y un escáner que la marca te está enseñando a ignorar al escáner. Seis de ocho hallazgos sobre un corpus real eran exactamente ese tipo de ruido.",
            "La sección de web se puntúa en su propia escala. Nunca afecta al veredicto de seguridad, ni al archivo SARIF, ni al código de salida — un favicon que falta no es un hallazgo al lado de una credencial filtrada.",
        ],
        "reproh": "La app que lo genera",
        "reprop": "Cuatro archivos, rotos a propósito. Nada de esto es una credencial real: la clave de Supabase es un valor sintácticamente válido que no apunta a ningún sitio, y el token bearer está escrito como placeholder — pon ahí 48 caracteres hex cualesquiera y te sale el informe de arriba. <strong>El placeholder no es remilgo, es la herramienta funcionando.</strong> Con el valor real impreso aquí, esta misma página se escaneaba como token bearer hardcodeado en código cliente, porque un literal que llega a una cabecera <code>Authorization</code> es justo lo que busca la regla y no puede distinguir una demo de un despliegue. Un placeholder no tiene forma de credencial, así que se queda callado — y los hallazgos de seguridad no se pueden suprimir por configuración, por diseño.",
        "cmd": "python3 -m http.server 8099\nnpx vibeward@latest http://localhost:8099/ --yes --lang es",
        "foot": "Generado por vibeward. Detecta y reporta; nunca arregla.",
    },
}


def build(lang, md_path, css):
    t = T[lang]
    body = convert(open(md_path, encoding="utf-8").read())
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    files = ""
    for name, src in (("index.html", DEMO_INDEX), ("assets/app.js", DEMO_JS % PLACEHOLDER)):
        files += f'<p class="fname">{name}</p><pre>{esc(src)}</pre>'
    notes = "".join(f"<p>{n}</p>" for n in t["notes"])
    ld = (
        '{"@context":"https://schema.org","@type":"TechArticle",'
        f'"headline":"{t["title"]}","description":"{t["desc"]}",'
        f'"inLanguage":"{lang}","url":"{t["canon"]}",'
        '"isPartOf":{"@type":"WebSite","name":"vibeward","url":"https://vibeward.ai"},'
        '"author":{"@type":"Person","name":"Jos\\u00e9 Siapo","url":"https://github.com/JSiapoDEV"},'
        '"about":{"@type":"SoftwareApplication","name":"vibeward",'
        '"applicationCategory":"DeveloperApplication","url":"https://vibeward.ai"}}'
    )
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{t['title']}</title>
<meta name="description" content="{t['desc']}">
<link rel="canonical" href="{t['canon']}">
<link rel="alternate" hreflang="en" href="https://vibeward.ai/sample-report/">
<link rel="alternate" hreflang="es" href="https://vibeward.ai/es/informe-de-ejemplo/">
<link rel="alternate" hreflang="x-default" href="https://vibeward.ai/sample-report/">
<meta property="og:type" content="article">
<meta property="og:title" content="{t['title']}">
<meta property="og:description" content="{t['desc']}">
<meta property="og:url" content="{t['canon']}">
<meta property="og:image" content="https://vibeward.ai/avatar-512.png">
<meta name="twitter:card" content="summary">
<script type="application/ld+json">{ld}</script>
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style>{css}{PAGE_CSS}</style>
</head>
<body>
<header class="top"><div class="wrap">
  <a class="brand" href="{t['home']}">vibe<span>ward</span></a>
  <nav class="navr">
    <a href="{t['home']}">← vibeward.ai</a>
    <a href="{t['alt']}">{t['altlabel']}</a>
  </nav>
</div></header>
<div class="wrap">
  <section class="intro">
    <span class="k">{t['k']}</span>
    <h1 class="page">{t['h1']}</h1>
    <p class="lead">{t['lead']}</p>
    <div class="note"><h3>{t['noteh']}</h3>{notes}</div>
  </section>
  <article class="report">{body}</article>
  <section class="repro">
    <h2>{t['reproh']}</h2>
    <p>{t['reprop']}</p>
    <pre>{esc(t['cmd'])}</pre>
    {files}
  </section>
  <footer class="btm"><div>{t['foot']} · <a href="https://github.com/JSiapoDEV/vibeward">GitHub</a></div></footer>
</div>
</body>
</html>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--emit-demo", metavar="DIR", help="write the deliberately broken demo app")
    ap.add_argument("--build", nargs=2, metavar=("EN.md", "ES.md"), help="render both report pages")
    args = ap.parse_args()

    if args.emit_demo:
        emit_demo(args.emit_demo)
        return
    if args.build:
        css = base_css()
        for lang, md in zip(("en", "es"), args.build):
            out = os.path.join(ROOT, T[lang]["out"])
            os.makedirs(os.path.dirname(out), exist_ok=True)
            page = build(lang, md, css)
            open(out, "w", encoding="utf-8").write(page)
            assert page.count("<h1") == 1, "a page must own exactly one <h1>"
            print(f"wrote {T[lang]['out']}")
        return
    ap.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
