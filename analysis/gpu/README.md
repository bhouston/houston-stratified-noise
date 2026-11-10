# In-engine GPU measurements

Real-time VXGI, denoised SSR and a light map bake in three.js, measured with linear float readback on a hardware WebGPU adapter.

**A real hardware WebGPU adapter is required.** The driver aborts if the adapter is a fallback or software adapter (SwiftShader, llvmpipe, lavapipe). The published numbers came from an Apple M3 (adapter vendor `apple`, architecture `metal-3`, `isFallbackAdapter: false`), macOS 27.2, Google Chrome 157.0.8103.39 headless, Puppeteer 25.16. The adapter is logged in every per-run JSON in `results/gpu/runs/`.

## What is committed

| Path | Contents |
| --- | --- |
| `harness/` | The measurement pages and samplers that are copied into the three.js checkouts |
| `patches/` | `base.diff`, `head.diff`, `bake.diff`: the edits to each checkout's tracked files (a `?noise=` switch chosen at shader build time; the default path is each commit's unmodified code) |
| `run.mjs`, `jobs-*.json` | Puppeteer driver and job lists |
| `analyze_realtime.py`, `analyze_bake.py`, `bake_sensitivity.py` | Metrics from the harness output → `results/gpu/*.json` |
| `make_crops.py`, `crops/` | The small 8-bit image crops the figures show, cut from the harness output |
| `figure.py`, `figure_variants.py` | The two figures → `results/gpu/figures/` |
| `results/gpu/realtime_metrics.json`, `bake_metrics.json`, `bake_sensitivity.json` | The numbers behind every table |
| `results/gpu/runs/` | Per-run JSON: job, adapter, Chrome version, statistics |

The harness's float32 images (about 1.1 GB) are not committed.

## Regenerate the figures (no GPU needed)

```sh
pnpm analysis:gpu
```

This runs `figure.py` and `figure_variants.py` from the committed metrics JSON and `crops/`. Regenerating the crops or the metrics needs the harness output (below).

## Rerun the measurements

1. Check out three.js three times (worktrees are convenient):
   - **base**: `3f7edc3d75e0`, the merge base of mrdoob/three.js#35429 with `dev`
   - **head**: `34137c3756fa`, the head of mrdoob/three.js#35429
   - **bake**: `eb7187278b74` on `bhouston/three.js`, branch `ign-adoption`. The light map baker (`examples/jsm/lighting/vxgi/VXGIIrradiance.js`) was removed upstream, so it exists at neither the upstream base nor head.
2. Apply the patches and copy the harness files:
   - base: `git apply patches/base.diff`; copy `harness/measure_common.js`, `measure_vxgi.html`, `measure_ssr.html` to `examples/` and `harness/MeasureWhiteNoise.js` to `examples/jsm/tsl/utils/`
   - head: `git apply patches/head.diff`; copy the same three files to `examples/` and `MeasureWhiteNoise.js`, `MeasureVariants.js`, `MeasureVoidCluster.js`, `MeasureAnalyticR4.js`, `MeasureRNoiseR4.js` to `examples/jsm/tsl/utils/`
   - bake: `git apply patches/bake.diff`; copy `measure_common.js` and `measure_bake.html` to `examples/` and `MeasureWhiteNoise.js` to `examples/jsm/tsl/utils/`

   The pages import `src/` directly; nothing under `build/` is generated.
3. Serve each checkout from its root: `python3 -m http.server 8131` (base), `8132` (head), `8133` (bake).
4. Run the driver from this repository's root. It needs Puppeteer (not a dependency of this repository; install it where you run the driver) and drives the installed Google Chrome with `--enable-unsafe-webgpu --use-angle=metal --disable-frame-rate-limit --disable-gpu-vsync`; edit `executablePath` and the ANGLE flag in `run.mjs` for another platform.

   ```sh
   node analysis/gpu/run.mjs analysis/gpu/jobs-realtime.json   # VXGI and SSR, white references and three runs per sampler
   node analysis/gpu/run.mjs analysis/gpu/jobs-vc.json         # variant D
   node analysis/gpu/run.mjs analysis/gpu/jobs-bake.json       # light map bake
   node analysis/gpu/run.mjs analysis/gpu/jobs-fps.json        # throughput
   node analysis/gpu/run.mjs analysis/gpu/jobs-fps-vxgi.json   # throughput, VXGI again (the first VXGI batch was disturbed by other GPU load)
   node analysis/gpu/run.mjs analysis/gpu/jobs-vc-fps.json     # throughput, variant D with an in-session control
   node analysis/gpu/run.mjs analysis/gpu/jobs-r4.json         # variants E and F (analytic lattices)
   node analysis/gpu/run.mjs analysis/gpu/jobs-r4-fps.json
   node analysis/gpu/run.mjs analysis/gpu/jobs-g.json          # variant G (the RNoise.js of bhouston/three.js#42)
   node analysis/gpu/run.mjs analysis/gpu/jobs-g-fps.json
   ```

   `jobs-raw.json` is the pre-TRAA white reference attempt described under Limits on the Results page (kept, unused); `jobs-stat.json` is a stationarity check with different warm-up lengths. Output goes to `analysis/gpu/raw/` (git-ignored), or to `$GPU_RAW`.
5. Compute metrics, crops and figures:

   ```sh
   pnpm py analysis/gpu/analyze_realtime.py
   pnpm py analysis/gpu/analyze_bake.py
   pnpm py analysis/gpu/bake_sensitivity.py
   pnpm py analysis/gpu/make_crops.py
   pnpm analysis:gpu
   ```

   Copy the per-run `*.json` files from `raw/` to `results/gpu/runs/` to publish the adapter information with the numbers.

Throughput is measured as required for sustained rendering: vsync and the frame-rate limit disabled, 60 warm-up frames, then 5 seconds counting GPU-completed frames (`queue.onSubmittedWorkDone`), samplers run sequentially, no per-frame timing.

The method, the tables and their limits are on the website's Results page (source: `site/src/gpu-readings.json`). In short: the bias metric uses white noise through the same TRAA and denoiser as its reference, which may favour the plain hash in the bias ranking; there is one static scene and camera per effect and one GPU; fps was measured on a GPU shared with other work.
