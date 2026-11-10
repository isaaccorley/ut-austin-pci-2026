"""Model inputs and outputs for one window: four quarterly mosaics, then p(field) and p(boundary).

Reads the public Sentinel-2 quarterly mosaics and the published FTW-2E probability COG.
uv run --no-project --with geopandas --with pyarrow --with matplotlib --with rasterio --with pillow python scripts/figures/ftw_inputs.py
"""

import os

import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer
from rasterio.windows import from_bounds

from common import OUT

os.environ.setdefault('GDAL_HTTP_USERAGENT', 'ut-austin-giscience-2026 figures')
os.environ.setdefault('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')

MOSAICS = 'https://data.source.coop/tge-labs/sentinel-2-quarterly-cloudless-mosaics'
SCORES = 'https://data.source.coop/ftw/global-data-2e/raster'
YEAR, TILE, EPSG = 2025, '15TVG_0_0', 32615
CENTER = (-93.0, 41.95)  # Marshall County, Iowa: the 2e README's example area
HALF_M = 2000  # 4 km window
SIZE = 640  # output px
DEST = OUT / 'ftw-inputs'
FIELD = np.array([0, 158, 115]) / 255  # pipeline-figure colours
BOUND = np.array([230, 159, 0]) / 255


def window_bounds():
    x, y = Transformer.from_crs('EPSG:4326', f'EPSG:{EPSG}', always_xy=True).transform(*CENTER)
    x, y = round(x / 10) * 10, round(y / 10) * 10
    return x - HALF_M, y - HALF_M, x + HALF_M, y + HALF_M


def read(url: str, bounds, band: int = 1) -> np.ndarray:
    with rasterio.open(url) as ds:
        assert ds.crs.to_epsg() == EPSG, (url, ds.crs)
        return ds.read(band, window=from_bounds(*bounds, ds.transform))


def save(rgb01: np.ndarray, name: str) -> None:
    img = Image.fromarray((np.clip(rgb01, 0, 1) * 255).astype(np.uint8))
    img.resize((SIZE, SIZE), Image.LANCZOS).save(DEST / name, quality=88)


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    b = window_bounds()
    for q in ('Q1', 'Q2', 'Q3', 'Q4'):
        rgb = np.stack([read(f'{MOSAICS}/{YEAR}/{q}/{TILE}/{band}.tif', b) for band in ('B04', 'B03', 'B02')], -1)
        save(np.clip(np.clip(rgb, 0, None) / 3000, 0, 1) ** 0.7, f'{q.lower()}.jpg')  # viewer stretch
    cog = f'{SCORES}/{YEAR}/zone={TILE[:2]}/gzd={TILE[:3]}/{TILE}/{TILE}.tif'
    for band, name, color in ((1, 'p-field.jpg', FIELD), (2, 'p-boundary.jpg', BOUND)):
        p = read(cog, b, band).astype(np.float32) / 255
        save(1 - p[..., None] * (1 - color), name)  # white-to-colour ramp, as in the pipeline figure
    print('bounds', b)


if __name__ == '__main__':
    main()
