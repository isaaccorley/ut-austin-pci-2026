"""Evaluation schematics: random vs regional folds, CoordBench cell sizes, Chunk Penalization weights.

Fold maps use the published FTW-2E tile centres as example locations; fold assignments are illustrative.
uv run --no-project --with geopandas --with pyarrow --with matplotlib python scripts/figures/eval_figs.py
"""

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import box

from common import (ACCENT, BG, CORAL, EQUAL_EARTH, INK, LAND, MUTED, OUT, RULE, land, raster_index,
                    setup_style)

DEST = OUT / 'eval'
TRAIN = '#9a9a9a'
LAT_MIN, LAT_MAX = -56, 74
RNG = np.random.default_rng(7)


def map_axes(ax, world):
    lo = gpd.GeoSeries.from_xy([-180, 180], [LAT_MIN, LAT_MAX], crs='EPSG:4326').to_crs(EQUAL_EARTH)
    ax.set_xlim(world.total_bounds[0], world.total_bounds[2])
    ax.set_ylim(lo.y.min(), lo.y.max())
    ax.set_axis_off()
    world.plot(ax=ax, color=LAND, linewidth=0)


def centres() -> gpd.GeoDataFrame:
    t = gpd.read_parquet(raster_index(), columns=['year', 'tile_key', 'geometry'])
    t = t[t.year == 2025]
    c = t.geometry.centroid  # lon/lat centroids are fine for 100 km tiles
    return gpd.GeoDataFrame(geometry=gpd.points_from_xy(c.x, c.y), crs='EPSG:4326')


def cell_folds(pts: gpd.GeoDataFrame, deg: float, k: int = 5) -> np.ndarray:
    """Assign each angular cell to one of k folds at random; points inherit their cell's fold."""
    ix = np.floor(pts.geometry.x / deg).astype(int) * 1000 + np.floor(pts.geometry.y / deg).astype(int)
    cells = np.unique(ix)
    fold = dict(zip(cells, RNG.integers(0, k, len(cells)), strict=True))
    return np.array([fold[c] for c in ix])


def folds(world, pts) -> None:
    """Same locations, one held-out fold: random assignment vs 20° regional cells."""
    fig, axes = plt.subplots(1, 2, figsize=(14.7, 3.9))
    fig.subplots_adjust(left=0, right=1, top=0.9, bottom=0, wspace=0.03)
    for ax, (title, f) in zip(axes, [('Random folds', RNG.integers(0, 5, len(pts))),
                                     ('Regional folds · 20° cells', cell_folds(pts, 20))], strict=True):
        map_axes(ax, world)
        p = pts.to_crs(EQUAL_EARTH)
        p[f != 0].plot(ax=ax, color=TRAIN, markersize=3.2, linewidth=0)
        p[f == 0].plot(ax=ax, color=CORAL, markersize=5, linewidth=0)
        ax.set_title(title, fontsize=19, loc='left', pad=8)
    fig.savefig(DEST / 'folds-random-vs-regional.png', dpi=200)
    regional = axes[1].get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    fig.savefig(DEST / 'folds-regional.png', dpi=200, bbox_inches=regional)  # untitled panel for the closing slide
    plt.close(fig)


def coordbench_cells(world, pts) -> None:
    """The four regional cell sizes; coral cells form one held-out fold."""
    fig, axes = plt.subplots(2, 2, figsize=(9.2, 5.2))
    fig.subplots_adjust(left=0, right=1, top=0.92, bottom=0, wspace=0.03, hspace=0.2)
    land_union = world.to_crs('EPSG:4326').union_all()
    for ax, deg in zip(axes.flat, [2, 10, 20, 40], strict=True):
        map_axes(ax, world)
        xs, ys = np.arange(-180, 180, deg), np.arange(-60, 90, deg)
        cells = gpd.GeoDataFrame(geometry=[box(x, y, x + deg, y + deg) for x in xs for y in ys], crs='EPSG:4326')
        cells = cells[cells.intersects(land_union)].copy()
        cells['fold'] = RNG.integers(0, 5, len(cells))
        cells = cells.to_crs(EQUAL_EARTH)
        cells[cells.fold == 0].plot(ax=ax, color=CORAL, alpha=0.85, linewidth=0)
        cells.boundary.plot(ax=ax, color=BG, linewidth=0.25 if deg < 10 else 0.7)
        ax.set_title(f'{deg}° cells', fontsize=17, loc='left', pad=4)
    fig.savefig(DEST / 'coordbench-cells.png', dpi=200)
    plt.close(fig)


def chunk_penalty() -> None:
    """Relative ridge penalty per training chunk: hard truncation vs geometric Chunk Penalization."""
    chunks = ['0–63', '64–127', '128–255', '256–511', '512–1k', '1k–2k', '2k–3k']
    j = np.arange(len(chunks))
    fig, axes = plt.subplots(1, 2, figsize=(13.4, 4.6), sharey=True)
    fig.subplots_adjust(left=0.06, right=0.99, top=0.86, bottom=0.2, wspace=0.08)
    keep = j <= 2
    ax = axes[0]
    ax.bar(j[keep], np.ones(keep.sum()), color=INK, width=0.7)
    for x in j[~keep]:
        ax.bar(x, 64, color='none', edgecolor=RULE, hatch='///', width=0.7, linewidth=0)
    ax.text(4.5, 8, 'dropped', ha='center', va='center', fontsize=16, color=MUTED)
    ax.set_title('Prefix truncation · keep 256 features', loc='left', fontsize=18, pad=10)
    ax = axes[1]
    ax.bar(j, 2.0 ** j, color=INK, width=0.7)
    ax.set_title(r'Chunk Penalization · keep all 3,072, penalty $\times\,\gamma^{\,j}$', loc='left', fontsize=18, pad=10)
    for ax in axes:
        ax.set_yscale('log', base=2)
        ax.set_ylim(0.6, 90)
        ax.set_xticks(j, chunks, fontsize=13, rotation=0)
        ax.tick_params(axis='x', length=0, pad=6)
        ax.spines['bottom'].set_color(RULE)
        ax.set_xlabel('feature chunk (dimensions)', fontsize=14, color=MUTED)
    axes[0].set_yticks([1, 4, 16, 64], ['1×', '4×', '16×', '64×'], fontsize=13)
    axes[0].set_ylabel('ridge penalty, relative', fontsize=14, color=MUTED)
    fig.savefig(DEST / 'chunk-penalty.svg')
    plt.close(fig)


if __name__ == '__main__':
    setup_style()
    DEST.mkdir(parents=True, exist_ok=True)
    world = land().to_crs(EQUAL_EARTH)
    world = world[world.geometry.bounds.maxy > -6.0e6]
    pts = centres()
    folds(world, pts)
    coordbench_cells(world, pts)
    chunk_penalty()
