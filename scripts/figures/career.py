"""Career path: industry and research labs above, degrees below, two parallel lines on one time axis.

Entries and logos are from isaac.earth (Experience, Education; images/logos), copied into assets/logos.
uv run --no-project --with geopandas --with matplotlib python scripts/figures/career.py
"""

import base64
import math

from common import BG, INK, MUTED, OUT

LOGOS = OUT / 'logos'
WORK = '#3b1e1c'  # TG brown
SCHOOL = '#5a7ab8'  # TG periwinkle, light-mode variant
W, H = 1472, 625
Y_WORK, Y_SCHOOL = 228, 388  # line centres
CARD, LOGO = 96, 74

# (year, [(logo, name lines)]); one point can carry two organisations that started the same year
WORK_POINTS = [
    (2015, [('ornl.webp', ['ORNL'])]),
    (2016, [('swri.webp', ['SwRI'])]),
    (2018, [('booz-allen.png', ['Booz', 'Allen'])]),
    (2019, [('housecanary.png', ['HouseCanary'])]),
    (2021, [('blacksky.png', ['BlackSky']), ('zeitview.webp', ['Zeitview'])]),
    (2024, [('microsoft.png', ['Microsoft', 'Research'])]),
    (2025, [('wherobots.png', ['Wherobots'])]),
    (2026, [('taylor-geospatial.png', ['Taylor', 'Geospatial'])]),
]
DEGREES = [
    (2016, 'tamuk.webp', 'B.S.', 'Texas A&amp;M–Kingsville'),
    (2018, 'utsa.png', 'M.S.', 'UT San Antonio'),
    (2024, 'utsa.png', 'Ph.D.', 'UT San Antonio'),
]


def x(year: float) -> float:
    return 60 + (year - 2015) * (W - 120) / 11


def wobble(px: float) -> float:
    """Same offset for both lines, so they stay parallel."""
    return 11 * math.sin(2 * math.pi * px / 310 + 0.4) + 5 * math.sin(2 * math.pi * px / 137 + 1.7)


def squiggle(y0: float, color: str) -> str:
    pts = ' '.join(f'{px},{y0 + wobble(px):.1f}' for px in range(0, W + 1, 4))
    return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round"/>'


def data_uri(name: str) -> str:
    mime = 'image/webp' if name.endswith('.webp') else 'image/png'
    return f'data:{mime};base64,' + base64.b64encode((LOGOS / name).read_bytes()).decode()


def card(cx: float, top: float, logo: str) -> str:
    pad = (CARD - LOGO) / 2
    return (f'<rect x="{cx - CARD / 2}" y="{top}" width="{CARD}" height="{CARD}" rx="12" fill="#fff" stroke="#d6d4c8"/>'
            f'<image href="{data_uri(logo)}" x="{cx - CARD / 2 + pad}" y="{top + pad}" width="{LOGO}" height="{LOGO}"/>')


def station(cx: float, y0: float, stem_end: float, color: str) -> str:
    dot = y0 + wobble(cx)
    return (f'<line x1="{cx}" y1="{stem_end}" x2="{cx}" y2="{dot:.1f}" stroke="{color}" stroke-width="2"/>'
            f'<circle cx="{cx}" cy="{dot:.1f}" r="9" fill="{BG}" stroke="{color}" stroke-width="4"/>')


def text(cx: float, y: float, s: str, size: int = 22, color: str = INK, weight: int = 400, anchor: str = 'middle') -> str:
    return f'<text x="{cx}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{s}</text>'


def work() -> list[str]:
    """Names, card and year stacked above each station."""
    out = []
    for year, orgs in WORK_POINTS:
        cx = x(year)
        out += [station(cx, Y_WORK, Y_WORK - 38, WORK), text(cx, Y_WORK - 44, str(year), 24, WORK, 700)]
        offsets = [0] if len(orgs) == 1 else [-(CARD + 10) / 2, (CARD + 10) / 2]
        for dx, (logo, lines) in zip(offsets, orgs, strict=True):
            out.append(card(cx + dx, Y_WORK - 165, logo))
            for i, line in enumerate(reversed(lines)):
                out.append(text(cx + dx, Y_WORK - 177 - 24 * i, line))
    return out


def school() -> list[str]:
    """Year, card, degree and school stacked below each station."""
    out = []
    for year, logo, degree, name in DEGREES:
        cx = x(year)
        out += [station(cx, Y_SCHOOL, Y_SCHOOL + 38, SCHOOL), text(cx, Y_SCHOOL + 60, str(year), 24, SCHOOL, 700),
                card(cx, Y_SCHOOL + 70, logo), text(cx, Y_SCHOOL + 194, degree, weight=700),
                text(cx, Y_SCHOOL + 219, name, color=MUTED)]
    return out


def main() -> None:
    labels = [text(0, Y_WORK + 50, 'INDUSTRY AND RESEARCH LABS', 18, WORK, 700, 'start'),
              text(0, Y_SCHOOL - 32, 'DEGREES IN ELECTRICAL ENGINEERING', 18, SCHOOL, 700, 'start')]
    body = [squiggle(Y_WORK, WORK), squiggle(Y_SCHOOL, SCHOOL), *labels, *work(), *school()]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           f'font-family="Arial, Helvetica, sans-serif" letter-spacing="0">'
           '<title>Isaac Corley: industry and research labs 2015–2026, degrees 2016–2024</title>'
           + ''.join(body) + '</svg>\n')
    (OUT / 'context' / 'career-path.svg').write_text(svg)


if __name__ == '__main__':
    main()
