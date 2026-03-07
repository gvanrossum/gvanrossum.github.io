#!/usr/bin/env python3

"""publish.py -- Publish a Markdown blog post to the site.

Usage:
    python publish.py <folder>/<post>.md

Examples:
    python publish.py opinions/my-first-post.md
    python publish.py interviews/john-doe.md

What it does (idempotently):

  1. Adds YAML front matter to the .md file if missing.
     - Title is extracted from the first '# Heading' line (which is then
       removed from the body so the layout can render it as <h1>),
       or derived from the filename.
     - Date defaults to today (override by adding 'date: YYYY-MM-DD'
       in front matter before running).
     - Layout is set to 'post'.

  2. If the folder has no index.html:
     - Creates one (styled like the existing blog indexes).
     - Adds the new blog to the top-level index.html (at the
       <!-- BLOG_LIST --> marker).

  3. If the folder already has index.html:
     - Adds the post at the top of the list (if not already present).

  4. Refreshes <folder>/feed.xml (RSS 2.0) from all .md posts in the folder,
      and ensures the folder's index.html links to the feed.
"""

import html as html_module
import re
import sys
from datetime import date, datetime
from email.utils import format_datetime
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent
SITE_URL = "https://gvanrossum.github.io"

# Markers used to locate insertion points in HTML files
BLOG_LIST_MARKER = "<!-- BLOG_LIST -->"
POSTS_START_MARKER = "<!-- POSTS_START -->"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def slugify_to_title(name: str) -> str:
    """Convert a folder name like 'my-opinions' to 'My Opinions'."""
    return name.replace("-", " ").replace("_", " ").title()


def parse_front_matter(text: str) -> tuple[dict, str]:
    """Parse YAML front matter from text.

    Returns (metadata_dict, body_after_front_matter).
    If there is no front matter, metadata_dict is empty and body is
    the full text.
    """
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm_text = text[3:end].strip()
            body = text[end + 4 :]  # skip past \n---
            # Strip at most one leading newline
            if body.startswith("\n"):
                body = body[1:]
            meta: dict[str, str] = {}
            for line in fm_text.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    val = val.strip().strip('"').strip("'")
                    meta[key.strip()] = val
            return meta, body
    return {}, text


def format_front_matter(meta: dict[str, str]) -> str:
    """Format metadata as a YAML front matter block."""
    lines = ["---"]
    # Ensure a stable key order
    key_order = ["layout", "title", "date"]
    keys = [k for k in key_order if k in meta] + sorted(
        k for k in meta if k not in key_order
    )
    for key in keys:
        val = meta[key]
        # Quote values that contain colons or special chars
        if any(c in val for c in ":\"'{}&*!@#%"):
            val_escaped = val.replace('"', '\\"')
            lines.append(f'{key}: "{val_escaped}"')
        else:
            lines.append(f"{key}: {val}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def extract_title_from_md(body: str) -> tuple[str | None, str]:
    """Extract title from the first '# Heading' line.

    Returns (title_or_None, body_with_heading_removed).
    If no heading is found, returns (None, original_body).
    """
    lines = body.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            # Remove the heading line (and a following blank line, if any)
            remaining = lines[:i] + lines[i + 1 :]
            if remaining and remaining[0].strip() == "" and i == 0:
                remaining = remaining[1:]
            return title, "\n".join(remaining)
        # Stop looking after a non-blank, non-heading line
        if stripped and not stripped.startswith("#"):
            break
    return None, body


def title_from_filename(filename: str) -> str:
    """Derive a title from a filename like 'my-great-post.md'."""
    return Path(filename).stem.replace("-", " ").replace("_", " ").title()


def format_date_display(date_str: str) -> str:
    """Format '2026-02-28' as 'February 28, 2026'."""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return d.strftime("%B %d, %Y")


def parse_publish_datetime(date_str: str) -> datetime:
    """Parse front-matter date/datetime and return an aware local datetime."""
    normalized = date_str.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        dt = datetime.strptime(normalized, "%Y-%m-%d")

    return dt.astimezone()


def format_rss_pub_date(date_str: str) -> str:
    """Format front-matter date/datetime as RFC-2822 in local timezone."""
    return format_datetime(parse_publish_datetime(date_str))


def absolute_url(relative_path: str) -> str:
    """Build an absolute URL under the site root."""
    return f"{SITE_URL.rstrip('/')}/{relative_path.lstrip('/')}"


def collect_blog_posts(blog_dir: Path) -> list[dict[str, str]]:
    """Collect post metadata from all Markdown files in a blog directory."""
    posts: list[dict[str, str]] = []

    for md_path in blog_dir.glob("*.md"):
        text = md_path.read_text()
        meta, _ = parse_front_matter(text)

        title = meta.get("title") or title_from_filename(md_path.name)
        date_str = meta.get("date") or date.today().isoformat()
        html_filename = md_path.stem + ".html"

        posts.append(
            {
                "title": title,
                "date": date_str,
                "html_filename": html_filename,
                "md_filename": md_path.name,
            }
        )

    posts.sort(
        key=lambda p: (parse_publish_datetime(p["date"]), p["html_filename"]),
        reverse=True,
    )
    return posts


def update_post_nav_links(blog_dir: Path) -> None:
    """Update newer/older front-matter links for all posts in a blog dir."""
    posts = collect_blog_posts(blog_dir)
    # posts is sorted newest-first
    for i, post in enumerate(posts):
        newer = posts[i - 1]["html_filename"] if i > 0 else ""
        older = posts[i + 1]["html_filename"] if i < len(posts) - 1 else ""

        md_path = blog_dir / post["md_filename"]
        text = md_path.read_text()
        meta, body = parse_front_matter(text)

        changed = False
        if meta.get("newer", "") != newer:
            if newer:
                meta["newer"] = newer
            elif "newer" in meta:
                del meta["newer"]
            changed = True
        if meta.get("older", "") != older:
            if older:
                meta["older"] = older
            elif "older" in meta:
                del meta["older"]
            changed = True

        if changed:
            md_path.write_text(format_front_matter(meta) + "\n" + body)
            print(f"  Updated nav links in {post['md_filename']}")


def detect_blog_title(blog_dir: Path, fallback_title: str) -> str:
    """Read blog title from index.html (<h1> or <title>), with fallback."""
    index_path = blog_dir / "index.html"
    if not index_path.exists():
        return fallback_title

    index_html = index_path.read_text()

    h1_match = re.search(
        r"<h1>(.*?)</h1>", index_html, flags=re.IGNORECASE | re.DOTALL
    )
    if h1_match:
        return html_module.unescape(h1_match.group(1).strip())

    title_match = re.search(
        r"<title>(.*?)</title>", index_html, flags=re.IGNORECASE | re.DOTALL
    )
    if title_match:
        return html_module.unescape(title_match.group(1).strip())

    return fallback_title


def write_blog_rss_feed(blog_dir: Path, blog_title: str) -> None:
    """Generate or refresh RSS feed.xml for a blog directory."""
    posts = collect_blog_posts(blog_dir)

    blog_rel = f"{blog_dir.name}/index.html"
    blog_link = absolute_url(blog_rel)
    feed_link = absolute_url(f"{blog_dir.name}/feed.xml")

    if posts:
        last_build = format_rss_pub_date(posts[0]["date"])
    else:
        last_build = format_datetime(datetime.now().astimezone())

    item_blocks: list[str] = []
    for post in posts:
        title = html_module.escape(post["title"])
        post_rel = f"{blog_dir.name}/{post['html_filename']}"
        post_url = html_module.escape(absolute_url(post_rel))
        pub_date = format_rss_pub_date(post["date"])
        item_blocks.append(
            "    <item>\n"
            f"      <title>{title}</title>\n"
            f"      <link>{post_url}</link>\n"
            f"      <guid>{post_url}</guid>\n"
            f"      <pubDate>{pub_date}</pubDate>\n"
            "    </item>"
        )

    channel_title = html_module.escape(f"Guido van Rossum: {blog_title}")
    channel_description = html_module.escape(
        f"Posts from Guido van Rossum: {blog_title}"
    )
    rss = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<rss version=\"2.0\" xmlns:atom=\"http://www.w3.org/2005/Atom\">\n"
        "  <channel>\n"
        f"    <title>{channel_title}</title>\n"
        f"    <link>{html_module.escape(blog_link)}</link>\n"
        f"    <description>{channel_description}</description>\n"
        f"    <atom:link href=\"{html_module.escape(feed_link)}\" "
        "rel=\"self\" type=\"application/rss+xml\" />\n"
        f"    <lastBuildDate>{last_build}</lastBuildDate>\n"
        + ("\n".join(item_blocks) + "\n" if item_blocks else "")
        + "  </channel>\n"
        "</rss>\n"
    )

    (blog_dir / "feed.xml").write_text(rss)
    print(f"  Wrote {blog_dir.name}/feed.xml ({len(posts)} post(s))")


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------


def ensure_front_matter(md_path: Path) -> dict[str, str]:
    """Ensure the .md file has YAML front matter.  Returns metadata."""
    text = md_path.read_text()
    meta, body = parse_front_matter(text)

    changed = False

    if "layout" not in meta:
        meta["layout"] = "post"
        changed = True

    if "title" not in meta:
        title, new_body = extract_title_from_md(body)
        if title:
            meta["title"] = title
            body = new_body
            changed = True
        else:
            meta["title"] = title_from_filename(md_path.name)
            changed = True

    if "date" not in meta:
        meta["date"] = date.today().isoformat()
        changed = True

    if changed:
        new_text = format_front_matter(meta) + "\n" + body
        md_path.write_text(new_text)
        print(f"  Updated front matter in {md_path.name}")
    else:
        print(f"  Front matter already OK in {md_path.name}")

    return meta


def create_blog_index(blog_dir: Path, blog_title: str) -> None:
    """Create a new index.html for a blog folder."""
    escaped = html_module.escape(blog_title)
    index_html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escaped}</title>
<link rel="stylesheet" href="../style.css">
</head>
<body>
<div class="container">

<p><a href="../index.html">&larr; Back to the home page</a></p>

<h1>{escaped}</h1>

<hr>

<h3>Posts</h3>

<p><a href="feed.xml">RSS feed</a></p>

<ul>
{POSTS_START_MARKER}
</ul>

<hr>
<p><a href="../index.html">&larr; Back to the home page</a></p>

</div>
</body>
</html>
"""
    (blog_dir / "index.html").write_text(index_html)
    print(f"  Created {blog_dir.name}/index.html")


def add_post_to_blog_index(
    blog_dir: Path, md_filename: str, title: str, date_str: str
) -> None:
    """Add a post entry to the blog folder's index.html."""
    index_path = blog_dir / "index.html"
    index_html = index_path.read_text()

    # GitHub Pages converts .md to .html
    html_filename = Path(md_filename).stem + ".html"

    # Idempotent: skip if already listed
    if html_filename in index_html:
        print(f"  Post already in index: {html_filename}")
        return

    escaped_title = html_module.escape(title)
    date_display = format_date_display(date_str)
    new_entry = (
        f'<li><b><a href="{html_filename}">{escaped_title}</a></b>'
        f' <span style="color: #666;">&mdash; {date_display}</span></li>'
    )

    if POSTS_START_MARKER in index_html:
        index_html = index_html.replace(
            POSTS_START_MARKER,
            POSTS_START_MARKER + "\n" + new_entry,
        )
    else:
        # Fallback for hand-edited index files: insert after first <ul>
        index_html = index_html.replace("<ul>\n", "<ul>\n" + new_entry + "\n", 1)

    index_path.write_text(index_html)
    print(f"  Added {html_filename} to {blog_dir.name}/index.html")


def ensure_blog_index_has_feed_link(blog_dir: Path) -> None:
    """Ensure a blog index has a link to feed.xml."""
    index_path = blog_dir / "index.html"
    index_html = index_path.read_text()

    if "feed.xml" in index_html:
        return

    marker = "<h3>Posts</h3>"
    feed_paragraph = '\n\n<p><a href="feed.xml">RSS feed</a></p>'

    if marker in index_html:
        index_html = index_html.replace(marker, marker + feed_paragraph, 1)
    else:
        index_html = feed_paragraph.strip() + "\n" + index_html

    index_path.write_text(index_html)
    print(f"  Added RSS link to {blog_dir.name}/index.html")


def register_blog_in_top_index(blog_folder: str, blog_title: str) -> None:
    """Add the blog to the top-level index.html blog list."""
    index_path = SITE_ROOT / "index.html"
    index_html = index_path.read_text()

    # Idempotent
    if f"{blog_folder}/index.html" in index_html:
        print(f"  Blog '{blog_folder}' already in top-level index")
        return

    escaped = html_module.escape(blog_title)
    new_entry = (
        f'<li><a href="{blog_folder}/index.html">{escaped}</a>'
        f' (<a href="{blog_folder}/feed.xml">RSS</a>)</li>'
    )

    if BLOG_LIST_MARKER in index_html:
        index_html = index_html.replace(
            BLOG_LIST_MARKER,
            BLOG_LIST_MARKER + "\n" + new_entry,
        )
        index_path.write_text(index_html)
        print(f"  Registered blog '{blog_folder}' in top-level index")
    else:
        print(
            f"  WARNING: Marker {BLOG_LIST_MARKER!r} not found in index.html.\n"
            f"  Please add the blog entry manually."
        )


def ensure_top_index_has_feed_link(blog_folder: str) -> None:
    """Ensure top-level index entry for a blog includes a feed link."""
    index_path = SITE_ROOT / "index.html"
    index_html = index_path.read_text()

    feed_href = f'{blog_folder}/feed.xml'
    if feed_href in index_html:
        return

    blog_href = f'{blog_folder}/index.html'
    pattern = re.compile(
        rf'(<li>\s*<a href="{re.escape(blog_href)}"[^>]*>.*?</a>)(.*?</li>)',
        flags=re.IGNORECASE,
    )
    match = pattern.search(index_html)
    if not match:
        return

    replacement = (
        match.group(1)
        + f' (<a href="{blog_folder}/feed.xml">RSS</a>)'
        + match.group(2)
    )
    index_html = index_html[: match.start()] + replacement + index_html[match.end() :]
    index_path.write_text(index_html)
    print(f"  Added top-level RSS link for '{blog_folder}'")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    md_rel = sys.argv[1]
    md_path = (SITE_ROOT / md_rel).resolve()

    if not md_path.exists():
        print(f"Error: {md_path} not found")
        sys.exit(1)

    if md_path.suffix != ".md":
        print(f"Error: {md_rel} is not a .md file")
        sys.exit(1)

    blog_dir = md_path.parent
    blog_folder = blog_dir.name

    # Sanity check: must be a direct subfolder of the site root
    if blog_dir.parent.resolve() != SITE_ROOT:
        print(f"Error: {md_rel} must be in a direct subfolder of the site root")
        sys.exit(1)

    print(f"Publishing {md_rel} ...")

    # 1. Front matter
    meta = ensure_front_matter(md_path)
    title = meta["title"]
    date_str = meta["date"]

    # 2. Blog index
    is_new_blog = not (blog_dir / "index.html").exists()
    if is_new_blog:
        blog_title = slugify_to_title(blog_folder)
        create_blog_index(blog_dir, blog_title)
        register_blog_in_top_index(blog_folder, blog_title)

    # 3. Post entry in blog index
    add_post_to_blog_index(blog_dir, md_path.name, title, date_str)

    # 4. Ensure RSS link and refresh feed
    ensure_blog_index_has_feed_link(blog_dir)
    ensure_top_index_has_feed_link(blog_folder)
    blog_title = detect_blog_title(blog_dir, slugify_to_title(blog_folder))
    write_blog_rss_feed(blog_dir, blog_title)

    # 5. Update Newer/Older navigation links across all posts
    update_post_nav_links(blog_dir)

    print("Done!")


if __name__ == "__main__":
    main()
