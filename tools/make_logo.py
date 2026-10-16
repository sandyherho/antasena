"""Generate the antasena logo (docs/_static/logo.svg).

A deep-water emblem with a keris: the blade centerline carries seven luk
(waves) whose amplitude decays toward the tip, and the blade half-width
tapers linearly to the point. The guard (ganja), ring (selut) and curved
handle (hulu) sit above the water line. Coordinates are in a 128 x 128 box.
"""
import math
from pathlib import Path

N_LUK = 7
X0, Y_TOP, Y_TIP = 64.0, 50.0, 118.0


def blade_outline(n=200):
    """Edges are the wavy centerline shifted horizontally by the half-width.

    A horizontal (rather than normal) offset keeps both edges parallel to the
    luk, as on a real blade, and cannot self-intersect at tight bends.
    """
    left, right = [], []
    L = Y_TIP - Y_TOP
    for i in range(n + 1):
        s = i / n                                   # 0 at guard, 1 at tip
        y = Y_TOP + s * L
        amp = 2.9 * (1 - 0.6 * s)                   # luk amplitude decays toward the tip
        x = X0 + amp * math.sin(math.pi * N_LUK * s)   # N_LUK half-waves = N_LUK bends
        w = 7.4 * (1 - s) ** 0.85 + 0.2             # half-width tapers to the point
        left.append((x - w, y))
        right.append((x + w, y))
    pts = left + right[::-1]
    return "M" + " L".join(f"{px:.2f},{py:.2f}" for px, py in pts) + " Z"


def midrib(n=120):
    L = Y_TIP - Y_TOP
    pts = []
    for i in range(n + 1):
        s = 0.04 + 0.86 * i / n
        y = Y_TOP + s * L
        amp = 2.9 * (1 - 0.6 * s)
        pts.append((X0 + amp * math.sin(math.pi * N_LUK * s), y))
    return "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts)


SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-label="antasena logo">
  <defs>
    <linearGradient id="sea" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#5cc3cd"/>
      <stop offset="0.42" stop-color="#1f6f8b"/>
      <stop offset="1" stop-color="#0b2239"/>
    </linearGradient>
    <linearGradient id="steel" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#cfe6ea"/>
      <stop offset="0.5" stop-color="#ffffff"/>
      <stop offset="1" stop-color="#a9cbd2"/>
    </linearGradient>
    <linearGradient id="gold" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#f6d27a"/>
      <stop offset="1" stop-color="#c8913a"/>
    </linearGradient>
    <clipPath id="disc"><circle cx="64" cy="64" r="60"/></clipPath>
  </defs>
  <circle cx="64" cy="64" r="60" fill="url(#sea)"/>
  <g clip-path="url(#disc)">
    <path d="M0 42 q8 -6 16 0 t16 0 t16 0 t16 0 t16 0 t16 0 t16 0 t16 0 V0 H0 Z" fill="#ffffff" opacity="0.10"/>
    <path d="M0 42 q8 -6 16 0 t16 0 t16 0 t16 0 t16 0 t16 0 t16 0 t16 0" fill="none"
          stroke="#e8f4f6" stroke-width="2.4" stroke-linecap="round" opacity="0.9"/>
    <path d="M0 50 q8 -4 16 0 t16 0 t16 0 t16 0 t16 0 t16 0 t16 0 t16 0" fill="none"
          stroke="#e8f4f6" stroke-width="1.2" stroke-linecap="round" opacity="0.35"/>
  </g>
  <!-- blade (wilah) with seven luk -->
  <path d="{blade_outline()}" fill="url(#steel)" stroke="#0b2239" stroke-width="1.4" stroke-linejoin="round"/>
  <path d="{midrib()}" fill="none" stroke="#d9a54a" stroke-width="1.1" stroke-linecap="round" opacity="0.9"/>
  <!-- guard (ganja), asymmetric with the gandik side to the left -->
  <path d="M48.5 50.2 C50 45.6 54.6 44.6 59.4 45.2 L74.6 45.4 C78.6 45.6 80.4 47.6 79.8 50.8
           C70.6 52 59.6 52.2 48.5 50.2 Z" fill="url(#gold)" stroke="#0b2239" stroke-width="1.1"
        stroke-linejoin="round"/>
  <!-- ring (selut) -->
  <rect x="58.6" y="40.6" width="10.8" height="4.6" rx="2.2" fill="url(#gold)" stroke="#0b2239"
        stroke-width="1"/>
  <!-- handle (hulu), bowed forward like a Javanese nunggak semi hilt -->
  <path d="M59.6 40.8 C58.8 34 58.6 27.4 61.6 22.2 C64.2 17.8 69.6 16.8 72.2 19.6
           C74.4 22 72.6 25.2 70.2 26.4 C68.4 27.4 68.2 30.4 68.8 33.4 C69.4 36.4 69.6 38.8 69.2 40.8 Z"
        fill="#2b1a10" stroke="#0b2239" stroke-width="1.1" stroke-linejoin="round"/>
  <path d="M62.4 37.6 C61.8 32 62 27.6 64 24.4" fill="none" stroke="#7a5236" stroke-width="1.3"
        stroke-linecap="round"/>
  <!-- rising bubbles -->
  <g fill="none" stroke="#e8f4f6" stroke-linecap="round">
    <circle cx="86" cy="96" r="4.2" stroke-width="2"/>
    <circle cx="93" cy="82" r="2.8" stroke-width="1.7"/>
    <circle cx="88" cy="70" r="1.9" stroke-width="1.5"/>
    <circle cx="40" cy="88" r="2.4" stroke-width="1.5" opacity="0.7"/>
  </g>
  <circle cx="64" cy="64" r="60" fill="none" stroke="#0b2239" stroke-width="2" opacity="0.35"/>
</svg>
"""

def write_png_assets() -> None:
    """Also export docs/img/logo.png and the embedded app icon (needs cairosvg)."""
    import base64

    import cairosvg

    root = Path(__file__).resolve().parents[1]
    svg = (root / "docs" / "_static" / "logo.svg").read_bytes()

    def png(w):
        return cairosvg.svg2png(bytestring=svg, output_width=w, output_height=w)

    (root / "docs" / "img" / "logo.png").write_bytes(png(256))
    lines = ['"""Embedded antasena logo (PNG, base64) for the window icon and header.', "",
             "Generated from docs/_static/logo.svg by tools/make_logo.py. Do not edit.", '"""', ""]
    for name, w in (("ICON_64", 64), ("HEADER_44", 44)):
        b = base64.b64encode(png(w)).decode()
        lines += [f"{name} = ("] + [f'    "{b[i:i + 96]}"' for i in range(0, len(b), 96)] + [")", ""]
    (root / "src" / "antasena" / "gui" / "icon.py").write_text("\n".join(lines))


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "docs" / "_static" / "logo.svg"
    out.write_text(SVG)
    print("wrote", out)
    write_png_assets()
    print("wrote docs/img/logo.png and src/antasena/gui/icon.py")
