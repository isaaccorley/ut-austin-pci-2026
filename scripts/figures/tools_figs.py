"""Geometry-tool figures: Rust vs Python coverage simplify per tile, and contourrs on one FTW-2E window.

The per-tile numbers in data/coverage_simplify_tiles.csv are global-ftw-2e rust/coverage-simplify/RESULTS.md.
uv run --no-project --with geopandas --with matplotlib --with rasterio --with pillow --with scipy --with contourrs==0.8.6 python scripts/figures/tools_figs.py
"""

import csv

import contourrs
import matplotlib.pyplot as plt
import numpy as np
import rasterio.features
import shapely
from matplotlib.collections import PolyCollection
from scipy import ndimage

from common import BG, INK, MUTED, OUT, ROOT, RULE, setup_style
from ftw_inputs import EPSG, MOSAICS, SCORES, TILE, YEAR, read, window_bounds

DEST = OUT / 'tools'
PYTHON = '#b9b7a8'  # reference implementation
OUTLINE = '#8aa0d4'  # as in the gallery stills


def coverage_tiles() -> None:
    """CPU time on one core and peak memory per tile: Python/GEOS reference vs the Rust port."""
    with open(ROOT / 'scripts' / 'figures' / 'data' / 'coverage_simplify_tiles.csv') as f:
        rows = list(csv.DictReader(f))
    labels = [f"{r['tile'][:5]} · {int(r['parcels']) / 1000:.0f}k parcels" for r in rows]
    y = np.arange(len(rows))[::-1]
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.3), sharey=True)
    fig.subplots_adjust(left=0.25, right=0.97, top=0.8, bottom=0.04, wspace=0.12)
    for ax, (py, rs), title, unit in zip(axes, [('python_s', 'rust1_s'), ('python_gib', 'rust1_gib')],
                                         ['CPU time per tile, one core', 'Peak memory per tile'], ['s', 'GiB'],
                                         strict=True):
        p = np.array([float(r[py]) for r in rows])
        q = np.array([float(r[rs]) for r in rows])
        ax.barh(y + 0.19, p, height=0.36, color=PYTHON)
        ax.barh(y - 0.19, q, height=0.36, color=INK)
        for yy, a, b in zip(y, p, q, strict=True):
            fmt = '{:.0f} ' if unit == 's' else '{:.1f} '
            ax.text(a, yy + 0.19, ' ' + fmt.format(a) + unit, va='center', fontsize=14, color=MUTED)
            ax.text(b, yy - 0.19, ' ' + fmt.format(b) + unit + f'  ({a / b:.1f}× less)', va='center', fontsize=14)
        ax.set_xlim(0, p.max() * 1.45)
        ax.set_title(title, loc='left', fontsize=18, pad=10)
        ax.set_xticks([])
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_color(RULE)
        ax.tick_params(axis='y', length=0, pad=8)
    axes[0].set_yticks(y, labels, fontsize=15)
    fig.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=PYTHON), plt.Rectangle((0, 0), 1, 1, color=INK)],
               labels=['Python reference (Shapely/GEOS)', 'Rust port, 1 thread'], loc='upper left',
               bbox_to_anchor=(0.25, 1.0), ncol=2, frameon=False, fontsize=15, handlelength=1.2)
    fig.savefig(DEST / 'coverage-simplify-tiles.svg')
    plt.close(fig)


def contourrs_window() -> None:
    """Field interiors on one 4 km window, labelled by connected components and polygonized by contourrs."""
    b = window_bounds()
    rgb = np.stack([read(f'{MOSAICS}/{YEAR}/Q1/{TILE}/{band}.tif', b) for band in ('B04', 'B03', 'B02')], -1)
    rgb = np.clip(np.clip(rgb, 0, None) / 3000, 0, 1) ** 0.7
    cog = f'{SCORES}/{YEAR}/zone={TILE[:2]}/gzd={TILE[:3]}/{TILE}/{TILE}.tif'
    pf, pb = (read(cog, b, band).astype(np.float32) / 255 for band in (1, 2))
    labels, n = ndimage.label((pf >= 0.5) & (pb < 0.5))  # four-connected field interiors
    sizes = np.bincount(labels.ravel())
    labels[sizes[labels] < 64] = 0  # drop specks under 400 m2
    labels = np.ascontiguousarray(labels.astype(np.int32))
    transform = rasterio.transform.from_bounds(*b, labels.shape[1], labels.shape[0])

    polys = contourrs.shapes(labels, mask=labels > 0, connectivity=4, transform=transform)
    ref = list(rasterio.features.shapes(labels, mask=labels > 0, connectivity=4, transform=transform))
    same = {(v, shapely.to_wkb(shapely.geometry.shape(g))) for g, v in polys} == \
           {(v, shapely.to_wkb(shapely.geometry.shape(g))) for g, v in ref}  # same polygons, emitted in another order
    print(f'contourrs window: {len(polys)} polygons, EPSG:{EPSG}, identical WKB to rasterio: {same}')

    rng = np.random.default_rng(3)
    colors = np.vstack([[0.957, 0.957, 0.922], rng.uniform(0.35, 0.92, (labels.max(), 3))])
    fig, axes = plt.subplots(1, 3, figsize=(10.4, 3.9))
    fig.subplots_adjust(left=0, right=1, top=0.88, bottom=0, wspace=0.04)
    extent = (b[0], b[2], b[1], b[3])
    panels = [('p(field), 2025', None), ('Labelled field interiors', None), (f'{len(polys)} polygons', None)]
    axes[0].imshow(pf, cmap='Greens', vmin=0, vmax=1, extent=extent)
    axes[1].imshow(colors[labels], extent=extent, interpolation='nearest')
    axes[2].imshow(rgb, extent=extent)
    rings = [np.asarray(ring) for g, _ in polys for ring in g['coordinates']]
    axes[2].add_collection(PolyCollection(rings, facecolors='none', edgecolors=OUTLINE, linewidths=1.0))
    for ax, (title, _) in zip(axes, panels, strict=True):
        ax.set_title(title, loc='left', fontsize=17, pad=6)
        ax.set_axis_off()
        ax.set_xlim(b[0], b[2])
        ax.set_ylim(b[1], b[3])
    fig.savefig(DEST / 'contourrs-iowa.png', dpi=200, facecolor=BG)
    plt.close(fig)


if __name__ == '__main__':
    setup_style()
    DEST.mkdir(parents=True, exist_ok=True)
    coverage_tiles()
    contourrs_window()
