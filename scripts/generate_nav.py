#!/usr/bin/env python3
"""Generate MkDocs nav from docs/archived/*.md (퍼블리싱용)"""

from pathlib import Path
import yaml

ARCHIVED_DIR = Path("docs/archived")
MKDOCS_YML = Path("mkdocs.yml")


def extract_title(md_path):
    with open(md_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("# "):
                return line.strip()[2:].strip()
    return md_path.stem.replace("_", " ").title()


def main():
    if not ARCHIVED_DIR.exists():
        print("No archived dir")
        return

    papers = sorted(ARCHIVED_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not papers:
        print("No archived papers - website will show empty list")
        return

    nav_items = []
    for p in papers:
        title = extract_title(p)
        display = title[:80] + "..." if len(title) > 80 else title
        nav_items.append({display: f"archived/{p.name}"})

    with open(MKDOCS_YML, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config["nav"] = [
        {"Home": "index.md"},
        {"Papers": nav_items},
    ]

    with open(MKDOCS_YML, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"Nav updated: {len(nav_items)} archived papers")


if __name__ == "__main__":
    main()
