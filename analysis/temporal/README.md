# Temporal and multi-value analysis

Entry point, from the repository root: `pnpm analysis:temporal` (about 6 minutes on 8 cores; see the top-level README for setup). It runs `run_all.py`, which writes to `results/temporal/`:

- `<section>.json`: raw numbers for sections AB, C (also H), D, E, F, G, X1, X3, X4, X5
- `tables_<section>.md` and `tables_<section>.json`: every table (the website renders the JSON)
- `figures/*.webp`

Run selected sections with `pnpm py analysis/temporal/run_all.py D X4`.

Files: `noises.py` (every sampler as `f(x, y, n, D)`, self-checks, the STBN download), `integrands.py` (test functions with known means), `run_all.py` (sections A to H), `extras.py` (sections X1 to X5; `pnpm py analysis/temporal/extras.py vectors` rewrites `src/noise/temporal-vectors.json` and `src/noise/vc64.js` so the JavaScript modules are checked against these implementations).

Terms: `D` in the code is the number of values per pixel (1, 2 or 4; printed as 1-value, 2-value, 4-value); `n` or `N` is the frame index or the number of frames accumulated, with one sample of each value per pixel per frame.

Third-party textures: the FAST atlas is read from `textures/fast/`. NVIDIA STBN is under a non-commercial licence, so it is not in the repository; it is downloaded on first run from a pinned commit and checked against a pinned SHA-256 (see `textures/stbn/SOURCE.md`). The 64×64 void-and-cluster texture is generated on first run. Both are cached in `analysis/temporal/cache/` (git-ignored).

Everything is a numpy model of the shader arithmetic: integer paths wrap like uint32, float paths use float32 for every operation in source order. Nothing here is rendered on a GPU; the in-engine measurements are in `analysis/gpu/`.

The readings of each section are on the website's Results page (source: `site/src/temporal-readings.json`).
