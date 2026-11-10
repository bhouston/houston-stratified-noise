# Analytic R4 comparison and component ablation

Entry point, from the repository root: `pnpm analysis:r4-ablation` (about 4 minutes on 8 cores). It runs `run.py`, which uses the temporal analysis harness in `analysis/temporal/` and writes to `results/r4-ablation/`:

- `R4.json`, `tables_R4.md`, `tables_R4.json`: part 1, hash-free "analytic R4" samplers against HSN, hash + R_d and the textures
- `ABL.json`, `tables_ABL.md`, `tables_ABL.json`: part 2, each part of HSN switched off in turn
- `figures/*.webp`

Run one part with `pnpm py analysis/r4-ablation/run.py R4` or `ABL`. `pnpm py analysis/r4-ablation/run.py vectors` rewrites `src/noise/r4-vectors.json`, which checks `src/noise/analytic-r4.js` against the samplers defined here.

Part 1 has two families of per-value-lattice rows: `(ii)`, with this study's own direction pairs, and `F`, with exactly the direction pairs measured in-engine (`analysis/gpu/harness/MeasureAnalyticR4.js`). `E` is the in-engine single lattice in uint32 fixed point; the script asserts its derived constants equal the in-engine ones. Use E and F when comparing CPU and in-engine results.

All tests are a static flat field, which does not penalise lattice structure; the in-engine measurements in `analysis/gpu/` do. The readings are on the website's Results page (source: `site/src/r4-readings.json`).
