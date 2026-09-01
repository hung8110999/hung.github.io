# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A personal static website / study blog hosted on GitHub Pages (`hwnggn.github.io`). There is **no framework, bundler, or Jekyll** — the only build step is a set of Python scripts that convert Markdown into static HTML. The published site is just the raw files in this repo served as-is.

## Commands

Regenerate the HTML + JSON after editing any Markdown post (run from repo root):

```bash
python scripts/convert.py                # all sections
python scripts/convert.py math english   # only the named sections
```

One script builds every section; there is no watch mode and no test suite — after converting, open the `.html` files directly in a browser (or use any static server, e.g. `python -m http.server`) to preview.

`scripts/render_graph_triangle_highlights.py` is a one-off image utility (requires Pillow) that tints regions on a specific sketch for the `english/proteus` post; not part of the normal flow.

## Content pipeline (the core architecture)

The site has four parallel content sections that all follow the **same three-part pattern**. Understanding one means understanding all four:

| Section | Source (edit here) | Generated HTML | Generated index |
|---------|--------------------|----------------|-----------------|
| blog    | `blog/markdown_posts/<slug>/blog.md`             | `blog/posts/<slug>.html`           | `blog/posts.json`           |
| math    | `math/markdown_posts_math/<slug>/blog.md`        | `math/math-posts/<slug>.html`      | `math/math_posts.json`      |
| english | `english/markdown_posts_english/<slug>/blog.md`  | `english/english_posts/<slug>.html`| `english/english_posts.json`|
| coding  | `coding/markdown_posts_coding/<slug>/blog.md`    | `coding/coding_posts/<slug>.html`  | `coding/coding_posts.json`  |

All four are driven by **one script, `scripts/convert.py`**. Everything a section does differently — paths, page title suffix, back-link, which nav entry is active, math engine, whether tags/repo reach the JSON index — is declared in its `SECTIONS` entry at the top of the file; the Markdown pipeline and page template below are shared. Adding a section means adding a dict entry, not a new script.

Rules that hold across all sections:

- **Never hand-edit the generated `.html` files or the `*_posts.json` files.** They are overwritten on every conversion run. Edit the source `blog.md` and re-run the converter.
- Each post lives in its **own folder**; the converter scans for subfolders containing a `.md` file. Post images go inside that folder (e.g. `<slug>/image/foo.png`) and are referenced with relative paths in Markdown — the converter rewrites them to point back at the source folder.
- The folder name is the slug used for the output filename and URL.
- The converter is a **hand-rolled Markdown→HTML implementation** (a series of regex passes — fenced code, notes, math, images-before-links, headings, bold/italic, lists, paragraph wrapping). It is not CommonMark-complete; when a construct doesn't render, read the passes in `convert_markdown()` rather than assuming standard Markdown behavior. Pass order matters and is commented where it does.

### Post front matter

Metadata comes from either YAML front matter at the top (`--- ... ---`) or an HTML `<!-- key: value -->` comment; the title is the first `# H1` (which is stripped from the body). Recognized keys: `date`, `description`, `subtitle`, `hide`, and per-section `tag`/`tags` (comma-separated or `[bracketed, list]`). `coding` additionally supports `repo: https://...` for repository-link cards.

**`hide: true`** (also `yes`/`on`/`1`) unlists a post. The page is still generated and stays reachable by URL, but it is left out of the JSON index — so it appears in no listing, neither its section page nor Latest News on the home page. Because every listing is driven by the JSON, that one flag is all it takes. To take a post off the site entirely, delete its source folder and generated `.html`.

### Markdown features

Available in **every** section:

- **Fenced code blocks** — ```` ```lang ```` … ```` ``` ````.
- **Margin notes** — `::: notes [left|right] Optional Title` … body … `:::` (closing line exactly `:::`). Renders as `<aside class="blog-post-notes blog-post-notes--left|right">`, parked in the outer margin on wide screens; notes may nest and may contain images/math.
- **Image attributes** — `![alt](path){width=50% position=right}` (Pandoc spelling) or `![alt](path){width: 50%}` (CSS spelling). Both are accepted; `position` maps to a `fig-*` class, everything else becomes inline CSS. An italic line directly after an image becomes its `<figcaption>`.

Per-section (set in `SECTIONS`, because each needs its own CDN `<script>` in the page head):

- **math** renders LaTeX with **KaTeX**: inline `$...$` / `\(...\)`, block `$$...$$` / `\[...\]`. Math is pulled out into placeholders *before* the Markdown passes so `*`, `_`, etc. inside formulas survive.
- **english** renders LaTeX with **MathJax** and supports ```` ```mermaid ```` diagrams.
- **coding** supports `repo: https://...` front matter, which adds a "View Repository" button to the post and a `repo` field to the JSON index (used by `data-layout="repo"` cards).

## Client-side rendering (`js/main.js`)

The section landing pages (`blog.html`, `math.html`, etc.) and `index.html` are static shells; posts are injected client-side by `loadPosts()`. It reads container `data-*` attributes and `fetch`es the JSON indexes:

- `data-json="path/to.json"` — single index source.
- `data-json-sources="a.json, b.json"` — used on the home page to merge multiple sections' latest posts (shows newest 3).
- `data-layout` — `news` (default), `home`, `learning-log`, or `repo`. Controls the card markup.

Tag display colors are driven by the `tagToClass` map in `main.js` — if you add a new tag value, add a matching `bg-*` CSS class and map entry there, otherwise it falls back to `bg-algebra`. `main.js` also owns the navbar/mobile menu, study-page topic toggles, timeline dot alignment, and the wide-screen margin-note stacking logic.

## Styling

All pages share the single stylesheet `css/style.css` (light-blue minimalist theme). The converters emit generated posts with fixed `blog-post-*` class names, so style changes for post bodies go in `style.css` against those classes rather than in the generated HTML.
