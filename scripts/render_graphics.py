#!/usr/bin/env python3
"""Deterministic 20-Point Star-Dial & 5-Node COSIS Aegis SVG + PNG generator."""

from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SANS = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
MONO = "ui-monospace, 'Cascadia Code', 'Fira Code', Menlo, Consolas, monospace"


def _defs(prefix: str) -> str:
    return f"""  <defs>
    <linearGradient id="{prefix}-bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#030912"/>
      <stop offset="52%" stop-color="#071b24"/>
      <stop offset="100%" stop-color="#040a14"/>
    </linearGradient>
    <linearGradient id="{prefix}-gold" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fef08a"/>
      <stop offset="50%" stop-color="#f59e0b"/>
      <stop offset="100%" stop-color="#b45309"/>
    </linearGradient>
    <linearGradient id="{prefix}-emerald" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00ff9d"/>
      <stop offset="55%" stop-color="#10b981"/>
      <stop offset="100%" stop-color="#0284c7"/>
    </linearGradient>
    <pattern id="{prefix}-grid" width="32" height="32" patternUnits="userSpaceOnUse">
      <path d="M 32 0 L 0 0 0 32" fill="none" stroke="#10b981"
            stroke-opacity="0.11" stroke-width="1"/>
      <circle cx="0" cy="0" r="1.3" fill="#fbbf24" fill-opacity="0.22"/>
    </pattern>
    <filter id="{prefix}-glow" x="-25%" y="-25%" width="150%" height="150%">
      <feGaussianBlur stdDeviation="4.5" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>"""


def _emblem_group(cx: float, cy: float, scale: float, prefix: str) -> str:
    # 20-point Art-Deco star-dial (20 NIST SP 800-53r5 families) + 5-node COSIS constellation core
    star_pts: list[str] = []
    ticks: list[str] = []
    for i in range(40):
        ang = math.radians(-90 + i * 9)
        r = (142 if i % 2 == 0 else 112) * scale
        star_pts.append(f"{cx + math.cos(ang) * r:.1f},{cy + math.sin(ang) * r:.1f}")
        if i % 2 == 0:
            tx1 = cx + math.cos(ang) * 90 * scale
            ty1 = cy + math.sin(ang) * 90 * scale
            tx2 = cx + math.cos(ang) * 104 * scale
            ty2 = cy + math.sin(ang) * 104 * scale
            ticks.append(
                f'    <line x1="{tx1:.1f}" y1="{ty1:.1f}" x2="{tx2:.1f}" y2="{ty2:.1f}" '
                f'stroke="#fde047" stroke-width="{2.6 * scale:.1f}" stroke-linecap="round"/>'
            )

    # 5 COSIS Use-Case nodes arranged in a sacred pentagram/pentagon ring
    pent_coords: list[tuple[float, float]] = []
    for idx in range(5):
        pang = math.radians(-90 + idx * 72)
        pent_coords.append(
            (cx + math.cos(pang) * 58 * scale, cy + math.sin(pang) * 58 * scale)
        )

    pent_poly = " ".join(f"{px:.1f},{py:.1f}" for px, py in pent_coords)
    chord_lines: list[str] = []
    nodes: list[str] = []
    node_colors = ["#00ff9d", "#38bdf8", "#fde047", "#00e5ff", "#10b981"]
    for idx, (px, py) in enumerate(pent_coords):
        nx, ny = pent_coords[(idx + 2) % 5]
        chord_lines.append(
            f'    <line x1="{px:.1f}" y1="{py:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" '
            f'stroke="#38bdf8" stroke-opacity="0.65" stroke-width="{2.2 * scale:.1f}"/>'
        )
        nodes.append(
            f'    <circle cx="{px:.1f}" cy="{py:.1f}" r="{10.5 * scale:.1f}" '
            f'fill="{node_colors[idx]}" stroke="#040a14" stroke-width="{2.5 * scale:.1f}" '
            f'filter="url(#{prefix}-glow)"/>'
        )

    return "\n".join(
        [
            "  <g>",
            f'    <polygon points="{" ".join(star_pts)}" fill="#071923" fill-opacity="0.95" '
            f'stroke="url(#{prefix}-gold)" stroke-width="{4.2 * scale:.1f}"/>',
            f'    <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{92 * scale:.1f}" fill="#041019" '
            f'stroke="url(#{prefix}-emerald)" stroke-width="{3.6 * scale:.1f}"/>',
            *ticks,
            f'    <polygon points="{pent_poly}" fill="#0a2730" fill-opacity="0.7" '
            f'stroke="#00ff9d" stroke-width="{2.8 * scale:.1f}"/>',
            *chord_lines,
            *nodes,
            f'    <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{14 * scale:.1f}" '
            f'fill="url(#{prefix}-gold)" filter="url(#{prefix}-glow)"/>',
            "  </g>",
        ]
    )


def build_square_icon_svg() -> str:
    return "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" '
            'width="512" height="512">',
            _defs("sc-sq"),
            '  <rect width="512" height="512" rx="92" fill="url(#sc-sq-bg)"/>',
            '  <rect width="512" height="512" rx="92" fill="url(#sc-sq-grid)"/>',
            '  <rect x="22" y="22" width="468" height="468" rx="74" fill="none" '
            'stroke="url(#sc-sq-gold)" stroke-width="4" stroke-opacity="0.85"/>',
            _emblem_group(256.0, 256.0, 1.46, "sc-sq"),
            "</svg>",
            "",
        ]
    )


def build_hero_banner_svg() -> str:
    arcs = [
        '  <path d="M 1030 92 A 95 95 0 0 1 1142 180" fill="none" '
        'stroke="#fbbf24" stroke-width="4" stroke-linecap="round" stroke-opacity="0.75"/>',
        '  <path d="M 1054 114 A 68 68 0 0 1 1122 180" fill="none" '
        'stroke="#00ff9d" stroke-width="4" stroke-linecap="round" stroke-opacity="0.8"/>',
        '  <path d="M 1076 136 A 42 42 0 0 1 1102 180" fill="none" '
        'stroke="#38bdf8" stroke-width="4" stroke-linecap="round" stroke-opacity="0.85"/>',
    ]
    return "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 360" '
            'width="1200" height="360">',
            _defs("sc-hero"),
            '  <rect width="1200" height="360" rx="24" fill="url(#sc-hero-bg)"/>',
            '  <rect width="1200" height="360" rx="24" fill="url(#sc-hero-grid)"/>',
            '  <rect x="14" y="14" width="1172" height="332" rx="18" fill="none" '
            'stroke="url(#sc-hero-gold)" stroke-width="2.5" stroke-opacity="0.82"/>',
            '  <path d="M 30 54 L 30 30 L 66 30 M 1170 54 L 1170 30 L 1134 30 '
            'M 30 306 L 30 330 L 66 330 M 1170 306 L 1170 330 L 1134 330" '
            'fill="none" stroke="#00ff9d" stroke-width="3"/>',
            *arcs,
            _emblem_group(196.0, 180.0, 1.04, "sc-hero"),
            f'  <text x="380" y="90" fill="#00ff9d" font-family="{MONO}" font-size="14" '
            'font-weight="700">20-FAMILY STAR-DIAL  //  NIST COSIS OVERLAYS</text>',
            f'  <text x="378" y="152" fill="#f8fafc" font-family="{SANS}" font-size="48" '
            'font-weight="800">SECURITY CONTROLS</text>',
            f'  <text x="380" y="196" fill="#94a3b8" font-family="{SANS}" font-size="19" '
            'font-weight="500">NIST SP 800-53 Rev. 5 Update 1 Catalog, 5 AI/SI Overlays '
            "&amp; OSCAL 1.1.2 Profiles</text>",
            '  <g transform="translate(380, 232)">',
            '    <rect width="192" height="40" rx="8" fill="#072227" '
            'stroke="#fbbf24" stroke-width="1.5"/>',
            f'    <text x="96" y="25" text-anchor="middle" fill="#fde047" font-family="{MONO}" '
            'font-size="13" font-weight="700">20 CONTROL FAMILIES</text>',
            "  </g>",
            '  <g transform="translate(586, 232)">',
            '    <rect width="202" height="40" rx="8" fill="#072227" '
            'stroke="#00ff9d" stroke-width="1.5"/>',
            f'    <text x="101" y="25" text-anchor="middle" fill="#00ff9d" font-family="{MONO}" '
            'font-size="13" font-weight="700">5 COSIS AI USE CASES</text>',
            "  </g>",
            '  <g transform="translate(802, 232)">',
            '    <rect width="204" height="40" rx="8" fill="#072227" '
            'stroke="#38bdf8" stroke-width="1.5"/>',
            f'    <text x="102" y="25" text-anchor="middle" fill="#38bdf8" font-family="{MONO}" '
            'font-size="13" font-weight="700">OSCAL 1.1.2 EXPORT</text>',
            "  </g>",
            f'  <text x="380" y="314" fill="#5eead4" font-family="{MONO}" font-size="13">'
            "$ security-controls export-oscal --use-case UC-AGENT-MULTI  -&gt;  UUIDv5 Profile"
            "</text>",
            "</svg>",
            "",
        ]
    )


def _rasterize(svg_path: Path, png_path: Path, width: int) -> None:
    import tempfile

    magick = shutil.which("magick")
    if not magick:
        raise RuntimeError("ImageMagick 'magick' binary required to rasterize PNG assets.")
    clean = (
        svg_path.read_text(encoding="utf-8")
        .replace(f'font-family="{SANS}"', 'font-family="Helvetica"')
        .replace(f'font-family="{MONO}"', 'font-family="Menlo"')
    )
    with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", encoding="utf-8") as tmp:
        tmp.write(clean)
        tmp.flush()
        cmd = [
            magick,
            "-font",
            "/System/Library/Fonts/Helvetica.ttc",
            "-background",
            "none",
            tmp.name,
            "-resize",
            f"{width}x",
            str(png_path),
        ]
        subprocess.run(cmd, check=True)  # noqa: S603


def main() -> int:
    sq = build_square_icon_svg()
    for rel_svg, rel_png in [
        ("assets/logo.svg", "assets/logo.png"),
        ("docs/assets/icon.svg", "docs/assets/icon.png"),
    ]:
        sp = ROOT / rel_svg
        pp = ROOT / rel_png
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(sq, encoding="utf-8")
        _rasterize(sp, pp, 512)

    hero_svg = ROOT / "docs" / "assets" / "logo.svg"
    hero_png = ROOT / "docs" / "assets" / "logo.png"
    hero_svg.write_text(build_hero_banner_svg(), encoding="utf-8")
    _rasterize(hero_svg, hero_png, 1200)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
