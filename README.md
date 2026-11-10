# UT Austin · Causal ML & EO for Social Sci

Isaac Corley, November 10, 2026. Guest lecture for Connor T. Jerzak's [Causal ML & EO for Social Sci](https://connorjerzak.com/pci-course/) at UT Austin. Research talk on Fields of the World, spatial generalization and MIND. Includes two live demos, six imagery change examples, and an introduction to location encoders and published satellite embeddings.

[**Present the slides**](https://isaac.earth/ut-austin-pci-2026/) · [Static mode](https://isaac.earth/ut-austin-pci-2026/?static=1)

Adapted from the [October 30 GIScience Colloquium talk](https://github.com/isaaccorley/ut-austin-giscience-2026), with additional change clips from the [CNG talk](https://github.com/isaaccorley/cng-mapping-digital-public-goods) and introductory slides for this course.

## Edit and present

The editable source is `index.qmd`. The title slide uses the FTW × OlmoEarth regional-PCA map near Ames, Iowa, with Source Serif 4 and JetBrains Mono typography matching the LinkedIn graphic in `assets/social/`. Speaker notes are omitted from the source and published deck. Reveal.js theme layers live in `theme/` (SCSS, loaded in the order listed in the `index.qmd` front matter) together with `theme/animations.html`, which drives video playback and the live demo iframes. The deck uses Quarto/Reveal.js at 1600 × 900, with scientific figures and local media on the Taylor Geospatial ivory background (`#f4f4eb`).

Install [Quarto](https://quarto.org/docs/get-started/) (tested with 1.8.27 and 1.10.19), then:

```sh
quarto preview index.qmd
```

Arrow keys navigate. Video controls are available; poster images provide a fallback. Append `?static=1` to disable automatic video playback and the live demos.

Two slides embed live web apps in iframes: the [Global FTW 2nd Edition preview](https://research.taylorgeospatial.org/global-ftw-2e/) (after the gallery) and [FTW × OlmoEarth](https://research.taylorgeospatial.org/ftw-olmoearth/) (after the distribution slide). They load when you arrive on the slide, with one slide of lookahead, and need internet; offline or with `?static=1` the slide shows a poster still instead. The map keeps keyboard focus after you interact with it, so click the slide title before pressing arrow keys.

Build an offline-capable local preview:

```sh
python3 scripts/build_site.py
python3 -m http.server 8000 --directory _site
```

Open http://localhost:8000. Serving the rendered `_site` folder requires only Python. External source links need internet access; figures, fonts, videos and Reveal.js are bundled.

Link previews use `assets/social/title-slide-preview.png`, configured with Open Graph and Twitter card metadata in `theme/social-meta.html`.

## Deployment

Pushes to `main` run `.github/workflows/deploy.yml`, which renders the deck with Quarto 1.10.19 and publishes `_site` to GitHub Pages at <https://isaac.earth/ut-austin-pci-2026/>. The workflow can also be started by hand from the Actions tab.

## Contents and status

- Slides 1–28: introduction and industry/academic career path, field-boundary mapping, globe-to-field zoom clip, live FTW-2E viewer, imagery changes in Saudi Arabia, Brazil, Uganda, China and Azerbaijan, scale of the nine-year run, who has field data and who uses it (France RPG, USDA Crop Progress, EUDR, war-time field loss in Ukraine), benchmark labels and the FTW v2 field-data catalog, the PRUE model comparison, annual global pipeline, compute timeline and AWS cost, geometry processing (Rust tools, contourrs, coarsen), live crop-type demo, preview limitations and geographic evaluation.
- Slides 29–31: original paper figures from SatCLIP (pretraining and downstream prediction), AlphaEarth (annual feature maps), and TESSERA (fitting a task model to published embeddings).
- Slides 32–44: MIND, nested features, Chunk Penalization, CoordBench, diagnostics, conclusions and links with QR codes.

The five added change clips play on arrival and loop while their slide is visible; there is no automatic slide advance. Static mode and print use the original poster images. Dates and quarters are retained from the CNG captures. The three introductory paper-figure slides contain only a title, the figure and a source citation.

## Figures

Data figures are generated from published sources by the scripts in `scripts/figures/` (downloads are cached in the ignored `.cache/`):

```sh
uv run --no-project --with geopandas --with pyarrow --with matplotlib python scripts/figures/ftw_scale.py
uv run --no-project --with geopandas --with pyarrow --with matplotlib python scripts/figures/eval_figs.py
uv run --no-project --with geopandas --with pyarrow --with matplotlib --with rasterio --with pillow python scripts/figures/ftw_inputs.py
uv run --no-project --with geopandas --with matplotlib --with pymupdf --with pillow --with playwright python scripts/figures/stills.py
uv run --no-project --with geopandas --with matplotlib --with rasterio --with pillow --with scipy --with contourrs==0.8.6 python scripts/figures/tools_figs.py
uv run --no-project --with geopandas --with matplotlib python scripts/figures/career.py
uv run --no-project --with geopandas --with pyarrow --with matplotlib --with rasterio --with duckdb --with pymupdf --with pillow python scripts/figures/uses_figs.py
```

`ftw_scale.py` writes `assets/scale/` from the FTW-2E raster and vector indexes on Source Cooperative and `scripts/figures/data/inference_windows.csv`. `eval_figs.py` writes `assets/eval/`. `ftw_inputs.py` reads one 4 km window of the 2025 quarterly mosaics and the published probability COG into `assets/ftw-inputs/`. See `ASSETS.md` for provenance.

Research results and project statistics are retained from the October 30, 2026 talk. The added CNG captures retain their October 8 provenance; the introductory figures retain their original labels and link to the SatCLIP, AlphaEarth and TESSERA papers. See `ASSETS.md` for figure provenance. Generated `_site` files and build caches are excluded from Git.
