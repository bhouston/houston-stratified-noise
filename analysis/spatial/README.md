# Spatial analysis (one frame)

Entry point, from the repository root: `pnpm analysis:spatial` (see the top-level README for setup). It runs `run_all.py`, which writes everything in `results/spatial/`:

- `results.json`: every raw number
- `tables.json`, `tables.md`: the formatted tables (the website renders `tables.json`)
- `figures/*.webp`: the figures

Files: `noises.py` (every method plus self-checks; `python noises.py vectors` rewrites `src/noise/python-vectors.json` for the JavaScript self-check), `vnc.py` (void-and-cluster generator), `run_all.py` (metrics, tables, figures), `requirements.txt` (pinned packages, Python 3.12).

Scope: one frame (sample index 0), one scalar per pixel. Nothing here says anything about temporal convergence or multi-dimensional sampling. The reading of each figure and table is on the website's Results page (source: `site/src/spatial-readings.json`).

## Methods as implemented

Pixel coordinates are integers (no +0.5). Seeded methods use seeds 1..8 on the crop at (1024,1024); unseeded methods use eight 256×256 crops with origins (1024+256a, 1024+256b), all tile-aligned, inside a roughly 2300×2300 screen. Every field is generated with a 32-pixel margin so filters never see an artificial seam.

| Key | Definition | Arithmetic | Realizations |
| --- | --- | --- | --- |
| HSN | Port of `examples/jsm/tsl/utils/HierarchicalHashedWeyl.js` from three.js PR #35429, index 0, default step. `hash(v)`: `v=(v^v>>16)*0x21f0aaad; v=(v^v>>15)*0x735a2d97; v^v>>15`. `pixelHash(x,y,s)=hash(x*0x9e3779b1 ^ y*0x85ebca77 ^ s)`. For level 0..2: `q=pixelHash(x>>(l+1), y>>(l+1), seed ^ ((l+1)*0x632be5ab))`, `a=(x>>l)&1`, `b=(y>>l)&1`, `low = (q&4) ? a : b`, `rank |= ((((a^b)<<1)|low) ^ (q&3)) << (30-2l)`. Output `(rank + pixelHash(x>>3,y>>3,seed^0x02e5be93) + index*step) >> 8) / 2^24`. | uint32, wraps | seeds 1..8 |
| White (PCG3D) | Jarzynski and Olano `pcg3d(x, y, seed)`, x output, top 24 bits. | uint32 | seeds 1..8 |
| White (HSN's own hash) | `pixelHash(x,y,seed) >> 8 / 2^24`. Tables only. | uint32 | seeds 1..8 |
| fract(sin) hash | `fract(sin(x*12.9898 + y*78.233) * 43758.5453)` | float32, libm `sin` | 8 crops |
| Hoskins hash12 | `p3=fract(p.xyx*.1031); p3+=dot(p3,p3.yzx+33.33); fract((p3.x+p3.y)*p3.z)` | float32 | 8 crops |
| IGN | `fract(52.9829189*fract(0.06711056*x + 0.00583715*y))` | float32 | 8 crops |
| R2 (Roberts) | `fract(x/g + y/g²)`, g = 1.32471795724474602596 | float64 | 8 crops |
| Three.js Analytic R² | `bindAnalyticNoise` from `examples/jsm/tsl/utils/RNoise.js` on three.js `dev`, the noise SSR used before the PR. `c = (pixel + floor(fract((index+seed)*(0.7548776662, 0.5698402910))*32)) mod 32`, `t = c.x/g + c.y/g² + seed`, channel x = `fract(t*g*(1/g))`. Seed 47 (SSR's ray-march seed). | float32 | index 0..7 |
| Bayer 8×8 | Standard recursive matrix (M2 = [[0,2],[3,1]]), value `(index+0.5)/64`. | exact | 8 crops (identical) |
| Void-and-cluster 256² | Own generator, Ulichney 1993: toroidal Gaussian σ=1.5, 10% random initial pixels, relax, then rank. Value `(rank+0.5)/N²`. 128² and 64² versions (tiled) are in the tables only. | float64 | seeds 1..8 |
| Peters blue noise 256² | Christoph Peters' free blue noise textures (CC0), `Data/256_256/HDR_L_0..7.png`, 16-bit, value `(v+0.5)/65536`. | texture | 8 textures |
| FAST (EA) 128² | `gauss1-ema01-spatial.png` from three.js PR #35244 (EA FastNoise, real_uniform_gauss1_0_exp0101_product), B channel of the left 128 columns, slices 0,4,..,28, value `(v+0.5)/256`, tiled. The spatio-temporal atlas is in the tables only. | texture, 8-bit | 8 slices |

Checks run before every analysis (`noises.py`):

- HSN equals the JavaScript reference bit for bit on the 1,024 test vectors in `src/noise/hsn-vectors.json`.
- Every aligned 8×8 tile's top 6 bits are a permutation of 0..63 (4 seeds × 3 indices × 1,024 tiles); aligned 2×2 and 4×4 blocks hold all 4 and 16 leading ranks.
- HSN with scrambling and phase switched off is exactly the standard Bayer matrix.

Two definitional findings:

- **"Analytic R²" in Three.js is Roberts' mask, but wrapped to a 32×32 tile** and computed in float32 around t ≈ 47 to 110. It has 1,024 distinct values and visible seams every 32 pixels. Its x channel otherwise behaves like R2.
- **There is no separate "analytic R4" spatial noise.** `bindAnalyticNoise` returns four channels that are all `fract(c_k · t)` of the same scalar t, with c = 1, 2/g, 3g·0.4198754210, 4/g². Because 1/g² + 1/g³ = 1 exactly, channel y is `fract(0.1397·(x − y) + const)`: constant along diagonals. Channels z and w are near-constant along (0,1) and (1,1). They are included as extra table rows (`ch.1..3`); channel y is worse than white noise under a σ=1 blur (1.40×). `R4_STEPS` in HSN are temporal steps only and have no single-frame meaning, so R4 is left to the multi-dimensional analysis.

## Caveats and limits

- Flat targets only. Every filtered-error test integrates a constant. Edges, gradients, and edge-stopping or bilateral denoisers are not covered, and those are where lattice noises such as IGN and R2 alias.
- RMS error is not perception. IGN and R2 concentrate their residual in a few directions and frequencies, which reads as visible weave or banding; HSN's residual is isotropic and unstructured. The metrics here score those the same. No contrast-sensitivity weighting was applied.
- Gaussian blurs use a kernel truncated at 4σ. Thresholds are 16 evenly spaced levels (t = (i+0.5)/16); the threshold test uses 4 realizations, everything else 8.
- Deterministic lattices (IGN, R2, Bayer) have no real ensemble: their eight "realizations" are crops with the same spectrum. Their spectra are computed without a window on a 256² domain they are not periodic on, so peaks are slightly smeared; a Hann-windowed column is given for the largest-bin measure. Textures are analysed at their native period (FAST at 128², so its bins are 4× coarser and its largest-bin fraction is not comparable with 256² rows; use the 128² crop column).
- Largest-bin fractions depend on FFT size and on how many periodograms are averaged. Compare methods within a column only.
- IGN and the float hashes are evaluated at integer coordinates between 992 and 2336. Three.js passes pixel centres (x+0.5), which shifts IGN's phase but not its statistics. fract(sin) depends on the platform's `sin`; numpy float32 `sin` is not any particular GPU's.
- PCG was run as `pcg3d` only (not `pcg2d`). NVIDIA STBN was not downloaded. R2 was run in float64; the fixed-point `r2Weyl` from bhouston/three.js PR #117 is mathematically the same mask and was not run separately.
- The window test measures means of values. The equivalent count guarantee for thresholded masks (an aligned 8×8 tile has within ±1 of 64t pixels below t) was not tested separately.
- Bayer's very low errors rely on the filter being wider than its 8-pixel period and on a flat target.
