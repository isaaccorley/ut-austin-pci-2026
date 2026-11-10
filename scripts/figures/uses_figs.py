"""Who has field data and who uses it: France RPG crops, USDA crop charts, an EUDR check and war-time field loss.

France reads the RPG 2024 from the FTW harmonized field-data catalog; the EUDR panel intersects published FTW-2E
2025 polygons with Hansen Global Forest Change loss after 2020; the Ukraine map compares FTW-2E p(field) overviews.
uv run --no-project --with geopandas --with pyarrow --with matplotlib --with rasterio --with duckdb --with pymupdf --with pillow python scripts/figures/uses_figs.py
"""

import io
import os
from concurrent.futures import ThreadPoolExecutor

import duckdb
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pymupdf
import rasterio
import shapely
from matplotlib.collections import PolyCollection
from PIL import Image
from pyproj import Transformer
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
from rasterio.windows import from_bounds

from common import BG, CORAL, INK, OUT, cached, raster_index, setup_style

os.environ.setdefault('GDAL_HTTP_USERAGENT', 'ut-austin-giscience-2026 figures')
os.environ.setdefault('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')

DEST = OUT / 'uses'
MOSAICS = 'https://data.source.coop/tge-labs/sentinel-2-quarterly-cloudless-mosaics'
RPG = 'https://data.source.coop/ftw/harmonized-field-data/fr/year=2024/fr-2024.parquet'
FTW_VECTOR = 'https://data.source.coop/ftw/global-data-2e/vector/{year}/zone={zone:02d}/utm{zone:02d}.parquet'
NASS = 'https://www.nass.usda.gov/Charts_and_Maps/Crop_Progress_&_Condition/2026/US_2026.pdf'
HANSEN = ('https://storage.googleapis.com/earthenginepartners-hansen/GFC-2025-v1.13/'
          'Hansen_GFC-2025-v1.13_lossyear_10S_070W.tif')
BORDERS = 'https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_boundary_lines_land.zip'
SAND = '#d8d2b8'  # fields present in both years

# RPG crop groups by HCAT English name; anything else is grey
CROPS = [('wheat', '#cbb57a'), ('rapeseed', '#e6cf45'), ('barley', '#e9dcae'), ('maize', '#6f6a33'),
         ('beet', '#8aa0d4'), ('potato', '#a7d0dc'), ('fallow', '#b9c39a'), ('unused', '#b9c39a')]
OTHER = '#d3d0c2'


def bbox_query(url: str, cols: str, bounds) -> gpd.GeoDataFrame:
    """Rows whose bbox covering column intersects bounds; row-group statistics keep the remote read small."""
    c = duckdb.connect()
    c.sql('INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;')
    x0, y0, x1, y1 = bounds
    df = c.sql(f"SELECT {cols}, ST_AsWKB(geometry) AS wkb FROM read_parquet('{url}') "
               f'WHERE bbox.xmax > {x0} AND bbox.xmin < {x1} AND bbox.ymax > {y0} AND bbox.ymin < {y1}').df()
    return gpd.GeoDataFrame(df.drop(columns='wkb'), geometry=shapely.from_wkb(df.wkb.map(bytes)))


def rings(geoms) -> list[np.ndarray]:
    return [np.asarray(p.exterior.coords) for g in geoms for p in getattr(g, 'geoms', [g])]


def france_rpg() -> None:
    """A 15 x 2.2 km strip of the Beauce, every declared parcel coloured by its 2024 crop."""
    x, y = Transformer.from_crs(4326, 2154, always_xy=True).transform(1.60, 48.28)
    b = (x - 7500, y - 1100, x + 7500, y + 1100)
    g = bbox_query(RPG, '"hcat:name_en" AS crop', b)
    color = [next((c for k, c in CROPS if k in str(s).lower()), OTHER) for s in g.crop]
    fig = plt.figure(figsize=(14.72, 2.16))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.add_collection(PolyCollection(rings(g.geometry), facecolors=color, edgecolors=BG, linewidths=0.6))
    ax.set_xlim(b[0], b[2])
    ax.set_ylim(b[1], b[3])
    ax.set_axis_off()
    fig.savefig(DEST / 'france-rpg-2024.png', dpi=200)
    plt.close(fig)
    print(f'France RPG 2024: {len(g)} parcels')


def crop_progress() -> None:
    """NASS 2026 corn progress and condition chart, page 2 of the national chart book."""
    pix = pymupdf.open(cached('nass-crop-progress-US_2026.pdf', NASS))[1].get_pixmap(dpi=220)
    img = Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')
    w, h = img.size
    frame = (int(w * 0.049), int(h * 0.09), int(w * 0.952), int(h * 0.962))  # the chart's grey frame
    img.crop(frame).save(DEST / 'nass-corn-2026.png')


def eudr_window(lon: float = -62.248, lat: float = -17.932, half_w: int = 2400, half_h: int = 3500) -> None:
    """Q3 2020 and Q3 2025 at a Santa Cruz clearing; 2025 FTW-2E fields mostly on post-2020 forest loss in coral."""
    t = gpd.read_parquet(raster_index()).query('year == 2025')
    t = t[t.geometry.contains(shapely.Point(lon, lat))].iloc[0]
    epsg = int(t.epsg)
    x, y = Transformer.from_crs(4326, epsg, always_xy=True).transform(lon, lat)
    b = (x - half_w, y - half_h, x + half_w, y + half_h)
    to_ll = Transformer.from_crs(epsg, 4326, always_xy=True)
    ll = to_ll.transform_bounds(*b)

    def rgb(year: int) -> np.ndarray:
        bands = []
        for band in ('B04', 'B03', 'B02'):
            with rasterio.open(f'{MOSAICS}/{year}/Q3/{t.tile_key}/{band}.tif') as ds:
                bands.append(ds.read(1, window=from_bounds(*b, ds.transform)))
        return np.clip(np.clip(np.stack(bands, -1), 0, None) / 3000, 0, 1) ** 0.7

    fields = bbox_query(FTW_VECTOR.format(year=2025, zone=int(t.tile_key[:2])), 'id', ll).set_crs(4326).to_crs(epsg)
    fields = fields[fields.intersects(shapely.box(*b))]
    with rasterio.open(cached('hansen-lossyear-10S_070W.tif', HANSEN)) as ds:
        win = from_bounds(*ll, ds.transform)
        loss = ds.read(1, window=win) >= 21  # loss year 2021 or later: after the EUDR cut-off of 31 December 2020
        lt = ds.window_transform(win)
    lf = fields.to_crs(4326)
    share = [rasterize([(g, 1)], out_shape=loss.shape, transform=lt).astype(bool) for g in lf.geometry]
    after = np.array([loss[m].mean() > 0.5 if m.any() else False for m in share])
    print(f'EUDR window {t.tile_key}: {len(fields)} fields, {after.sum()} mostly on 2021+ forest loss')

    fig, axes = plt.subplots(1, 2, figsize=(4.72, 4.72 / 2 * half_h / half_w))
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0, wspace=0.05)
    extent = (b[0], b[2], b[1], b[3])
    for ax, year in zip(axes, (2020, 2025), strict=True):
        ax.imshow(rgb(year), extent=extent)
        ax.add_collection(PolyCollection(rings(fields.geometry[after]), facecolors='none', edgecolors=CORAL,
                                         linewidths=0.8))
        ax.text(0.03, 0.96, str(year), transform=ax.transAxes, va='top', fontsize=15, color=INK,
                bbox={'facecolor': BG, 'edgecolor': 'none', 'pad': 2.5})
        ax.set_xlim(b[0], b[2])
        ax.set_ylim(b[1], b[3])
        ax.set_axis_off()
    fig.savefig(DEST / 'eudr-santa-cruz.png', dpi=240, facecolor=BG)
    plt.close(fig)


def field_mosaic(year: int, bounds, res: float) -> np.ndarray:
    """FTW-2E p(field) from the 1/64 COG overviews, averaged onto a lon/lat grid."""
    w, s, e, n = bounds
    t = gpd.read_parquet(raster_index()).query('year == @year').cx[w:e, s:n]
    transform, shape = from_origin(w, n, res, res), (round((n - s) / res), round((e - w) / res))

    def one(href: str) -> np.ndarray:
        with rasterio.open(href, OVERVIEW_LEVEL=4) as ds:
            dst = np.full(shape, np.nan, np.float32)
            reproject(ds.read(1).astype(np.float32) / 255, dst, src_transform=ds.transform, src_crs=ds.crs,
                      dst_transform=transform, dst_crs='EPSG:4326', resampling=Resampling.average, dst_nodata=np.nan)
            return dst

    out = np.full(shape, np.nan, np.float32)
    with ThreadPoolExecutor(16) as ex:
        for d in ex.map(one, t.href):
            out = np.where(np.isnan(out), d, out)
    return out


def ukraine_loss(bounds=(31.8, 46.3, 39.75, 50.3), res: float = 0.004, k: int = 4) -> None:
    """Share of 2021 field area (p >= 0.5) that FTW-2E no longer detects in 2025 (p < 0.2), in ~1.5 km blocks."""
    a, b = field_mosaic(2021, bounds, res), field_mosaic(2025, bounds, res)
    h, w = (a.shape[0] // k) * k, (a.shape[1] // k) * k

    def block(m: np.ndarray) -> np.ndarray:
        return m[:h, :w].reshape(h // k, k, w // k, k).mean(axis=(1, 3))

    had = block((a >= 0.5).astype(np.float32))
    lost = block(((a >= 0.5) & (b < 0.2)).astype(np.float32)) / np.maximum(had, 1e-6)
    img = np.ones((*had.shape, 3)) * np.array(plt.matplotlib.colors.to_rgb(BG))
    img[had > 0.05] = plt.matplotlib.colors.to_rgb(SAND)
    # stricter than 0.5: the 2025 run is a little sparser everywhere
    img[(had > 0.05) & (lost > 0.6)] = plt.matplotlib.colors.to_rgb(CORAL)
    print(f'Ukraine: {np.mean(lost[had > 0.05] > 0.6):.1%} of blocks with 2021 fields lost over 60% of them by 2025')

    w0, s0, e0, n0 = bounds
    aspect = 1 / np.cos(np.radians((s0 + n0) / 2))
    fig = plt.figure(figsize=(4.72, 4.72 * (n0 - s0) * aspect / (e0 - w0)))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.imshow(img, extent=(w0, w0 + w * res, n0 - h * res, n0), interpolation='nearest')
    gpd.read_file(cached('ne_10m_boundary_lines.zip', BORDERS)).cx[w0:e0, s0:n0].plot(ax=ax, color=INK, lw=0.6)
    for name, lon, lat in (('Kharkiv', 36.23, 49.99), ('Dnipro', 35.05, 48.46), ('Zaporizhzhia', 35.14, 47.84),
                           ('Donetsk', 37.80, 48.00), ('Kherson', 32.62, 46.64)):
        ax.plot(lon, lat, 'o', ms=4.5, color=INK)
        ax.text(lon + 0.1, lat + 0.06, name, fontsize=13, color=INK)
    ax.set_xlim(w0, e0)
    ax.set_ylim(s0, n0)
    ax.set_aspect(aspect)
    ax.set_axis_off()
    fig.savefig(DEST / 'ukraine-field-loss.png', dpi=240, facecolor=BG)
    plt.close(fig)


if __name__ == '__main__':
    setup_style()
    DEST.mkdir(parents=True, exist_ok=True)
    france_rpg()
    crop_progress()
    eudr_window()
    ukraine_loss()
