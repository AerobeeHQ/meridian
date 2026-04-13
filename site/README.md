# Codex Brochure Site

Single-page product brochure for Codex, built with [staticjinja](https://staticjinja.readthedocs.io/).

## Structure

```
site/
├── templates/        # Jinja2 templates (source)
│   └── index.html
├── static/           # Static assets (copied as-is to output)
│   ├── css/style.css
│   └── js/main.js
├── output/           # Compiled output — deploy this to Cloudflare Pages
├── build.py          # Build script
└── pyproject.toml    # Python dependencies
```

`output/` is git-ignored. Run the build locally and deploy the compiled files.

---

## Running locally

### 1. Install dependencies

```bash
cd site
uv sync
```

### 2. Build once

```bash
uv run build_site.py
```

The compiled site is written to `site/output/`.

### 3. Preview with auto-reload (development)

```bash
uv run build_site.py --watch
```

Then open `site/output/index.html` in your browser, or serve it locally:

```bash
cd output && python3 -m http.server 8080
# → http://localhost:8080
```

---

## Deploying to Cloudflare Pages

Cloudflare Pages hosts the compiled `output/` directory. There is no build step on Cloudflare — build locally and publish manually.

### Option A — Wrangler CLI (recommended)

```bash
# Install Wrangler (once)
npm install -g wrangler

# Authenticate (once)
wrangler login

# Build the site
cd site
uv run build_site.py

# Deploy
wrangler pages deploy output/ --project-name codex-site
```

On first deploy Wrangler will create the project. Subsequent deploys update it.

### Option B — Cloudflare Dashboard (drag and drop)

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com) → **Pages**
2. Create a new project → **Upload assets**
3. Drag the entire `site/output/` folder into the upload area
4. Click **Deploy**

For subsequent deploys, open the project → **Deployments** → **Upload**.

---

## Workflow summary

```bash
# 1. Edit templates or styles
# 2. Rebuild
cd site && uv run build_site.py

# 3. Preview
cd output && python3 -m http.server 8080

# 4. Deploy to Cloudflare
wrangler pages deploy output/ --project-name codex-site
```
