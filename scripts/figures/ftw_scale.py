"""FTW-2E scale figures from the published Source Cooperative indexes and the r1 run log.

uv run --no-project --with geopandas --with pyarrow --with matplotlib python scripts/figures/ftw_scale.py
"""

import csv
from datetime import datetime

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch

from common import (ACCENT, BG, CORAL, EQUAL_EARTH, FIELD, INK, LAND, MUTED, OUT, ROOT, RULE,
                    land, raster_index, setup_style, vector_index)

DEST = OUT / 'scale'
LAT_MIN, LAT_MAX = -56, 74


def world_axes(width_in: float, world: gpd.GeoDataFrame):
    """Equal Earth axes cropped to the populated latitudes, sized to the data aspect."""
    lo = gpd.GeoSeries.from_xy([-180, 180], [LAT_MIN, LAT_MAX], crs='EPSG:4326').to_crs(EQUAL_EARTH)
    x0, x1 = world.total_bounds[0], world.total_bounds[2]
    y0, y1 = lo.y.min(), lo.y.max()
    fig = plt.figure(figsize=(width_in, width_in * (y1 - y0) / (x1 - x0)))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_axis_off()
    world.plot(ax=ax, color=LAND, linewidth=0)
    return fig, ax


def tiles(year: int) -> gpd.GeoDataFrame:
    t = gpd.read_parquet(raster_index())
    return t[t.year == year].to_crs(EQUAL_EARTH)


def legend_bar(fig, colors, labels, title, box=(0.035, 0.12, 0.21, 0.028)):
    """Discrete colour key in the South Pacific."""
    ax = fig.add_axes(box)
    ax.imshow([np.arange(len(colors))], cmap=ListedColormap(colors), aspect='auto')
    ax.set_yticks([])
    ax.set_xticks(np.arange(len(colors)), labels, fontsize=12, color=MUTED)
    ax.tick_params(length=0, pad=4)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(title, fontsize=13, loc='left', color=INK, pad=6)


def tile_map(world: gpd.GeoDataFrame) -> None:
    """Every processed 100 km tile, coloured by its 2025 predicted field share."""
    t = tiles(2025)
    edges = [0, 0.01, 0.05, 0.15, 0.35, 1.01]
    fig, ax = world_axes(11.1, world)
    t.plot(ax=ax, column='field_frac', cmap=ListedColormap(FIELD), norm=BoundaryNorm(edges, len(FIELD)),
           edgecolor=BG, linewidth=0.12)
    legend_bar(fig, FIELD, ['<1%', '1–5', '5–15', '15–35', '>35%'], 'Predicted field share per tile, 2025')
    fig.savefig(DEST / 'ftw-tiles-2025.png', dpi=200)
    plt.close(fig)
    print('tiles', len(t))


def ratio_map(world: gpd.GeoDataFrame) -> None:
    """Tile field share 2024 / 2023; tiles under 2% field share in 2023 stay neutral."""
    a, b = tiles(2023).set_index('tile_key'), tiles(2024).set_index('tile_key')
    t = b[['geometry']].join(a.field_frac.rename('f23')).join(b.field_frac.rename('f24'))
    t['ratio'] = t.f24 / t.f23
    edges = [0, 0.7, 0.85, 0.95, 1.05, 1.15, 1.3, 99]
    colors = ['#c8321a', CORAL, '#ffb09c', '#dedcce', '#c3d1ec', ACCENT, '#4f6fae']
    fig, ax = world_axes(9.6, world)
    t[t.f23 < 0.02].plot(ax=ax, color='#cfcdbf', edgecolor=BG, linewidth=0.1)
    t[t.f23 >= 0.02].plot(ax=ax, column='ratio', cmap=ListedColormap(colors),
                          norm=BoundaryNorm(edges, len(colors)), edgecolor=BG, linewidth=0.1)
    legend_bar(fig, colors, ['<0.7', '', '', '1', '', '', '>1.3'], 'Field share 2024 / 2023',
               box=(0.035, 0.12, 0.25, 0.04))
    fig.savefig(DEST / 'ftw-ratio-2024-2023.png', dpi=200)
    plt.close(fig)
    print('ratio tiles', int((t.f23 >= 0.02).sum()))


def fields_per_year() -> None:
    """Published polygon counts by year; 2017 and 2024 are the years the preview flags."""
    v = pd.read_parquet(vector_index(), columns=['year', 'n_parcels'])
    n = v.groupby('year').n_parcels.sum() / 1e6
    flagged = {2017, 2024}
    fig, ax = plt.subplots(figsize=(5.4, 6.0))
    fig.subplots_adjust(left=0.03, right=0.99, top=0.8, bottom=0.08)
    colors = [CORAL if y in flagged else INK for y in n.index]
    ax.bar(n.index, n.values, width=0.74, color=colors)
    for y, m in n.items():
        ax.text(y, m + 2, f'{m:.0f}', ha='center', va='bottom', fontsize=17,
                color=CORAL if y in flagged else INK)
    ax.set_ylim(0, 162)
    ax.set_xticks(n.index, [f"'{y % 100:02d}" for y in n.index], fontsize=17)
    ax.set_yticks([])
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color(RULE)
    ax.tick_params(axis='x', length=0, pad=6)
    fig.text(0.03, 0.955, 'Field polygons per year (millions)', fontsize=20, va='top')
    fig.text(0.03, 0.895, f'{n.sum() / 1e3:.2f} B in total', fontsize=17, color=MUTED, va='top')
    ax.legend(handles=[Patch(color=CORAL, label='under-detection flagged')], loc='lower left',
              bbox_to_anchor=(0, 1.0), frameon=False, fontsize=16, handlelength=1, borderaxespad=0.2)
    fig.savefig(DEST / 'ftw-fields-per-year.svg')
    plt.close(fig)
    print('fields', n.round(1).to_dict(), 'total', round(n.sum(), 1))


def inference_gantt() -> None:
    """GPU inference windows of run r1, one bar per year in run order."""
    rows = list(csv.DictReader(open(ROOT / 'scripts' / 'figures' / 'data' / 'inference_windows.csv')))
    t0 = min(datetime.fromisoformat(r['start']) for r in rows)
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    fig.subplots_adjust(left=0.08, right=0.98, top=0.95, bottom=0.13)
    for i, r in enumerate(rows):
        s = (datetime.fromisoformat(r['start']) - t0).total_seconds() / 3600
        e = (datetime.fromisoformat(r['end']) - t0).total_seconds() / 3600
        ax.barh(i, e - s, left=s, height=0.68, color=CORAL if r['where'] == 'aws' else ACCENT)
        ax.text(s - 0.6, i, r['year'], ha='right', va='center', fontsize=17)
    end = max((datetime.fromisoformat(r['end']) - t0).total_seconds() / 3600 for r in rows)
    ax.axvline(end, color=INK, linewidth=1, linestyle=(0, (3, 3)))
    ax.text(end - 0.5, -0.25, f'nine years: {end:.1f} h', ha='right', va='center', fontsize=17)
    ax.set_ylim(len(rows) - 0.4, -0.6)
    ax.set_xlim(-5, 42)
    ax.set_yticks([])
    ax.spines['left'].set_visible(False)
    ax.set_xticks(range(0, 41, 8))
    ax.set_xlabel('hours since the first tile', fontsize=16, color=MUTED)
    ax.tick_params(axis='x', labelsize=16)
    ax.legend(handles=[Patch(color=ACCENT, label='20 GPUs on RAILS (12 H100, 8 A100)'),
                       Patch(color=CORAL, label='16 H100 on AWS (2 × p5.48xlarge)')],
              loc='lower left', frameon=False, fontsize=15, handlelength=1)
    fig.savefig(DEST / 'ftw-inference-gantt.svg')
    plt.close(fig)
    print('inference span h', round(end, 2))


if __name__ == '__main__':
    setup_style()
    DEST.mkdir(parents=True, exist_ok=True)
    world = land().to_crs(EQUAL_EARTH)
    world = world[world.geometry.bounds.maxy > -6.0e6]  # drop Antarctica
    tile_map(world)
    ratio_map(world)
    fields_per_year()
    inference_gantt()
