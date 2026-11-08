# vibeward-web

Landing site for [vibeward](https://github.com/JSiapoDEV/vibeward) — served at **vibeward.ai**.

Plain static HTML (no build step), served by a Cloudflare Worker with static assets.
Deployed by Cloudflare Workers Builds on every push to `main`. Includes `llms.txt` and
`llms-full.txt` so AI tools can discover and summarize the project.

## Files

```
public/             everything that gets served
  index.html        the landing page (self-contained, inline CSS)
  es/index.html     Spanish version
  404.html          served with status 404 for unknown paths
  llms.txt          concise project summary for LLMs (llmstxt.org)
  llms-full.txt     full reference for LLMs
  robots.txt, sitemap.xml, favicon.svg, avatar*, fonts/
wrangler.jsonc      Worker config (assets directory + 404 handling)
```

## Hosting

- Worker `vibeward-web`, custom domains `vibeward.ai` and `www.vibeward.ai`.
- DNS and security headers (CSP, HSTS, X-Frame-Options, ...) live in the Cloudflare zone
  (Transform Rule `security-headers`), not in this repo.
- Moved off GitHub Pages in Nov 2026: Pages could not renew its origin certificate behind
  the Cloudflare proxy.

## Local preview

```bash
python3 -m http.server 8000 -d public   # then open http://localhost:8000
```
