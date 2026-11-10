"""Shared style, cached downloads and published FTW-2E indexes for the slide figures."""

import io
import urllib.request
import zipfile
from pathlib import Path

import geopandas as gpd
import matplotlib as mpl

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / '.cache' / 'figures'
OUT = ROOT / 'assets'

BG = '#f4f4eb'  # Taylor Geospatial ivory, the slide background
INK = '#000000'
MUTED = '#555555'
RULE = '#cccccc'
LAND = '#e4e3d6'
ACCENT = '#80a0d8'
PALE = '#a7d0dc'
CORAL = '#ff4f2c'
FIELD = ['#e0cfa2', '#cbb57a', '#a99257', '#6f6a33', '#3f4f1f']  # sand to deep crop green

SOURCE_COOP = 'https://data.source.coop/ftw/global-data-2e'
NATURAL_EARTH = 'https://naciscdn.org/naturalearth/{res}/physical/ne_{res}_land.zip'
EQUAL_EARTH = 'EPSG:8857'


def setup_style() -> None:
    """Arial, black on TG ivory, as the deck theme; no chart junk."""
    mpl.rcParams.update({
        'font.family': ['Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': 15,
        'text.color': INK,
        'axes.labelcolor': INK,
        'axes.edgecolor': INK,
        'xtick.color': INK,
        'ytick.color': INK,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'figure.facecolor': BG,
        'axes.facecolor': BG,
        'savefig.facecolor': BG,
        'svg.fonttype': 'path',
    })


def cached(name: str, url: str) -> Path:
    """Download once into .cache/figures."""
    path = CACHE / name
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={'User-Agent': 'ut-austin-giscience-2026 figures'})
        with urllib.request.urlopen(req) as r:  # the Source Coop proxy rejects urllib's default agent
            path.write_bytes(r.read())
    return path


def land(res: str = '50m') -> gpd.GeoDataFrame:
    """Natural Earth land polygons (public domain)."""
    folder = CACHE / f'ne_{res}_land'
    if not folder.exists():
        data = cached(f'ne_{res}_land.zip', NATURAL_EARTH.format(res=res)).read_bytes()
        zipfile.ZipFile(io.BytesIO(data)).extractall(folder)
    return gpd.read_file(folder / f'ne_{res}_land.shp')


def raster_index() -> Path:
    """Published per-(year, tile) raster index; one row per tile-year."""
    return cached('raster.parquet', f'{SOURCE_COOP}/index/raster.parquet')


def vector_index() -> Path:
    """Published per-(year, UTM zone) vector index."""
    return cached('vector.parquet', f'{SOURCE_COOP}/index/vector.parquet')
