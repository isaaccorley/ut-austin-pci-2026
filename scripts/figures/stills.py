"""Paper table crop and catalog screenshot: PRUE Table 1 and the Portolan harmonized field data catalog.

The catalog capture drives the locally installed Google Chrome through Playwright.
uv run --no-project --with geopandas --with matplotlib --with pymupdf --with pillow --with playwright python scripts/figures/stills.py
"""

import io

import pymupdf
from PIL import Image
from playwright.sync_api import sync_playwright

from common import OUT, cached

PRUE_PDF = ('https://openaccess.thecvf.com/content/CVPR2026/papers/'
            'Muhawenayo_PRUE_A_Practical_Recipe_for_Field_Boundary_Segmentation_at_Scale_CVPR_2026_paper.pdf')
PRUE_TABLE = (6, pymupdf.Rect(55, 158, 557, 419))  # page index, Table 1 body between its top and bottom rules (pt)
CATALOG = 'https://browser.portolan-sdi.org/#/external/data.source.coop/ftw/harmonized-field-data/catalog.json'


def prue_table() -> None:
    page, clip = PRUE_TABLE
    pix = pymupdf.open(cached('prue-cvpr2026.pdf', PRUE_PDF))[page].get_pixmap(dpi=300, clip=clip)
    Image.open(io.BytesIO(pix.tobytes('png'))).convert('L').save(OUT / 'papers' / 'prue-table1.png', optimize=True)


def portolan_catalog() -> None:
    """Two rows of collection tiles under the sticky title bar, 2000 x 1020 CSS px at 1.5x."""
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width': 2000, 'height': 1050}, device_scale_factor=1.5)
        page.goto(CATALOG, wait_until='networkidle', timeout=90000)
        page.get_by_text('Catalogs').first.wait_for(timeout=60000)
        page.evaluate("""() => { const h = [...document.querySelectorAll('h2,h3,h4')].find(e => e.textContent.trim().startsWith('Catalogs'));
          window.scrollTo(0, h.getBoundingClientRect().top + window.scrollY - 88); }""")
        page.wait_for_function("""[...document.images].filter(i => i.getBoundingClientRect().top < innerHeight)
          .every(i => i.complete && i.naturalWidth > 0)""", timeout=60000)
        page.wait_for_timeout(1000)
        shot = Image.open(io.BytesIO(page.screenshot())).convert('RGB')
        browser.close()
    shot.crop((0, 0, 3000, 1530)).resize((2400, 1224), Image.LANCZOS).save(
        OUT / 'stills' / 'portolan-harmonized-catalog.jpg', quality=86, optimize=True)


if __name__ == '__main__':
    (OUT / 'papers').mkdir(exist_ok=True)
    prue_table()
    portolan_catalog()
