# Houston Stratified Noise

Houston Stratified Noise (HSN) is a texture-free, arithmetic-only screen-space noise for real-time rendering. It is also known as Hierarchical Hashed Weyl (HHW) in Three.js; the two are arithmetically identical.

It gives every aligned 8×8 tile the 64 values k/64 in a scrambled Bayer order, rotates each tile by a hashed phase, and rotates everything by a Weyl step each frame. It costs four integer hashes (about 100 integer operations) per value and needs no texture.

- Blog post: https://ben3d.ca/blog/houston-stratified-noise
- Three.js pull request: https://github.com/mrdoob/three.js/pull/35429
- Site with every figure, table and an interactive explorer: https://bhouston.github.io/houston-stratified-noise/

This repository exists so that every number and figure in the post can be reproduced, including the ones that are unfavourable to the noise.

## What is here

| Path | Contents |
| --- | --- |
| `src/noise/` | Dependency-free ES modules: the bit-exact HSN reference (`hsn.js`), step constants, IGN and animated IGN, PCG3D and other hashes, Roberts' R2 and the old Three.js "Analytic R²", Bayer 8×8, and the "hash + R_d" and "IGN + R_d" baselines. `noise.test.js` is the self-check. |
| `analysis/solution/` | Structural checks of the construction and the algorithm diagrams (Node). |
| `analysis/spatial/` | Single-frame analysis: histograms, spectra, radial power, anisotropy, filtered error, window stratification, autocorrelation (Python). |
| `analysis/temporal/`, `analysis/gpu/` | Pending. |
| `results/` | Committed outputs: JSON for numbers, WebP for figures. |
| `textures/` | Third-party blue-noise textures used as references, each with a `SOURCE.md` giving origin and licence. |
| `site/` | The static site (Vite, vanilla JS). |
| `names.json` | The display name of the noise, used by the plotting scripts and the site. |

## Reproduce

Requirements: Node 26 with pnpm, and [uv](https://docs.astral.sh/uv/) for the Python analysis.

```sh
pnpm install
pnpm test                # self-check: HSN bit-exact against stored vectors, aligned-tile permutation property, cross-checks against the numpy implementations
pnpm analysis:solution   # results/solution/: structure.txt, structure.json, step-pairs.json, diagrams
pnpm analysis:spatial    # results/spatial/: results.json, tables.json, tables.md, figures/*.webp
```

`pnpm analysis:spatial` runs `analysis/spatial/run_all.py` with Python 3.12 and the pinned packages in `analysis/spatial/requirements.txt` (uv creates the environment). Without uv: `python3.12 -m venv .venv && .venv/bin/pip install -r analysis/spatial/requirements.txt && .venv/bin/python analysis/spatial/run_all.py`. The first run generates the void-and-cluster textures (about a minute) and caches them in `analysis/spatial/cache/`. The run is deterministic; see `analysis/spatial/README.md` for the protocol.

## Run the site

```sh
pnpm dev       # local development server
pnpm build     # static build in dist/, for the GitHub Pages base path /houston-stratified-noise/
pnpm preview   # serve dist/
```

The site renders its tables from the JSON in `results/` and runs `src/noise/` in the browser for the explorer. Pushing to `main` deploys it to GitHub Pages.

## Results summary: one frame

HSN is not blue noise. It is isotropic, peak-free, perfectly uniform noise whose low frequencies are suppressed by 12 to 18 dB relative to white. Real blue-noise masks suppress the same band by 30 to 50 dB, and the IGN and R2 lattices by 17 to 27 dB. Under every spatial filter tested HSN beats white noise and loses to IGN, R2 and all three blue-noise textures. What it has that IGN and R2 lack is a spectrum with no peaks and no direction; what it has that blue-noise textures lack is zero bytes and exact stratification on aligned 2, 4 and 8 pixel blocks.

The tables below are excerpts of `results/spatial/tables.md` (the eleven main methods; mean of 8 realizations of 256×256).

Error left after a blur of the noise value, RMS ×10³ (multiple of white noise). Lower is better.

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

Spectral peaks and direction: share of power in the single largest bin of a 50% mask, and mean radial anisotropy (isotropic noise is −9 dB).

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

Error of w×w window means relative to white noise: windows aligned to the grid / at every offset / at the worst offset.

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

Temporal convergence and in-engine (SSR, VXGI) results are pending.

## Limitations

- The guarantees hold only for windows aligned to the 2, 4 and 8 pixel grid. Sub-pixel jitter, reprojection, half-resolution tracing and upscaling break that alignment; the "every offset" numbers are the relevant ones for those pipelines.
- There is no repulsion across block edges, so the spectrum has no deep low-frequency hole, and filtered error is worse than IGN, R2 and blue-noise textures.
- Dimensions are independently seeded, not jointly stratified in space.
- The spatial analysis integrates flat targets only and reports RMS error, which is not perception: structured residuals (IGN, R2, Bayer) and unstructured ones (HSN, blue noise) score the same. Edges, gradients and edge-aware denoisers are not covered.
- The JavaScript reference is an operation-for-operation transliteration of the Three.js TSL. Equality with the shader is by construction; it also equals a CPU model that was compared with GPU output.

## Naming

`names.json` holds the display name and short name. The plotting scripts, generated tables and the site read it, so switching the lead name means editing that file and re-running `pnpm analysis:solution`, `pnpm analysis:spatial` and `pnpm build`. Prose in this README and in `analysis/spatial/README.md` is static and needs a manual edit. Identifiers in code (`hsn`) do not change.

## Citations

- B. E. Bayer, "An optimum method for two-level rendition of continuous-tone pictures", 1973.
- R. Ulichney, "The void-and-cluster method for dither array generation", 1993. http://cv.ulichney.com/papers/1993-void-cluster.pdf
- R. Cranley and T. Patterson, "Randomization of number theoretic methods for multiple integration", 1976.
- J. Jimenez, "Next Generation Post Processing in Call of Duty: Advanced Warfare", SIGGRAPH 2014 course (interleaved gradient noise). https://www.iryoku.com/next-generation-post-processing-in-call-of-duty-advanced-warfare/
- M. Roberts, "The Unreasonable Effectiveness of Quasirandom Sequences", 2018. https://extremelearning.com.au/unreasonable-effectiveness-of-quasirandom-sequences/
- M. Jarzynski and M. Olano, "Hash Functions for GPU Rendering", JCGT 9(3), 2020. https://www.jcgt.org/published/0009/03/02/paper.pdf
- C. Wellons, hash-prospector. https://github.com/skeeto/hash-prospector (the hash constants are from issue #19)
- A. Ahmed and P. Wonka, "Screen-space blue-noise diffusion of Monte Carlo sampling error via hierarchical ordering of pixels", 2020. DOI 10.1145/3414685.3417881
- C. Peters, "Free blue noise textures", 2016. https://momentsingraphics.de/BlueNoise.html
- W. Donnelly, A. Wolfe, J. Bütepage and J. Valdés, "Filter-Adapted Spatio-Temporal Sampling for Real-Time Rendering", I3D 2024. https://arxiv.org/abs/2310.15364
- D. Hoskins, "Hash without Sine" (hash12).

## Licence

Code: MIT, see `LICENSE`. The textures in `textures/` are third-party works under their own licences (BSD 3-Clause for FAST, CC0 1.0 for Christoph Peters' textures); see the `SOURCE.md` in each directory.
