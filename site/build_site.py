"""
Codex brochure site — staticjinja build script.

Usage:
    uv run build_site.py           # Build once → output/
    uv run build_site.py --watch   # Build + watch for changes (local dev)
"""

import os
import sys
import time
import shutil
from pathlib import Path
from staticjinja import Site

# Anchor all paths relative to this file so the script works when invoked
# from any directory (e.g. `uv run build_site.py` from the repo root).
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

USE_RELOADER = "--watch" in sys.argv


def copy_static_assets(source: Path, destination: Path) -> None:
    """Copy static assets into the output directory."""
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    print("Copied static/ → output/static/")


def get_tree_state(root: Path) -> tuple[tuple[str, bool, int, int], ...]:
    """Return a lightweight snapshot of a directory tree for change detection."""
    if not root.exists():
        return tuple()

    entries = []
    for item in sorted(root.rglob("*")):
        try:
            stat = item.stat()
        except FileNotFoundError:
            # The file may have been deleted between discovery and stat.
            continue

        entries.append(
            (
                str(item.relative_to(root)),
                item.is_dir(),
                stat.st_mtime_ns,
                stat.st_size,
            )
        )

    return tuple(entries)


# Ensure output directory exists
out = Path("output")
out.mkdir(exist_ok=True)

src_static = Path("static")
dst_static = out / "static"
templates_dir = Path("templates")

site = Site.make_site(
    searchpath="templates",
    outpath="output",
)

if not USE_RELOADER:
    copy_static_assets(src_static, dst_static)
    site.render()
else:
    copy_static_assets(src_static, dst_static)
    site.render()

    template_state = get_tree_state(templates_dir)
    static_state = get_tree_state(src_static)

    print("Watching templates/ and static/ for changes. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)

            new_template_state = get_tree_state(templates_dir)
            new_static_state = get_tree_state(src_static)

            templates_changed = new_template_state != template_state
            static_changed = new_static_state != static_state

            if static_changed:
                copy_static_assets(src_static, dst_static)
                static_state = new_static_state

            if templates_changed:
                site.render()
                template_state = new_template_state
    except KeyboardInterrupt:
        print("\nStopped watching for changes.")
