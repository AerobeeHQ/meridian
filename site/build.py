"""
Codex brochure site — staticjinja build script.

Usage:
    uv run build.py           # Build once → output/
    uv run build.py --watch   # Build + watch for changes (local dev)
"""

import sys
import shutil
from pathlib import Path
from staticjinja import Site

USE_RELOADER = "--watch" in sys.argv

# Ensure output directory exists
out = Path("output")
out.mkdir(exist_ok=True)

# Copy static assets
src_static = Path("static")
dst_static = out / "static"
if dst_static.exists():
    shutil.rmtree(dst_static)
shutil.copytree(src_static, dst_static)
print(f"Copied static/ → output/static/")

# Render templates
site = Site.make_site(
    searchpath="templates",
    outpath="output",
)
site.render(use_reloader=USE_RELOADER)
