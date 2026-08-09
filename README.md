# vibeward-web

Landing site for [vibeward](https://github.com/JSiapoDEV/vibeward) — served at **vibeward.ai**.

Plain static HTML (no build step). Deployed to GitHub Pages by `.github/workflows/deploy.yml`
on every push to `main`. Includes `llms.txt` and `llms-full.txt` so AI tools can discover and
summarize the project.

## Files

```
index.html        the landing page (self-contained, inline CSS)
llms.txt          concise project summary for LLMs (llmstxt.org)
llms-full.txt     full reference for LLMs
robots.txt        allow all crawlers
CNAME             custom domain (vibeward.ai)
.nojekyll         disable Jekyll on GitHub Pages
.github/workflows/deploy.yml   GitHub Pages deploy
```

## One-time setup

1. Create the repo under the org: `github.com/JSiapoDEV/vibeward-web`, push this folder.
2. Repo → **Settings → Pages → Source: GitHub Actions**.
3. **DNS at Namecheap** (Advanced DNS for vibeward.ai):
   - `A` `@` → `185.199.108.153`
   - `A` `@` → `185.199.109.153`
   - `A` `@` → `185.199.110.153`
   - `A` `@` → `185.199.111.153`
   - `CNAME` `www` → `jsiapodev.github.io.`
4. Settings → Pages → Custom domain: `vibeward.ai`, then enable **Enforce HTTPS** (after the
   cert provisions, a few minutes to an hour).

## Local preview

```bash
python3 -m http.server 8000   # then open http://localhost:8000
```
