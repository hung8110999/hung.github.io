"""
convert.py — Markdown → HTML Blog Post Converter

Scans markdown_posts/ for subfolders containing blog.md,
converts them to HTML post pages, and generates posts.json.

Usage: python scripts/convert.py
"""

import os
import re
import json
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MARKDOWN_DIR = os.path.join(ROOT, 'markdown_posts')
POSTS_DIR = os.path.join(ROOT, 'posts')
POSTS_JSON = os.path.join(ROOT, 'posts.json')

os.makedirs(POSTS_DIR, exist_ok=True)


# ──────────────────────────────────────────────
# Markdown → HTML Converter
# ──────────────────────────────────────────────

def convert_markdown(md, folder_name):
    html = md

    # ── Headings ──
    html = re.sub(r'^### (.+)$', r'<h3 class="blog-post-h3">\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2 class="blog-post-h2">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1 class="blog-post-h1">\1</h1>', html, flags=re.MULTILINE)

    # ── Horizontal rules ──
    html = re.sub(r'^---+$', r'<hr class="blog-post-hr">', html, flags=re.MULTILINE)

    # ── Bold + Italic combined ──
    html = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', html)

    # ── Bold ──
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)

    # ── Italic (single *) ──
    html = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', html)

    # ── Strikethrough ──
    html = re.sub(r'~~(.*?)~~', r'<del>\1</del>', html)

    # ── Inline code ──
    html = re.sub(r'`([^`]+)`', r'<code class="blog-post-code">\1</code>', html)

    # ── Images ![alt](path){optional style} — MUST come before links ──
    def img_repl(m):
        alt, img_path, style = m.group(1), m.group(2), m.group(3)
        normalized = img_path.replace('\\', '/')
        final_path = f"../markdown_posts/{folder_name}/{normalized}"
        inline_style = f' style="{style}"' if style else ''
        return (
            f'<figure class="blog-post-figure">\n'
            f'  <img src="{final_path}" alt="{alt}" class="blog-post-img"{inline_style}>\n'
            f'</figure>'
        )

    html = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)(?:\{([^}]*)\})?', img_repl, html)

    # ── Links [text](url) — after images ──
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', html)

    # ── Unordered lists ──
    lines = html.split('\n')
    processed = []
    in_list = False

    for line in lines:
        trimmed = line.strip()
        list_match = re.match(r'^- (.+)$', trimmed)

        if list_match:
            if not in_list:
                processed.append('<ul class="blog-post-list">')
                in_list = True
            processed.append(f'  <li>{list_match.group(1)}</li>')
        else:
            if in_list:
                processed.append('</ul>')
                in_list = False
            processed.append(line)

    if in_list:
        processed.append('</ul>')

    html = '\n'.join(processed)

    # ── Image captions: lines starting with * or <em> after a figure (allows blank lines) ──
    html = re.sub(
        r'</figure>\s*(?:\*|<em>)\s*([^\n]+)',
        lambda m: f'<figcaption class="blog-post-caption">{m.group(1).replace("</em>", "").strip("* ").strip()}</figcaption>\n</figure>',
        html
    )

    # ── Paragraphs: wrap plain text lines ──
    final_lines = html.split('\n')
    output = []

    for line in final_lines:
        t = line.strip()
        if (
            t == '' or
            t.startswith('<') or
            t.startswith('<!--') or
            t == '</ul>' or
            t == '</figure>'
        ):
            output.append(line)
        else:
            output.append(f'<p class="blog-post-p">{t}</p>')

    return '\n'.join(output)


# ──────────────────────────────────────────────
# Extract Metadata from HTML Comment Frontmatter
# ──────────────────────────────────────────────

def _parse_simple_kv(block: str):
    """
    Parse a loose 'key: value' block (one pair per line).
    Keeps values as raw strings; ignores empty lines.
    """
    data = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or ':' not in line:
            continue
        k, v = line.split(':', 1)
        k = k.strip().lower()
        v = v.strip()
        if k:
            data[k] = v
    return data


def _extract_yaml_frontmatter(md: str):
    """
    Extract YAML-like frontmatter from the top of the file:
    ---
    key: value
    ---
    Returns (data_dict, start_idx, end_idx) where indices refer to md slice to remove,
    or ({}, None, None) if not present.
    """
    if not md.startswith('---'):
        return {}, None, None
    m = re.match(r'^---\s*\n([\s\S]*?)\n---\s*(?:\n|$)', md)
    if not m:
        return {}, None, None
    data = _parse_simple_kv(m.group(1))
    return data, m.start(), m.end()


def _parse_date_flexible(date_str: str):
    date_str = (date_str or '').strip()
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    return None


def extract_metadata(md):
    meta = {'date': '2026-01-01', 'description': '', 'title': 'Untitled', 'subtitle': ''}

    # 1) YAML frontmatter at file start (preferred if present)
    yaml_data, _, _ = _extract_yaml_frontmatter(md)
    if yaml_data:
        if 'date' in yaml_data:
            meta['date'] = yaml_data.get('date', '').strip()
        if 'description' in yaml_data:
            meta['description'] = yaml_data.get('description', '').strip()
        if 'subtitle' in yaml_data:
            meta['subtitle'] = yaml_data.get('subtitle', '').strip()

    # 2) HTML comment frontmatter anywhere in file
    comment_match = re.search(r'<!--([\s\S]*?)-->', md)
    if comment_match:
        block = comment_match.group(1)
        data = _parse_simple_kv(block)
        if 'date' in data:
            meta['date'] = data.get('date', '').strip()
        if 'description' in data:
            meta['description'] = data.get('description', '').strip()
        if 'subtitle' in data:
            meta['subtitle'] = data.get('subtitle', '').strip()

    title_match = re.search(r'^# (.+)$', md, re.MULTILINE)
    if title_match:
        meta['title'] = title_match.group(1).strip()

    return meta


# ──────────────────────────────────────────────
# HTML Template for a Blog Post Page
# ──────────────────────────────────────────────

def build_post_html(meta, body_html):
    d = _parse_date_flexible(meta.get('date', ''))
    formatted_date = d.strftime('%B %d, %Y') if d else (meta.get('date') or '')
    subtitle_html = f'<div class="blog-post-subtitle">{meta["subtitle"]}</div>' if meta.get('subtitle') else ''

    return f"""<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{meta['title']} — Hung's Blog</title>
    <meta name="description" content="{meta['description']}">
    <meta name="date" content="{meta['date']}">
    <link rel="stylesheet" href="../css/style.css">
    <link rel="icon"
        href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🚀</text></svg>">
</head>

<body>
    <!-- Navigation -->
    <nav class="navbar" id="navbar">
        <div class="nav-container">
            <a href="../index.html" class="nav-logo"><span class="logo-icon">H</span> Hung</a>
            <ul class="nav-links" id="navLinks">
                <li><a href="../index.html">Profile</a></li>
                <li><a href="../road.html">My Road</a></li>
                <li class="nav-dropdown">
                    <a href="#">Study ▾</a>
                    <div class="dropdown-menu">
                        <a href="../math.html">Math</a>
                        <a href="../english.html">English</a>
                        <a href="../coding.html">Coding</a>
                    </div>
                </li>
                <li><a href="../blog.html" class="active">Blog</a></li>
            </ul>
            <button class="nav-toggle" id="navToggle" aria-label="Toggle menu">
                <span></span><span></span><span></span>
            </button>
        </div>
    </nav>

    <main class="main-content">
        <article class="blog-post">
            <header class="blog-post-header">
                <div class="blog-post-date">{formatted_date}</div>
                <h1 class="blog-post-title">{meta['title']}</h1>
                {subtitle_html}
            </header>

            <div class="blog-post-body">
                {body_html}
            </div>

            <div class="blog-post-footer">
                <a href="../blog.html" class="btn btn-secondary">← Back to Blog</a>
            </div>
        </article>
    </main>

    <footer class="footer">
        <p>© 2026 Nguyen Gia Hung — Built with 💙 for self-study. Hosted on <a href="https://pages.github.com"
                target="_blank">GitHub Pages</a>.</p>
    </footer>
    <script src="../js/main.js"></script>
</body>

</html>
"""


# ──────────────────────────────────────────────
# Main: Scan, Convert, Write
# ──────────────────────────────────────────────

def main():
    posts_index = []

    folders = sorted([
        f for f in os.listdir(MARKDOWN_DIR)
        if os.path.isdir(os.path.join(MARKDOWN_DIR, f))
    ])

    for folder in folders:
        folder_path = os.path.join(MARKDOWN_DIR, folder)
        md_files = [f for f in os.listdir(folder_path) if f.endswith('.md')]
        if not md_files:
            print(f"[SKIP] Skipping '{folder}' -- no .md file found.")
            continue
        md_file = os.path.join(folder_path, md_files[0])

        with open(md_file, 'r', encoding='utf-8') as f:
            raw = f.read()

        meta = extract_metadata(raw)

        # Remove metadata comment and first H1 from body
        # Strip YAML frontmatter at top (if present)
        _, fm_start, fm_end = _extract_yaml_frontmatter(raw)
        body_src = raw[fm_end:] if fm_end is not None else raw

        # Strip first HTML comment block (if used for metadata)
        body = re.sub(r'<!--[\s\S]*?-->', '', body_src, count=1).strip()
        body = re.sub(r'^# .+$', '', body, count=1, flags=re.MULTILINE).strip()

        body_html = convert_markdown(body, folder)
        post_html = build_post_html(meta, body_html)

        out_file = os.path.join(POSTS_DIR, f'{folder}.html')
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(post_html)
        print(f"[OK] Generated: posts/{folder}.html")

        posts_index.append({
            'title': meta['title'],
            'date': meta['date'],
            'description': meta['description'],
            'subtitle': meta.get('subtitle', ''),
            'url': f'posts/{folder}.html',
        })

    # Sort newest first
    posts_index.sort(key=lambda p: p['date'], reverse=True)

    with open(POSTS_JSON, 'w', encoding='utf-8') as f:
        json.dump(posts_index, f, indent=2, ensure_ascii=False)
    print(f"[OK] Generated: posts.json with {len(posts_index)} post(s).")


if __name__ == '__main__':
    main()
