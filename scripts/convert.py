"""
convert.py - Markdown → HTML converter for every section of the site.

Replaces the old per-section scripts (convert_math.py, convert_english.py,
convert_coding.py), which were ~90% copies of each other. Everything a section
does differently now lives in one SECTIONS entry; the pipeline below is shared.

Usage:
    python scripts/convert.py                # all sections
    python scripts/convert.py math english   # only the named sections

Each section reads <root>/<markdown_dir>/<slug>/*.md and writes
<root>/<posts_dir>/<slug>.html plus a JSON index consumed by js/main.js.

Post metadata comes from YAML front matter (--- ... ---) or an HTML comment
(<!-- key: value -->); the title is the first `# H1`, which is dropped from the
body. Keys: date, description, subtitle, tag/tags (comma-separated or [a, b]),
repo (coding only), and hide.

`hide: true` (or yes/on/1) unlists a post: its page is still generated and stays
reachable by URL, but it is left out of the JSON index, so it shows up in no
listing -- not the section page, not Latest News on the home page.

Markdown extras available in every section:
  - ``` fenced code blocks (```mermaid renders as a diagram where enabled)
  - ::: notes [left|right] Optional title ... :::   margin notes, closed by `:::`
  - ![alt](path){width=50% position=right} or {width: 50%} image attributes

Math is per-section: the `math` section renders LaTeX with KaTeX, `english`
with MathJax. See the math_engine handling in convert_markdown().
"""

import argparse
import html as html_lib
import json
import os
import re
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


# ──────────────────────────────────────────────
# Per-section configuration
# ──────────────────────────────────────────────

# Head/body fragments only some sections need. Kept as plain (non-f) strings so
# the embedded JS braces and backslashes need no escaping.

KATEX_HEAD = '''

    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
'''

KATEX_BODY = '''
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            document.querySelectorAll(".math-inline").forEach(function(el) {
                var latex = el.getAttribute("data-math");
                if (latex) {
                    el.innerHTML = katex.renderToString(latex, { throwOnError: false, displayMode: false });
                }
            });
            document.querySelectorAll(".math-block").forEach(function(el) {
                var latex = el.getAttribute("data-math");
                if (latex) {
                    el.innerHTML = katex.renderToString(latex, { throwOnError: false, displayMode: true });
                }
            });
        });
    </script>'''

MATHJAX_MERMAID_HEAD = r'''
    <script>
        window.MathJax = {
            tex: {
                inlineMath: [['\\(', '\\)'], ['$', '$']],
                displayMath: [['\\[', '\\]'], ['$$', '$$']]
            },
            svg: {
                fontCache: 'global'
            }
        };
    </script>
    <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
        window.addEventListener('DOMContentLoaded', function () {
            if (window.mermaid) {
                mermaid.initialize({ startOnLoad: true, securityLevel: 'loose' });
            }
        });
    </script>'''


SECTIONS = {
    'blog': {
        'markdown_dir': 'blog/markdown_posts',
        'posts_dir': 'blog/posts',
        'posts_json': 'blog/posts.json',
        'title_suffix': "Hung's Blog",
        'back_href': '../../blog.html',
        'back_label': 'Blog',
        'nav_active': 'blog',      # which nav entry is highlighted
        'study_active': False,     # highlight the "Study" dropdown trigger too
        'math_engine': None,       # None | 'katex' | 'mathjax'
        'mermaid': False,
        'index_tags': False,       # emit tag/tags in the JSON index
        'index_repo': False,       # emit repo in the index + a repo button
    },
    'math': {
        'markdown_dir': 'math/markdown_posts_math',
        'posts_dir': 'math/math-posts',
        'posts_json': 'math/math_posts.json',
        'title_suffix': "Hung's Math Blog",
        'back_href': '../../math.html',
        'back_label': 'Math Notes',
        'nav_active': 'math',
        'study_active': False,
        'math_engine': 'katex',
        'mermaid': False,
        'index_tags': True,
        'index_repo': False,
    },
    'english': {
        'markdown_dir': 'english/markdown_posts_english',
        'posts_dir': 'english/english_posts',
        'posts_json': 'english/english_posts.json',
        'title_suffix': "Hung's English Notes",
        'back_href': '../../english.html',
        'back_label': 'English Notes',
        'nav_active': 'english',
        'study_active': True,
        'math_engine': 'mathjax',
        'mermaid': True,
        'index_tags': True,
        'index_repo': False,
    },
    'coding': {
        'markdown_dir': 'coding/markdown_posts_coding',
        'posts_dir': 'coding/coding_posts',
        'posts_json': 'coding/coding_posts.json',
        'title_suffix': "Hung's Coding Notes",
        'back_href': '../../coding.html',
        'back_label': 'Coding Notes',
        'nav_active': 'coding',
        'study_active': True,
        'math_engine': None,
        'mermaid': False,
        'index_tags': True,
        'index_repo': True,
    },
}


def _head_extra(cfg):
    if cfg['math_engine'] == 'katex':
        return KATEX_HEAD
    if cfg['math_engine'] == 'mathjax' or cfg['mermaid']:
        return MATHJAX_MERMAID_HEAD
    return ''


def _body_extra(cfg):
    return KATEX_BODY if cfg['math_engine'] == 'katex' else ''


# ──────────────────────────────────────────────
# Math extraction (KaTeX): protect LaTeX from the markdown regexes
# ──────────────────────────────────────────────

def _extract_math(md):
    """Replace math with placeholders. Returns (text, [(kind, latex), ...]).

    Order matters: block $$ first, then \\[ \\], then inline $, then \\( \\).
    """
    math_list = []

    def repl_block(m):
        math_list.append(('block', m.group(1).strip()))
        return f'\n\n<!--MATH_BLOCK_{len(math_list) - 1}-->\n\n'

    def repl_inline(m):
        math_list.append(('inline', m.group(1).strip()))
        return f'<!--MATH_INLINE_{len(math_list) - 1}-->'

    text = re.sub(r'\$\$([\s\S]*?)\$\$', repl_block, md)
    text = re.sub(r'\\\[([\s\S]*?)\\\]', repl_block, text)
    text = re.sub(r'(?<!\$)\$(?!\$)([^$\n]+?)\$(?!\$)', repl_inline, text)
    text = re.sub(r'\\\(([\s\S]*?)\\\)', repl_inline, text)
    return text, math_list


def _restore_math(html, math_list):
    """Turn the placeholders into elements the KaTeX bootstrap can render."""
    for i, (kind, latex) in enumerate(math_list):
        escaped = (latex.replace('&', '&amp;').replace('<', '&lt;')
                   .replace('>', '&gt;').replace('"', '&quot;'))
        if kind == 'block':
            html = html.replace(f'<!--MATH_BLOCK_{i}-->',
                                f'<div class="math-block" data-math="{escaped}"></div>')
        else:
            html = html.replace(f'<!--MATH_INLINE_{i}-->',
                                f'<span class="math-inline" data-math="{escaped}"></span>')
    return html


# ──────────────────────────────────────────────
# Markdown → HTML
# ──────────────────────────────────────────────

_NOTES_SIDE_PREFIX = re.compile(r'^\[\s*(left|right)\s*\]\s*(.*)$', re.IGNORECASE | re.DOTALL)

_POSITION_CLASSES = {
    'left': 'fig-left',
    'right': 'fig-right',
    'inline': 'fig-inline',
    'behind': 'fig-behind',
    'front': 'fig-front',
}


def _parse_notes_title_line(raw):
    """Return (side, display_title); side defaults to 'right'."""
    m = _NOTES_SIDE_PREFIX.match((raw or '').strip())
    if m:
        return m.group(1).lower(), (m.group(2) or '').strip()
    return 'right', (raw or '').strip()


def _image_attrs(attrs):
    """Parse an image attribute block into (extra figure class, style attribute).

    Accepts both the Pandoc spelling `{width=50% position=right}` and the CSS
    spelling `{width: 50%}` -- both are already in use across sections.
    """
    extra_class = ''
    css_parts = []
    for key, val in re.findall(r'([\w-]+)\s*[:=]\s*([^\s;]+)', attrs or ''):
        if key == 'position' and val in _POSITION_CLASSES:
            extra_class += f' {_POSITION_CLASSES[val]}'
        else:
            css_parts.append(f'{key}: {val}')
    style = f' style="{"; ".join(css_parts)}"' if css_parts else ''
    return extra_class, style


def convert_markdown(md, cfg, folder_name):
    html = md
    block_store = {}
    notes_store = {}
    counters = {'block': 0, 'notes': 0}

    def stash_block(content):
        token = f"@@BLOCK_{counters['block']}@@"
        block_store[token] = content
        counters['block'] += 1
        return token

    # ── Fenced code blocks: before inline backticks, so ``` wins over ` ──
    def fenced_block_repl(m):
        lang = (m.group(1) or '').strip().lower()
        code = (m.group(2) or '').rstrip()
        if lang == 'mermaid' and cfg['mermaid']:
            return stash_block(f'<div class="mermaid">\n{code}\n</div>')
        escaped = html_lib.escape(code)
        class_attr = f' language-{lang}' if lang else ''
        return stash_block(
            f'<pre class="blog-post-pre"><code class="blog-post-code{class_attr}">{escaped}</code></pre>'
        )

    html = re.sub(r'```([a-zA-Z0-9_-]*)\n([\s\S]*?)\n```', fenced_block_repl, html)

    # ── Margin notes: before math, so a note body may contain equations ──
    notes_pattern = re.compile(
        r'^::: notes(?:[ \t]+([^\n]*))?[ \t]*\n([\s\S]*?)^:::[ \t]*$',
        re.MULTILINE,
    )
    while True:
        m = notes_pattern.search(html)
        if not m:
            break
        side, title = _parse_notes_title_line(m.group(1) or '')
        token = f"@@NOTES_BLOCK_{counters['notes']}@@"
        notes_store[token] = (title, m.group(2).rstrip('\n'), side)
        counters['notes'] += 1
        html = html[:m.start()] + '\n' + token + '\n' + html[m.end():]

    # ── Math ──
    math_list = []
    if cfg['math_engine'] == 'katex':
        html, math_list = _extract_math(html)
    elif cfg['math_engine'] == 'mathjax':
        # Stash display math so paragraph/list post-processing leaves it alone.
        html = re.sub(
            r'^\$\$\s*\n([\s\S]*?)\n\$\$\s*$',
            lambda m: stash_block(f'<div class="blog-post-math-block">\\[{m.group(1).strip()}\\]</div>'),
            html,
            flags=re.MULTILINE,
        )

    # ── Images: before links (both use bracket syntax) and before inline math,
    #    whose <span> would otherwise be injected into an alt attribute. ──
    def img_repl(m):
        alt, img_path, attrs = m.group(1), m.group(2), m.group(3)
        normalized = img_path.replace('\\', '/')
        final_path = f"../{os.path.basename(cfg['markdown_dir'])}/{folder_name}/{normalized}"
        extra_class, inline_style = _image_attrs(attrs)
        return (
            f'<figure class="blog-post-figure{extra_class}">\n'
            f'  <img src="{final_path}" alt="{html_lib.escape(alt, quote=True)}"'
            f' class="blog-post-img"{inline_style}>\n'
            f'</figure>'
        )

    html = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)(?:\{([^}]*)\})?', img_repl, html)

    if cfg['math_engine'] == 'mathjax':
        # An alt attribute may legitimately contain \( ... \); hide whole figures
        # from the inline-math pass so it cannot rewrite text inside attributes.
        figure_stash = {}

        def stash_figure(m):
            tok = f'@@FIGSTASH_{len(figure_stash)}@@'
            figure_stash[tok] = m.group(0)
            return tok

        html = re.sub(r'<figure class="blog-post-figure[^"]*">[\s\S]*?</figure>', stash_figure, html)
        html = re.sub(r'\\\((.+?)\\\)',
                      lambda m: f'<span class="blog-post-math">\\({m.group(1).strip()}\\)</span>', html)
        html = re.sub(r'(?<!\$)\$([^\$\n]+)\$(?!\$)',
                      lambda m: f'<span class="blog-post-math">\\({m.group(1).strip()}\\)</span>', html)
        for tok, fig in figure_stash.items():
            html = html.replace(tok, fig)

    # ── Inline formatting ──
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

    # ── Unordered lists ──
    processed = []
    in_list = False
    for line in html.split('\n'):
        list_match = re.match(r'^- (.+)$', line.strip())
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

    # ── Image captions: an italic line right after a figure ──
    html = re.sub(
        r'</figure>\s*(?:\*|<em>)\s*([^\n]+)',
        lambda m: f'<figcaption class="blog-post-caption">'
                  f'{m.group(1).replace("</em>", "").strip("* ").strip()}</figcaption>\n</figure>',
        html
    )

    # ── Wrap remaining bare text lines in paragraphs ──
    output = []
    for line in html.split('\n'):
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
    html = '\n'.join(output)

    # ── Restore stashed content ──
    for token, content in block_store.items():
        html = html.replace(token, content)

    for token, (title, inner_md, side) in notes_store.items():
        inner_html = convert_markdown(inner_md, cfg, folder_name)
        t = (title or '').strip()
        if not t or t.lower() in ('note', 'notes'):
            suffix_html, aria = '', 'Note'
        else:
            suffix_html = f'<span class="blog-post-notes-title-suffix"> - {html_lib.escape(t)}</span>'
            aria = f'Note - {t}'
        side_class = 'blog-post-notes--left' if side == 'left' else 'blog-post-notes--right'
        html = html.replace(token, (
            f'<aside class="blog-post-notes {side_class}" aria-label="{html_lib.escape(aria)}">\n'
            f'<strong class="blog-post-notes-label"><span class="blog-post-notes-mark">Note</span>'
            f'{suffix_html}</strong>\n'
            f'{inner_html}\n'
            f'</aside>'
        ))

    if math_list:
        html = _restore_math(html, math_list)

    return html


# ──────────────────────────────────────────────
# Front matter
# ──────────────────────────────────────────────

def _parse_simple_kv(block):
    """Parse a loose 'key: value' block, one pair per line."""
    data = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or ':' not in line:
            continue
        k, v = line.split(':', 1)
        k = k.strip().lower()
        if k:
            data[k] = v.strip()
    return data


def _extract_yaml_frontmatter(md):
    """Return (data, start, end); end is where the body begins, or None."""
    if not md.startswith('---'):
        return {}, None, None
    m = re.match(r'^---\s*\n([\s\S]*?)\n---\s*(?:\n|$)', md)
    if not m:
        return {}, None, None
    return _parse_simple_kv(m.group(1)), m.start(), m.end()


def _parse_date_flexible(date_str):
    date_str = (date_str or '').strip()
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    return None


_TRUTHY = {'true', 'yes', 'on', '1'}


def _parse_bool(val):
    """Front-matter booleans are plain strings: true/yes/on/1 mean true."""
    return str(val or '').strip().lower() in _TRUTHY


def _parse_tags_value(val):
    """Parse a `tags` value: comma-separated, optionally wrapped in [ ]."""
    s = str(val or '').strip()
    if not s:
        return []
    if s.startswith('[') and s.endswith(']'):
        s = s[1:-1]
    return [p.strip() for p in re.split(r'\s*,\s*', s) if p.strip()]


def _tags_from_kv(data):
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
        'repo': '',
        'hide': False,
    }

    # An HTML comment overrides YAML front matter when a post carries both.
    yaml_data, _, _ = _extract_yaml_frontmatter(md)
    comment_match = re.search(r'<!--([\s\S]*?)-->', md)
    comment_data = _parse_simple_kv(comment_match.group(1)) if comment_match else {}

    collected = []
    for data in (yaml_data, comment_data):
        if not data:
            continue
        for key in ('date', 'description', 'subtitle', 'repo'):
            if key in data:
                meta[key] = data.get(key, '').strip()
        if 'hide' in data:
            meta['hide'] = _parse_bool(data['hide'])
        collected.extend(_tags_from_kv(data))

    meta['tags'] = _dedupe_tags(collected)
    meta['tag'] = meta['tags'][0] if meta['tags'] else ''

    title_match = re.search(r'^# (.+)$', md, re.MULTILINE)
    if title_match:
        meta['title'] = title_match.group(1).strip()

    return meta


# ──────────────────────────────────────────────
# Page template
# ──────────────────────────────────────────────

def _nav_html(cfg):
    def cls(key):
        return ' class="active"' if cfg['nav_active'] == key else ''

    study = ' class="active"' if cfg['study_active'] else ''
    return f"""            <ul class="nav-links" id="navLinks">
                <li><a href="../../index.html">Profile</a></li>
                <li><a href="../../road.html">My Road</a></li>
                <li class="nav-dropdown">
                    <a href="#"{study}>Study ▾</a>
                    <div class="dropdown-menu">
                        <a href="../../math.html"{cls('math')}>Math</a>
                        <a href="../../english.html"{cls('english')}>English</a>
                        <a href="../../coding.html"{cls('coding')}>Coding</a>
                    </div>
                </li>
                <li><a href="../../blog.html"{cls('blog')}>Blog</a></li>
            </ul>"""


def build_post_html(meta, body_html, cfg):
    d = _parse_date_flexible(meta.get('date', ''))
    formatted_date = d.strftime('%B %d, %Y') if d else (meta.get('date') or '')
    subtitle_html = (f'<div class="blog-post-subtitle">{meta["subtitle"]}</div>'
                     if meta.get('subtitle') else '')

    # Sections with repo support keep the button's line even when it is empty.
    footer_lead = ''
    if cfg['index_repo']:
        repo_html = (
            f'<p><a href="{meta["repo"]}" class="btn btn-secondary" target="_blank"'
            f' rel="noopener">View Repository</a></p>'
            if meta.get('repo') else ''
        )
        footer_lead = f'{repo_html}\n                '

    return f"""<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{meta['title']} - {cfg['title_suffix']}</title>
    <meta name="description" content="{meta['description']}">
    <meta name="date" content="{meta['date']}">
    <link rel="stylesheet" href="../../css/style.css">
    <link rel="icon" type="image/png" href="../../assets/favicon.png">{_head_extra(cfg)}
</head>

<body>
    <!-- Navigation -->
    <nav class="navbar" id="navbar">
        <div class="nav-container">
            <a href="../../index.html" class="nav-logo"><img src="../../assets/favicon.png" alt="" class="logo-icon"> Hung Nguyen's Blog</a>
{_nav_html(cfg)}
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
                {footer_lead}<a href="{cfg['back_href']}" class="btn btn-secondary">← Back to {cfg['back_label']}</a>
            </div>
        </article>
    </main>

    <footer class="footer">
        <p>© 2026 Nguyen Gia Hung</p>
    </footer>
    <script src="../../js/main.js"></script>{_body_extra(cfg)}
</body>

</html>
"""


# ──────────────────────────────────────────────
# Build
# ──────────────────────────────────────────────

def build_section(name, cfg):
    markdown_dir = os.path.join(ROOT, cfg['markdown_dir'])
    posts_dir = os.path.join(ROOT, cfg['posts_dir'])
    posts_json = os.path.join(ROOT, cfg['posts_json'])

    if not os.path.isdir(markdown_dir):
        print(f"[SKIP] {name}: '{cfg['markdown_dir']}' not found. "
              f"Create it and add subfolders containing a .md file.")
        return

    os.makedirs(posts_dir, exist_ok=True)
    posts_index = []

    folders = sorted(f for f in os.listdir(markdown_dir)
                     if os.path.isdir(os.path.join(markdown_dir, f)))

    for folder in folders:
        folder_path = os.path.join(markdown_dir, folder)
        md_files = [f for f in os.listdir(folder_path) if f.endswith('.md')]
        if not md_files:
            print(f"[SKIP] {name}/{folder}: no .md file found.")
            continue

        with open(os.path.join(folder_path, md_files[0]), 'r', encoding='utf-8') as f:
            raw = f.read()

        meta = extract_metadata(raw)

        # Body = source minus front matter, the metadata comment, and the H1.
        _, _, fm_end = _extract_yaml_frontmatter(raw)
        body = raw[fm_end:] if fm_end is not None else raw
        body = re.sub(r'<!--[\s\S]*?-->', '', body, count=1).strip()
        body = re.sub(r'^# .+$', '', body, count=1, flags=re.MULTILINE).strip()

        post_html = build_post_html(meta, convert_markdown(body, cfg, folder), cfg)

        with open(os.path.join(posts_dir, f'{folder}.html'), 'w', encoding='utf-8') as f:
            f.write(post_html)

        # `hide: true` keeps the page reachable by URL but out of the JSON index,
        # so it appears in no listing -- neither the section page nor Latest News.
        if meta['hide']:
            print(f"[HIDE] {cfg['posts_dir']}/{folder}.html (generated, not listed)")
            continue

        print(f"[OK] Generated: {cfg['posts_dir']}/{folder}.html")

        entry = {
            'title': meta['title'],
            'date': meta['date'],
            'description': meta['description'],
            'subtitle': meta.get('subtitle', ''),
        }
        if cfg['index_tags']:
            entry['tag'] = meta.get('tag', '')
            entry['tags'] = meta.get('tags', [])
        if cfg['index_repo']:
            entry['repo'] = meta.get('repo', '')
        entry['url'] = f"{cfg['posts_dir']}/{folder}.html"
        posts_index.append(entry)

    posts_index.sort(key=lambda p: p['date'], reverse=True)

    with open(posts_json, 'w', encoding='utf-8') as f:
        json.dump(posts_index, f, indent=2, ensure_ascii=False)
    print(f"[OK] Generated: {cfg['posts_json']} with {len(posts_index)} post(s).")


def main():
    parser = argparse.ArgumentParser(
        description='Convert Markdown posts to HTML for every section of the site.')
    parser.add_argument('sections', nargs='*', metavar='SECTION',
                        help=f"sections to build (default: all of {', '.join(SECTIONS)})")
    args = parser.parse_args()

    names = args.sections or list(SECTIONS)
    unknown = [n for n in names if n not in SECTIONS]
    if unknown:
        parser.error(f"unknown section(s): {', '.join(unknown)}. "
                     f"Choose from: {', '.join(SECTIONS)}")

    for name in names:
        build_section(name, SECTIONS[name])


if __name__ == '__main__':
    main()
