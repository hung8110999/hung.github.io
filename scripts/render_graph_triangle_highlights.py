"""Tint regions on arch_graph_triangle_block.png for blog callouts (A/B/C).

Adjust REGION_FRAC if overlays miss the hand-drawn regions on a revised sketch.
"""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'english/markdown_posts_english/proteus/image/arch_graph_triangle_block.png'
OUT_DIR = SRC.parent

# (x0, y0, x1, y1) as fractions of width/height — tuned for 4944×1552 sketch.
# C: triangle multiplicative update — mask like the hand-annotated ref: full node + pad above/below,
#    and overlap the right edge of the pair-representation grid on the left (same sketch).
# B: upper geometry branch only; bottom trimmed so it does not wash over C.
# A: collate → attention → scatter; starts under the yellow mask.
REGION_FRAC = {
    'C_yellow': (0.01, 0.355, 0.372, 0.738),
    'B_blue': (0.20, 0.05, 0.78, 0.33),
    'A_red': (0.12, 0.748, 0.995, 0.96),
}

COLORS = {
    'C_yellow': (255, 220, 40, 95),
    'B_blue': (70, 140, 255, 95),
    'A_red': (230, 70, 70, 95),
}


def main():
    im = Image.open(SRC).convert('RGBA')
    w, h = im.size
    for key, frac in REGION_FRAC.items():
        box = tuple(int(round(v * (w if i % 2 == 0 else h))) for i, v in enumerate(frac))
        overlay = Image.new('RGBA', im.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle(box, fill=COLORS[key])
        composed = Image.alpha_composite(im, overlay)
        out_path = OUT_DIR / f'graph_triangle_highlight_{key}.png'
        composed.convert('RGB').save(out_path, optimize=True)
        print(out_path.name, box)


if __name__ == '__main__':
    main()
