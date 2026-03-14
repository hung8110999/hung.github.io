import os
import re
import json

base_dir = r"d:\blog\hung.github.io"
markdown_dir = os.path.join(base_dir, "markdown_posts")
posts_dir = os.path.join(base_dir, "posts")
template_file = os.path.join(base_dir, "scripts", "post_template.html")

if not os.path.exists(template_file):
    print("Warning: post_template.html not found, using basic update replacing topic-content div")

def convert_markdown_to_html(markdown, folder_name):
    html = markdown
    html = re.sub(r'^# (.*)$', r'<h1 style="font-size: var(--fs-4xl); margin-bottom: var(--space-lg); line-height: 1.2;">\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*)$', r'<h2 style="margin-top: var(--space-2xl); margin-bottom: var(--space-md); font-size: var(--fs-2xl);">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*)$', r'<h3 style="margin-top: var(--space-xl); margin-bottom: var(--space-sm); font-size: var(--fs-xl);">\1</h3>', html, flags=re.MULTILINE)

    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)

    def img_repl(m):
        alt, img_path, style = m.group(1), m.group(2), m.group(3)
        final_img = f"../markdown_posts/{folder_name}/{img_path.replace(chr(92), '/')}"
        inline_style = style if style else 'width: 100%; border-radius: var(--radius-lg); margin-top: var(--space-xl); border: 1px solid var(--border-light);'
        return f'<img src="{final_img}" alt="{alt}" style="{inline_style}">'

    html = re.sub(r'!\[(.*?)\]\((.*?)\)(?:{(.*?)})?', img_repl, html)

    html = re.sub(r'^- (.*)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*</li>)', r'<ul style="margin-bottom: var(--space-lg);">\1</ul>', html, flags=re.DOTALL)

    lines = html.split('\n')
    processed_lines = []
    for line in lines:
        trimmed = line.strip()
        if trimmed and not trimmed.startswith('<') and not trimmed.startswith('<!--'):
            processed_lines.append(f'<p style="margin-bottom: var(--space-lg);">{trimmed}</p>')
        else:
            processed_lines.append(line)
    return '\n'.join(processed_lines)

for folder in os.listdir(markdown_dir):
    fpath = os.path.join(markdown_dir, folder)
    if os.path.isdir(fpath):
        md_file = os.path.join(fpath, "blog.md")
        if os.path.exists(md_file):
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            html_content = convert_markdown_to_html(content, folder)
            
            # Since user doesn't have node, let's just update the target file manually
            target_html = os.path.join(posts_dir, f"{folder}.html")
            if os.path.exists(target_html):
                with open(target_html, "r", encoding="utf-8") as f:
                    old_html = f.read()
                
                # Replace topic-content block
                new_topic_content = f'<div class="topic-content"\n                    style="font-size: var(--fs-lg); line-height: 1.8; color: var(--text-primary); padding: 0;">\n{html_content}\n                </div>'
                updated = re.sub(r'<div class="topic-content"[\s\S]*?</div>', new_topic_content, old_html, count=1)
                
                # Remove first h1 if inside body
                updated = re.sub(r'<h1.*?>.*?</h1>', '', updated, count=1, flags=re.IGNORECASE|re.DOTALL)

                with open(target_html, "w", encoding="utf-8") as f:
                    f.write(updated)
                print(f"Updated {target_html}")
