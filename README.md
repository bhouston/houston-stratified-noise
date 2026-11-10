# Houston Stratified Noise

Houston Stratified Noise (HSN) is a screen-space sampling noise for real-time rendering that needs no texture and no precomputation. It is meant for downloadable, fast-starting 3D graphics on the web, where a sampler has to be texture-free (nothing to download) and precomputation-free (nothing to generate at startup).

It gives every aligned 8×8 tile of pixels the 64 values k/64 in a scrambled Bayer order, rotates each tile by a hashed phase, and steps every value by an integer Weyl sequence each frame, with a different step for each value per pixel. It costs four integer hashes (about 100 integer operations) per value.

- Blog post: https://ben3d.ca/blog/houston-stratified-noise
- Used in Three.js in pull request https://github.com/mrdoob/three.js/pull/35429 (`examples/jsm/tsl/utils/HierarchicalHashedWeyl.js`)
- Site with every figure, table and an interactive explorer: https://bhouston.github.io/houston-stratified-noise/

This repository exists so that every number and figure in the post can be reproduced, including the ones that are unfavourable to the noise.

## What the measurements say

1. **The fix that matters is one integer Weyl step per value.** The previous Three.js SSR and VXGI samplers were biased because their values per pixel were not independent. Giving each value its own integer Weyl step fixes that, and every variant measured that does so removes the banding.
2. **In the engine, the hierarchy's measured benefit is lower flicker.** A plain per-pixel hash with the same steps matches HSN on SSR within 2%. On VXGI, like for like with R2 steps (variant C against variant A), the hash is about 4% lower on RMSE (8.86 against 9.26) with about 24% more flicker (5.07 against 4.09). HSN costs four hashes per value against the hash's one, with no measurable frame-rate change.
3. **It is not blue noise.** On a single frame it is isotropic and free of spectral peaks, like blue noise, but its low frequencies are only partly suppressed, and its error after a blur is worse than interleaved gradient noise (IGN), R2 and blue-noise textures.
4. **IGN-based samplers are still better for one value per pixel.** Under exponential accumulation and a blur, animated IGN has about 1.5 times lower error, and IGN as a spatial phase with a golden-ratio Weyl step is also ahead (6.24 against 7.57).

Terms used throughout: **values per pixel** is how many random numbers a pixel draws per frame (1, 2 or 4, each with its own seed and step); **frames accumulated** is the length of the temporal history.

## Results: accumulated over time

Samplers like this are used under temporal accumulation: TRAA or an exponential moving average over roughly 16 to 32 frames, with a small spatial filter. These tables are excerpts of `results/temporal/tables_D.md`: RMSE ×1000 on a static flat field in a CPU model of the shader arithmetic, lower is better. Motion and disocclusion were not measured.

Exponential moving average, α = 0.1 (about 19 effective frames), then a Gaussian σ = 1 blur:

| Sampler | 1 value per pixel | 2 values | 4 values |
| --- | ---: | ---: | ---: |
| **HSN** | 7.57 | 14.2 | 17.1 |
| FAST texture | 7.82 | 11.4 | 18.4 |
| STBN texture | 8.52 | 15.9 | 19.4 |
| Void-and-cluster 64² + R_d steps | 7.64 | 12.1 | 15.4 |
| Animated IGN | 4.95 | 131.1 | 144.1 |
| Hash + R_d steps (float time) | 11.0 | 14.1 | 17.6 |
| White noise | 27.2 | 25.6 | 29.5 |

16 frames accumulated (box average), then a Gaussian σ = 1 blur:

| Sampler | 1 value per pixel | 2 values | 4 values |
| --- | ---: | ---: | ---: |
| **HSN** | 6.28 | 15.4 | 18.0 |
| FAST texture | 8.05 | 12.2 | 20.0 |
| STBN texture | 8.90 | 17.0 | 21.0 |
| Void-and-cluster 64² + R_d steps | 8.22 | 12.3 | 16.4 |
| Animated IGN | 4.69 | 131.1 | 144.1 |
| Hash + R_d steps (float time) | 10.4 | 14.4 | 17.9 |
| White noise | 29.8 | 27.8 | 32.3 |

32 frames accumulated, then a Gaussian σ = 1 blur:

| Sampler | 1 value per pixel | 2 values | 4 values |
| --- | ---: | ---: | ---: |
| **HSN** | 3.81 | 8.46 | 10.3 |
| FAST texture | 5.31 | 8.20 | 14.1 |
| STBN texture | 6.18 | 12.0 | 14.8 |
| Void-and-cluster 64² + R_d steps | 4.25 | 7.27 | 10.8 |
| Animated IGN | 3.12 | 131.1 | 144.0 |
| Hash + R_d steps (float time) | 5.48 | 8.76 | 12.0 |
| White noise | 21.1 | 19.7 | 22.8 |

The one-value column is the threshold tests, where HSN matches or beats FAST and STBN; on the smooth one-value test functions FAST is about 30% better and STBN about 14%. The animated IGN error for two and four values per pixel is bias from its correlated values. For two values a plain hash with the same steps ties HSN once about four frames are accumulated; for four values HSN keeps a small lead (4–14% depending on the window, about 14% at 32 frames). Per-pixel convergence comes from the Weyl steps, not from the hierarchy.

### In Three.js on a real GPU, steady state after TRAA

Excerpts of `results/gpu/realtime_metrics.json`: mean of three runs of 256 frames, ×10⁻³, change against the previous sampler; Apple M3, hardware WebGPU. A to D are simpler fixes run through the same harness. The shipped HSN row uses the first two R4 steps for VXGI while A, B and D use R2 steps, so compare A with C for a like-for-like step set.

VXGI:

| Sampler | RMSE | Bias | Temporal noise | Flicker |
| --- | ---: | ---: | ---: | ---: |
| Before (IGN pair) | 17.70 | 15.94 | 7.66 | 3.534 |
| **HSN** (pull request head) | 9.99 (−43.6%) | 5.26 (−67.0%) | 8.49 (+10.8%) | 4.140 (+17.2%) |
| A: Hash + R_d | 8.86 (−49.9%) | 4.29 (−73.1%) | 7.75 (+1.2%) | 5.067 (+43.4%) |
| B: IGN + R_d | 9.85 (−44.4%) | 7.03 (−55.9%) | 6.90 (−9.9%) | 3.837 (+8.6%) |
| C: HSN, R2 steps | 9.26 (−47.7%) | 5.44 (−65.9%) | 7.49 (−2.2%) | 4.094 (+15.9%) |
| D: Void-and-cluster + R_d | 10.66 (−39.8%) | 5.97 (−62.5%) | 8.83 (+15.2%) | 4.027 (+14.0%) |

SSR, denoised:

| Sampler | RMSE | Bias | Temporal noise | Flicker |
| --- | ---: | ---: | ---: | ---: |
| Before (analytic R2) | 3.282 | 1.715 | 2.798 | 2.461 |
| **HSN** (pull request head) | 2.982 (−9.1%) | 0.659 (−61.5%) | 2.908 (+3.9%) | 2.463 (+0.1%) |
| A: Hash + R_d | 3.000 (−8.6%) | 0.482 (−71.9%) | 2.961 (+5.8%) | 2.481 (+0.8%) |
| B: IGN + R_d | 3.335 (+1.6%) | 1.039 (−39.4%) | 3.169 (+13.2%) | 2.699 (+9.7%) |
| D: Void-and-cluster + R_d | 3.036 (−7.5%) | 0.676 (−60.6%) | 2.959 (+5.8%) | 2.459 (−0.1%) |

Bias is measured against white noise through the same TRAA and denoiser, which may favour the plain hash in the bias ranking. There is one static scene and camera per effect and one GPU.

## Results: single frame and short histories

These characterise the pattern, and the frames right after a history reset (a disocclusion or a camera cut), where HSN is furthest from blue-noise textures. On one frame its blurred error is 34% (one value per pixel) and 56% (two values) higher than the FAST texture's.

HSN is not blue noise. It is isotropic, peak-free, perfectly uniform noise whose low frequencies are suppressed by 12 to 18 dB relative to white. Real blue-noise masks suppress the same band by 30 to 50 dB, and the IGN and R2 lattices by 17 to 27 dB. Under every spatial filter tested HSN beats white noise and loses to IGN, R2 and all three blue-noise textures. What it has that IGN and R2 lack is a spectrum with no peaks and no direction; what it has that blue-noise textures lack is zero bytes and exact stratification on aligned 2, 4 and 8 pixel blocks.

Excerpts of `results/spatial/tables.md` (the eleven main methods; mean of 8 realizations of 256×256). Error left after a blur of one frame of the noise value, RMS ×10³ (multiple of white noise):

| Method | Gaussian σ=1 | Gaussian σ=2 | Gaussian σ=4 | box 3×3 | box 5×5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| **HSN** | 49.63 (0.61×) | 15.81 (0.39×) | 4.84 (0.24×) | 66.51 (0.69×) | 32.44 (0.56×) |
| White (PCG3D) | 81.60 (1.00×) | 40.68 (1.00×) | 20.20 (1.00×) | 96.42 (1.00×) | 57.73 (1.00×) |
| fract(sin) hash | 81.23 (1.00×) | 40.49 (1.00×) | 20.45 (1.01×) | 96.00 (1.00×) | 57.49 (1.00×) |
| Hoskins hash12 | 81.32 (1.00×) | 40.75 (1.00×) | 20.40 (1.01×) | 96.16 (1.00×) | 57.71 (1.00×) |
| IGN | 28.86 (0.35×) | 9.01 (0.22×) | 2.95 (0.15×) | 37.69 (0.39×) | 20.81 (0.36×) |
| R2 (Roberts) | 28.09 (0.34×) | 6.98 (0.17×) | 1.74 (0.09×) | 49.21 (0.51×) | 22.65 (0.39×) |
| Three.js Analytic R² | 29.88 (0.37×) | 7.63 (0.19×) | 2.09 (0.10×) | 50.37 (0.52×) | 23.61 (0.41×) |
| Bayer 8×8 | 13.94 (0.17×) | 2.40 (0.06×) | 0.05 (0.00×) | 52.67 (0.55×) | 28.15 (0.49×) |
| Void-and-cluster 256² | 14.09 (0.17×) | 0.77 (0.02×) | 0.14 (0.01×) | 43.30 (0.45×) | 19.90 (0.34×) |
| Peters blue noise 256² | 21.91 (0.27×) | 0.79 (0.02×) | 0.10 (0.01×) | 43.77 (0.45×) | 23.58 (0.41×) |
| FAST (EA) 128² | 20.04 (0.25×) | 1.39 (0.03×) | 0.37 (0.02×) | 43.49 (0.45×) | 21.92 (0.38×) |

Spectral peaks and direction: share of power in the single largest bin of a 50% mask, and mean radial anisotropy (isotropic noise is −9 dB):

| Method | largest bin, 50% mask, 128² crop | anisotropy mean (dB) |
| --- | ---: | ---: |
| **HSN** | 0.030% | -9.1 |
| White (PCG3D) | 0.017% | -9.1 |
| fract(sin) hash | 0.020% | -7.6 |
| Hoskins hash12 | 0.017% | -8.6 |
| IGN | 17.826% | +13.8 |
| R2 (Roberts) | 24.577% | +14.1 |
| Three.js Analytic R² | 31.721% | +19.4 |
| Bayer 8×8 | 100.000% | +22.2 |
| Void-and-cluster 256² | 0.024% | -9.1 |
| Peters blue noise 256² | 0.023% | -9.0 |
| FAST (EA) 128² | 0.022% | -9.1 |

Error of w×w window means relative to white noise: windows aligned to the grid / at every offset / at the worst offset:

| Method | 2×2 | 4×4 | 8×8 | 16×16 |
| --- | ---: | ---: | ---: | ---: |
| **HSN** | 0.500 / 0.799 / 1.004 | 0.250 / 0.617 / 0.777 | 0.125 / 0.457 / 0.579 | 0.127 / 0.340 / 0.426 |
| White (PCG3D) | 1.001 / 1.001 / 1.014 | 1.001 / 1.001 / 1.018 | 0.999 / 0.999 / 1.013 | 0.978 / 0.997 / 1.006 |
| fract(sin) hash | 0.998 / 0.999 / 1.013 | 0.999 / 0.997 / 1.014 | 0.997 / 0.996 / 1.005 | 1.011 / 1.008 / 1.022 |
| Hoskins hash12 | 1.000 / 0.999 / 1.012 | 1.000 / 0.999 / 1.012 | 1.006 / 1.003 / 1.017 | 0.995 / 0.993 / 1.005 |
| IGN | 0.575 / 0.575 / 0.577 | 0.486 / 0.485 / 0.488 | 0.298 / 0.298 / 0.302 | 0.207 / 0.206 / 0.211 |
| R2 (Roberts) | 0.556 / 0.556 / 0.557 | 0.285 / 0.285 / 0.287 | 0.271 / 0.272 / 0.277 | 0.274 / 0.276 / 0.279 |
| Three.js Analytic R² | 0.567 / 0.565 / 0.622 | 0.324 / 0.314 / 0.381 | 0.282 / 0.273 / 0.305 | 0.258 / 0.251 / 0.285 |
| Bayer 8×8 | 0.499 / 0.281 / 0.812 | 0.242 / 0.105 / 0.325 | 0.000 / 0.000 / 0.000 | 0.000 / 0.000 / 0.000 |
| Void-and-cluster 256² | 0.550 / 0.549 / 0.562 | 0.423 / 0.424 / 0.432 | 0.276 / 0.277 / 0.284 | 0.195 / 0.196 / 0.199 |
| Peters blue noise 256² | 0.680 / 0.678 / 0.690 | 0.452 / 0.452 / 0.460 | 0.314 / 0.313 / 0.320 | 0.214 / 0.217 / 0.222 |
| FAST (EA) 128² | 0.627 / 0.628 / 0.649 | 0.435 / 0.433 / 0.445 | 0.300 / 0.296 / 0.308 | 0.216 / 0.208 / 0.216 |

## Results: analytic R4 and what each part contributes

Hash-free "analytic R4" samplers (every pixel's phase a linear function of its coordinates) were compared on the CPU and in the engine. On the CPU flat-field test the per-value lattices have lower error than HSN (10–34% with four values). But every hash-free version puts 6–18% of a threshold mask's spectral power in a single bin (HSN: about 0.09%), and in the engine the lattice variants are worse than HSN and the plain hash on most measures, with structured error over time. The 32×32-tile analytic R4 of three.js fork PR #42 has the lowest SSR frame RMSE of anything measured (1.4% below HSN) but 38% more steady-state bias and visibly structured time-averaged error, and is worse than HSN in VXGI (RMSE +6.7%, bias +18%). The CPU and in-engine per-value-lattice variants use different direction pairs; the CPU tables also carry the exact in-engine definitions (rows E and F) for a like-for-like comparison.

A single-factor ablation (`results/r4-ablation/tables_ABL.md`) shows what each part of HSN buys and costs: the per-value steps and the Weyl step are the largest effects by far; the hierarchy gives 14 times less low-frequency energy and 1.4–1.7 times lower error for one value per pixel, fading after the first frame for two or more; the per-parent scramble removes the ordered-dither pattern and decorrelates the values but costs about 16% on one-value small-kernel error and flicker; the tile phase is nearly redundant once the scramble is present; three levels is the knee.

## What is here

| Path | Contents |
| --- | --- |
| `src/noise/` | Dependency-free ES modules: the bit-exact HSN reference (`hsn.js`), step constants (`steps.js`, including the optional four-value trade-off set from the step search), IGN and animated IGN, PCG and other hashes, Roberts' R2 and the old Three.js "Analytic R²", Bayer 8×8, and the hash + R_d, IGN + R_d and void-and-cluster + R_d baselines, and the analytic R4 lattice samplers. `noise.test.js` is the self-check. |
| `analysis/solution/` | Structural checks of the construction and the algorithm diagrams (Node). |
| `analysis/spatial/` | Single-frame analysis: histograms, spectra, radial power, anisotropy, filtered error, window stratification, autocorrelation (Python). |
| `analysis/temporal/` | Convergence over frames accumulated for 1, 2 and 4 values per pixel, EMA and short windows with spatial filters, flicker, temporal spectrum, long-run robustness, step constants, and the comparison against hash + R_d and IGN + R_d (Python). |
| `analysis/steps/` | A bounded search for better step constants with a held-out validation (Python). |
| `analysis/r4-ablation/` | Analytic R4 comparisons and the per-component ablation of HSN, on the temporal harness (Python). |
| `analysis/gpu/` | In-engine measurements of SSR, VXGI and a light map bake in three.js on a real GPU: harness, patches, driver, analysis. |
| `results/` | Committed outputs: JSON for numbers, WebP for figures. |
| `textures/` | Third-party blue-noise textures used as references, each with a `SOURCE.md` giving origin and licence. |
| `site/` | The static site (Vite, vanilla JS). |
| `names.json` | The display name of the noise, used by the plotting scripts and the site. |

## Reproduce

Requirements: Node 26 with pnpm, and [uv](https://docs.astral.sh/uv/) for the Python analyses.

```sh
pnpm install
pnpm test                # self-check: HSN bit-exact against stored vectors, aligned-tile permutation property, every module against the numpy implementations
pnpm analysis:solution   # results/solution/   (seconds)
pnpm analysis:spatial    # results/spatial/    (about 1 minute)
pnpm analysis:temporal   # results/temporal/   (about 6 minutes; downloads NVIDIA STBN on first run)
pnpm analysis:steps      # results/steps/      (about 5 minutes)
pnpm analysis:r4-ablation # results/r4-ablation/ (about 4 minutes)
pnpm analysis:gpu        # results/gpu/figures/ from the committed metrics and image crops
```

`pnpm py <script>` runs a Python script with Python 3.12 and the pinned packages in `analysis/requirements.txt` (uv creates the environment). Without uv: `python3.12 -m venv .venv && .venv/bin/pip install -r analysis/requirements.txt`, then run the scripts with `.venv/bin/python`. All analyses are deterministic; rerunning them from a clean checkout reproduces the committed JSON exactly. Generated textures and the STBN download are cached in `analysis/*/cache/` (git-ignored).

The in-engine measurements need three three.js checkouts and a hardware WebGPU adapter; `analysis/gpu/README.md` has the exact steps. The published numbers came from an Apple M3 (`metal-3`).

## Run the site

```sh
pnpm dev       # local development server
pnpm build     # static build in dist/, for the GitHub Pages base path /houston-stratified-noise/
pnpm preview   # serve dist/
```

The site renders its tables from the JSON in `results/` and runs `src/noise/` in the browser for the explorer. Pushing to `main` deploys it to GitHub Pages.

## Limitations

- Every CPU test is a static flat field with one sample of each value per pixel per frame. Motion, reprojection, disocclusion and history clamping were not measured, and short reset histories are where HSN is weakest against blue-noise textures.
- The spatial guarantees hold only for windows aligned to the 2, 4 and 8 pixel grid. Sub-pixel jitter, half-resolution tracing and upscaling break that alignment; the "every offset" numbers are the relevant ones for those pipelines.
- There is no repulsion across block edges, so the spectrum has no deep low-frequency hole.
- The values of a pixel are independently seeded, not jointly stratified in space.
- RMS error is not perception: structured residuals (IGN, R2, Bayer) and unstructured ones (HSN, blue noise) score the same.
- The in-engine measurements cover one static scene and camera per effect on one GPU; the bias metric depends on a white-noise-through-TRAA reference; fps was measured on a GPU shared with other work.
- The JavaScript reference is an operation-for-operation transliteration of the Three.js TSL. Equality with the shader is by construction; it also equals a CPU model that was compared with GPU output.

## Naming

`names.json` holds the display name and short name. The plotting scripts, generated tables and the site read it, so changing the name means editing that file and re-running the analyses and `pnpm build`. Prose in this README and the `analysis/*/README.md` files is static. Identifiers in code (`hsn`) do not change.

## Citations

- B. E. Bayer, "An optimum method for two-level rendition of continuous-tone pictures", Proc. IEEE Int. Conf. Commun., Conference Record, pp. (26-11)–(26-15), 1973.
- R. Ulichney, "The void-and-cluster method for dither array generation", 1993. http://cv.ulichney.com/papers/1993-void-cluster.pdf
- R. Cranley and T. N. L. Patterson, "Randomization of Number Theoretic Methods for Multiple Integration", SIAM Journal on Numerical Analysis 13(6):904–914, 1976. DOI 10.1137/0713071
- J. Jimenez, "Next Generation Post Processing in Call of Duty: Advanced Warfare", SIGGRAPH 2014 course (interleaved gradient noise). https://www.iryoku.com/next-generation-post-processing-in-call-of-duty-advanced-warfare/
- M. Roberts, "The Unreasonable Effectiveness of Quasirandom Sequences", 2018. https://extremelearning.com.au/unreasonable-effectiveness-of-quasirandom-sequences/
- M. Jarzynski and M. Olano, "Hash Functions for GPU Rendering", JCGT 9(3), 2020. https://www.jcgt.org/published/0009/03/02/paper.pdf
- C. Wellons, hash-prospector. https://github.com/skeeto/hash-prospector (the hash constants are from issue #19)
- A. Ahmed and P. Wonka, "Screen-space blue-noise diffusion of Monte Carlo sampling error via hierarchical ordering of pixels", 2020. DOI 10.1145/3414685.3417881
- C. Peters, "Free blue noise textures", 2016. https://momentsingraphics.de/BlueNoise.html
- W. Donnelly, A. Wolfe, J. Bütepage and J. Valdés, "Filter-Adapted Spatio-Temporal Sampling for Real-Time Rendering", I3D 2024. https://arxiv.org/abs/2310.15364
- A. Wolfe, N. Morrical, T. Akenine-Möller and R. Ramamoorthi, "Scalar Spatiotemporal Blue Noise Masks", EGSR 2022. https://arxiv.org/abs/2112.09629
- D. Hoskins, "Hash without Sine" (hash12).

## Licence

Code: MIT, see `LICENSE`. The textures in `textures/` are third-party works under their own licences (BSD 3-Clause for FAST, CC0 1.0 for Christoph Peters' textures); see the `SOURCE.md` in each directory. NVIDIA's STBN textures are under a non-commercial licence and are downloaded by the temporal analysis rather than included (`textures/stbn/SOURCE.md`). The harness in `analysis/gpu/harness/` and the patches in `analysis/gpu/patches/` are modifications of three.js example code (MIT).
