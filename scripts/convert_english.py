"""
convert_english.py — Markdown → HTML English Post Converter

Scans english/markdown_posts_english/ for subfolders containing blog.md,
converts them to HTML post pages, and generates english/english_posts.json.

Usage: python scripts/convert_english.py

YAML: `tag: Topic` or `tags: Reading, Writing` (comma-separated or [bracket, list]).

Side notes (pastel box in the outer margin, out of the text column): use a fenced block.
The visible title always starts with **Note** (bold red in CSS). Optional words after
`::: notes` become a suffix, e.g. `::: notes Terminology` → "Note — Terminology".

    ::: notes Optional suffix only
    - Bullet **with** formatting
    ![Alt text](image/file.png){width=100%}
    *Image caption on the next line*
    :::

Closing line must be exactly `:::` (optionally trailing spaces). Nested `::: notes` inside a note is supported.
"""

import json
import os
import re
import html as html_lib
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENGLISH_ROOT = os.path.join(ROOT, 'english')
MARKDOWN_DIR = os.path.join(ENGLISH_ROOT, 'markdown_posts_english')
POSTS_DIR = os.path.join(ENGLISH_ROOT, 'english_posts')
POSTS_JSON = os.path.join(ENGLISH_ROOT, 'english_posts.json')

os.makedirs(POSTS_DIR, exist_ok=True)


def convert_markdown(md, folder_name):
    html = md
    block_store = {}
    block_index = 0
    notes_store = {}
    notes_block_index = 0

    def stash_block(content):
        nonlocal block_index
        token = f"@@BLOCK_{block_index}@@"
        block_store[token] = content
        block_index += 1
        return token

    def extract_notes(s):
        """Fenced side notes: ::: notes [optional title] ... markdown body ... :::"""
        nonlocal notes_block_index
        pattern = re.compile(
            r'^::: notes(?:[ \t]+([^\n]*))?[ \t]*\n([\s\S]*?)^:::[ \t]*$',
            re.MULTILINE,
        )
        result = s
        while True:
            m = pattern.search(result)
            if not m:
                return result
            title = (m.group(1) or '').strip()
            inner_md = m.group(2).rstrip('\n')
            token = f'@@NOTES_BLOCK_{notes_block_index}@@'
            notes_store[token] = (title, inner_md)
            notes_block_index += 1
            result = result[:m.start()] + '\n' + token + '\n' + result[m.end():]

    def fenced_block_repl(m):
        lang = (m.group(1) or '').strip().lower()
        code = (m.group(2) or '').rstrip()
        if lang == 'mermaid':
            return stash_block(f'<div class="mermaid">\n{code}\n</div>')
        escaped = html_lib.escape(code)
        class_attr = f' language-{lang}' if lang else ''
        return stash_block(
            f'<pre class="blog-post-pre"><code class="blog-post-code{class_attr}">{escaped}</code></pre>'
        )

    # Fenced code blocks (including mermaid) must be handled before inline backticks.
    html = re.sub(r'```([a-zA-Z0-9_-]*)\n([\s\S]*?)\n```', fenced_block_repl, html)

    # Side notes (markdown inside, including images); before math so $$ can appear in a note if needed
    html = extract_notes(html)

    # Math blocks: $$ ... $$ (stash to avoid paragraph/list post-processing)
    html = re.sub(
        r'^\$\$\s*\n([\s\S]*?)\n\$\$\s*$',
        lambda m: stash_block(f'<div class="blog-post-math-block">\\[{m.group(1).strip()}\\]</div>'),
        html,
        flags=re.MULTILINE
    )

    # Images BEFORE inline math: alt/caption text may contain \( ... \); if math ran first,
    # <span class="..."> would inject raw double quotes and break the alt attribute.
    def img_repl(m):
        alt, img_path, attrs = m.group(1), m.group(2), m.group(3)
        normalized = img_path.replace('\\', '/')
        final_path = f"../markdown_posts_english/{folder_name}/{normalized}"
        alt_escaped = html_lib.escape(alt, quote=True)
        inline_style = ''
        fig_class = 'blog-post-figure'
        position_map = {
            'left': 'fig-left',
            'right': 'fig-right',
            'inline': 'fig-inline',
            'behind': 'fig-behind',
            'front': 'fig-front',
        }
        if attrs:
            # Parse Pandoc-style attributes like width=50% into CSS: width: 50%
            css_parts = []
            for pair in re.findall(r'([\w-]+)\s*=\s*(\S+)', attrs):
                key, val = pair
                if key == 'position' and val in position_map:
                    fig_class += f' {position_map[val]}'
                else:
                    css_parts.append(f'{key}: {val}')
            if css_parts:
                inline_style = f' style="{"; ".join(css_parts)}"'
        return (
            f'<figure class="{fig_class}">\n'
            f'  <img src="{final_path}" alt="{alt_escaped}" class="blog-post-img"{inline_style}>\n'
            f'</figure>'
        )

    html = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)(?:\{([^}]*)\})?', img_repl, html)

    # Figures may contain alt="... \(...\) ..." after html.escape; inline math below would
    # still match \( inside attributes and inject <span>. Stash <figure>...</figure> first.
    figure_stash = {}
    fig_stash_i = [0]

    def stash_figure_block(m):
        tok = f"@@FIGSTASH_{fig_stash_i[0]}@@"
        figure_stash[tok] = m.group(0)
        fig_stash_i[0] += 1
        return tok

    html = re.sub(
        r'<figure class="blog-post-figure[^"]*">[\s\S]*?</figure>',
        stash_figure_block,
        html,
    )

    # Inline math: \( ... \)
    html = re.sub(
        r'\\\((.+?)\\\)',
        lambda m: f'<span class="blog-post-math">\\({m.group(1).strip()}\\)</span>',
        html
    )

    # Inline math: $ ... $ (avoid $$ blocks via lookarounds)
    html = re.sub(
        r'(?<!\$)\$([^\$\n]+)\$(?!\$)',
        lambda m: f'<span class="blog-post-math">\\({m.group(1).strip()}\\)</span>',
        html
    )

    for _tok, _fig in figure_stash.items():
        html = html.replace(_tok, _fig)

    html = re.sub(r'^### (.+)$', r'<h3 class="blog-post-h3">\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2 class="blog-post-h2">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1 class="blog-post-h1">\1</h1>', html, flags=re.MULTILINE)

    html = re.sub(r'^---+$', r'<hr class="blog-post-hr">', html, flags=re.MULTILINE)
    html = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', html)
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', html)
    html = re.sub(r'~~(.*?)~~', r'<del>\1</del>', html)
    html = re.sub(r'`([^`]+)`', r'<code class="blog-post-code">\1</code>', html)
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', html)

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

    html = re.sub(
        r'</figure>\s*(?:\*|<em>)\s*([^\n]+)',
        lambda m: f'<figcaption class="blog-post-caption">{m.group(1).replace("</em>", "").strip("* ").strip()}</figcaption>\n</figure>',
        html
    )

    final_lines = html.split('\n')
    output = []

    for line in final_lines:
        t = line.strip()
        if (
            t == '' or
            t.startswith('<') or
            t.startswith('<!--') or
            t == '</ul>' or
            t == '</figure>' or
            re.match(r'^@@BLOCK_\d+@@$', t) or
            re.match(r'^@@NOTES_BLOCK_\d+@@$', t)
        ):
            output.append(line)
        else:
            output.append(f'<p class="blog-post-p">{t}</p>')
    rendered = '\n'.join(output)
    for token, content in block_store.items():
        rendered = rendered.replace(token, content)
    for token, (title, inner_md) in notes_store.items():
        inner_html = convert_markdown(inner_md, folder_name)
        t = (title or '').strip()
        if not t or t.lower() in ('note', 'notes'):
            suffix_html = ''
            aria = 'Note'
        else:
            suffix_html = (
                f'<span class="blog-post-notes-title-suffix"> — {html_lib.escape(t)}</span>'
            )
            aria = f'Note — {t}'
        aside = (
            f'<aside class="blog-post-notes" aria-label="{html_lib.escape(aria)}">\n'
            f'<strong class="blog-post-notes-label"><span class="blog-post-notes-mark">Note</span>'
            f'{suffix_html}</strong>\n'
            f'{inner_html}\n'
            f'</aside>'
        )
        rendered = rendered.replace(token, aside)
    return rendered


def _parse_simple_kv(block: str):
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


def _parse_tags_value(val):
    if val is None:
        return []
    s = str(val).strip()
    if not s:
        return []
    if s.startswith('[') and s.endswith(']'):
        s = s[1:-1]
    return [p.strip() for p in re.split(r'\s*,\s*', s) if p.strip()]


def _tags_from_kv(data: dict):
    if not data:
        return []
    out = []
    if data.get('tags') is not None:
        out.extend(_parse_tags_value(data.get('tags')))
    if data.get('tag'):
        out.append(str(data['tag']).strip())
    return out


def _dedupe_tags(seq):
    seen = set()
    out = []
    for t in seq:
        t = (t or '').strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def extract_metadata(md):
    meta = {
        'date': '2026-01-01',
        'description': '',
        'title': 'Untitled',
        'subtitle': '',
        'tag': '',
        'tags': [],
    }

    collected = []
    yaml_data, _, _ = _extract_yaml_frontmatter(md)
    if yaml_data:
        if 'date' in yaml_data:
            meta['date'] = yaml_data.get('date', '').strip()
        if 'description' in yaml_data:
            meta['description'] = yaml_data.get('description', '').strip()
        if 'subtitle' in yaml_data:
            meta['subtitle'] = yaml_data.get('subtitle', '').strip()
        collected.extend(_tags_from_kv(yaml_data))

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
        collected.extend(_tags_from_kv(data))

    tags = _dedupe_tags(collected)
    meta['tags'] = tags
    meta['tag'] = tags[0] if tags else ''

    title_match = re.search(r'^# (.+)$', md, re.MULTILINE)
    if title_match:
        meta['title'] = title_match.group(1).strip()

    return meta


def build_post_html(meta, body_html):
    d = _parse_date_flexible(meta.get('date', ''))
    formatted_date = d.strftime('%B %d, %Y') if d else (meta.get('date') or '')
    subtitle_html = f'<div class="blog-post-subtitle">{meta["subtitle"]}</div>' if meta.get('subtitle') else ''

    return f"""<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{meta['title']} — Hung's English Notes</title>
    <meta name="description" content="{meta['description']}">
    <meta name="date" content="{meta['date']}">
    <link rel="stylesheet" href="../../css/style.css">
    <script>
        window.MathJax = {{
            tex: {{
                inlineMath: [['\\\\(', '\\\\)'], ['$', '$']],
                displayMath: [['\\\\[', '\\\\]'], ['$$', '$$']]
            }},
            svg: {{
                fontCache: 'global'
            }}
        }};
    </script>
    <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
        window.addEventListener('DOMContentLoaded', function () {{
            if (window.mermaid) {{
                mermaid.initialize({{ startOnLoad: true, securityLevel: 'loose' }});
            }}
        }});
    </script>
    <link rel="icon"
        href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🚀</text></svg>">
</head>

<body>
    <nav class="navbar" id="navbar">
        <div class="nav-container">
            <a href="../../index.html" class="nav-logo"><span class="logo-icon">H</span> Hung</a>
            <ul class="nav-links" id="navLinks">
                <li><a href="../../index.html">Profile</a></li>
                <li><a href="../../road.html">My Road</a></li>
                <li class="nav-dropdown">
                    <a href="#" class="active">Study ▾</a>
                    <div class="dropdown-menu">
                        <a href="../../math.html">Math</a>
                        <a href="../../english.html" class="active">English</a>
                        <a href="../../coding.html">Coding</a>
                    </div>
                </li>
                <li><a href="../../blog.html">Blog</a></li>
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
                <a href="../../english.html" class="btn btn-secondary">← Back to English Notes</a>
            </div>
        </article>
    </main>

    <footer class="footer">
        <p>© 2026 Nguyen Gia Hung — Built with 💙 for self-study. Hosted on <a href="https://pages.github.com"
                target="_blank">GitHub Pages</a>.</p>
    </footer>
    <script src="../../js/main.js"></script>
</body>

</html>
"""


def main():
    posts_index = []

    if not os.path.isdir(MARKDOWN_DIR):
        print(f"[SKIP] Directory '{MARKDOWN_DIR}' not found. Create it and add subfolders with blog.md")
        return

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

        _, _, fm_end = _extract_yaml_frontmatter(raw)
        body_src = raw[fm_end:] if fm_end is not None else raw
        body = re.sub(r'<!--[\s\S]*?-->', '', body_src, count=1).strip()
        body = re.sub(r'^# .+$', '', body, count=1, flags=re.MULTILINE).strip()

        body_html = convert_markdown(body, folder)
        post_html = build_post_html(meta, body_html)

        out_file = os.path.join(POSTS_DIR, f'{folder}.html')
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(post_html)
        print(f"[OK] Generated: english/english_posts/{folder}.html")

        posts_index.append({
            'title': meta['title'],
            'date': meta['date'],
            'description': meta['description'],
            'subtitle': meta.get('subtitle', ''),
            'tag': meta.get('tag', ''),
            'tags': meta.get('tags', []),
            'url': f'english/english_posts/{folder}.html',
        })

    posts_index.sort(key=lambda p: p['date'], reverse=True)

    with open(POSTS_JSON, 'w', encoding='utf-8') as f:
        json.dump(posts_index, f, indent=2, ensure_ascii=False)
    print(f"[OK] Generated: english/english_posts.json with {len(posts_index)} post(s).")


if __name__ == '__main__':
    main()
