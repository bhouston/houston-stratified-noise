
**ABL.0 Summary: what each HSN component buys.** RMSE values x 1e-3; "ratio" is without / with (above 1 means the component helps on that metric, below 1 means it costs).

| Component | What it is for | Metric | With (full HSN) | Without | Ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| Hierarchy (vs per-pixel hash phase) | stratify values inside every small footprint | single frame, Gauss s=1, 1 value | 63.4 | 110.5 | 1.74x |
|  |  | single frame, Gauss s=1, 2 values | 94.6 | 111.4 | 1.18x |
|  |  | EMA 0.1 + Gauss s=1, 1 value | 6.89 | 9.93 | 1.44x |
|  |  | EMA 0.1 + Gauss s=1, 2 values | 14.2 | 14.2 | 1.00x |
|  |  | low-frequency share of 50% mask | 0.360% | 5.100% | 14.16x |
| Per-parent scramble (vs Bayer order, tile phase kept) | remove the regular ordered-dither pattern | largest spectral bin of 50% mask | 0.099% | 0.578% | 5.85x |
|  |  | anisotropy of 50% mask | 0.15 | 1.34 | 9.19x |
|  | decorrelate the dimensions (Bayer gives every seed the same rank order) | single frame, Gauss s=1, 2 values | 94.6 | 130.2 | 1.38x |
|  |  | EMA 0.1 + Gauss s=1, 2 values | 14.2 | 15.7 | 1.10x |
|  |  | EMA 0.1 + Gauss s=1, 4 values | 17.1 | 24.8 | 1.45x |
|  | cost | single frame, Gauss s=1, 1 value | 63.4 | 53.2 | 0.84x |
|  | cost | EMA 0.1 + Gauss s=1, 1 value | 6.89 | 6.60 | 0.96x |
|  | cost | flicker, EMA + Gauss s=1, 1 value | 6.65 | 5.57 | 0.84x |
| Tile phase (vs none, scramble kept) | hide the 8-pixel tile grid; continuous values | power on multiples of 1/8 cycle/pixel | 0.405% | 0.492% | 1.22x |
|  |  | histogram chi2/dof, 256 bins | 0.624 | 192.753 | 309.13x |
|  | (no measurable effect) | unaligned 8x8 window mean, 1 value | 21.2 | 21.6 | 1.02x |
|  | (no measurable effect) | single frame, Gauss s=2, 1 value | 19.2 | 19.7 | 1.03x |
|  | (no measurable effect) | EMA 0.1 + Gauss s=1, 2 values | 14.2 | 14.2 | 1.00x |
| Tile phase (vs none, without scramble) | breaks up the tiled Bayer matrix | largest spectral bin of 50% mask | 0.578% | 28.285% | 48.89x |
|  |  | power on multiples of 1/8 cycle/pixel | 0.187% | 100.000% | 534.17x |
| Scramble + phase (vs tiled Bayer 8x8) | both together | largest spectral bin of 50% mask | 0.099% | 28.285% | 285.88x |
|  | cost | single frame, Gauss s=1, 1 value | 63.4 | 44.1 | 0.70x |
|  | cost | single frame, Gauss s=2, 1 value | 19.2 | 8.87 | 0.46x |
|  | cost | unaligned 8x8 window mean, 1 value | 21.2 | 5.41 | 0.26x |
| Hierarchy | exact stratification of every aligned 8x8 tile | aligned 8x8 window mean, 1 value | 5.11 | 49.1 | 9.61x |
|  | (lost when the window straddles tiles) | unaligned 8x8 window mean, 1 value | 21.2 | 48.9 | 2.31x |
| Three levels (vs one level) | stratify at 2, 4 and 8 pixels | single frame, Gauss s=2, 1 value | 19.2 | 26.1 | 1.36x |
|  |  | EMA 0.1 + Gauss s=1, 2 values | 14.2 | 16.0 | 1.12x |
| Three levels (vs two) |  | single frame, Gauss s=2, 1 value | 19.2 | 20.3 | 1.06x |
| Three levels (vs four) | a fourth level | single frame, Gauss s=2, 1 value | 19.2 | 19.2 | 1.00x |
|  |  | EMA 0.1 + Gauss s=1, 1 value | 6.89 | 6.86 | 1.00x |
| Per-dimension steps (vs shared golden step) | keep a pixel's dimensions independent over time | per pixel, N=256, 2 values | 5.18 | 136.3 | 26.33x |
|  |  | EMA 0.1 + Gauss s=1, 2 values | 14.2 | 48.1 | 3.37x |
|  |  | EMA 0.1 + Gauss s=1, 4 values | 17.1 | 63.8 | 3.74x |
| Weyl temporal step (vs static pattern) | converge over time at each pixel | per pixel, N=64, 1 value | 10.0 | 390.6 | 39.00x |
|  |  | EMA 0.1 + Gauss s=1, 1 value | 6.89 | 63.3 | 9.20x |
|  | cost | flicker, EMA + Gauss s=1, 1 value | 6.65 | 0.00 | 0.00x |
| uint32 time (vs float32) from frame 1e5 | no precision loss at large frame index | per pixel, N=64, 1 value | 9.99 | 10.1 | 1.01x |
|  |  | EMA 0.1 + Gauss s=1, 2 values | 14.2 | 14.5 | 1.02x |
| uint32 time (vs float32) from frame 1e6 | no precision loss at large frame index | per pixel, N=64, 1 value | 9.99 | 31.8 | 3.18x |
|  |  | EMA 0.1 + Gauss s=1, 2 values | 14.3 | 33.1 | 2.32x |
| uint32 time (vs float32) from frame 1e7 | no precision loss at large frame index | per pixel, N=64, 1 value | 9.99 | 228.3 | 22.85x |
|  |  | EMA 0.1 + Gauss s=1, 2 values | 14.3 | 239.3 | 16.77x |

**ABL.1 Single frame, one value per pixel: histogram and spectrum.** Histogram: chi-square/dof of the 128x128 value field in 64 and 256 equal bins (white expects 1.0; 0 is exactly uniform). 50% threshold mask (Hann window, mean of 4 frames): largest spectral bin as a share of power (white about 0.05%), angular anisotropy (std/mean over 16 direction sectors), share of power below 1/8 cycle/pixel (white 4.9%), and share of power exactly on multiples of 1/8 cycle/pixel (no window; white expects 0.38%).

| Variant | hist 64 bins | hist 256 bins | largest bin | anisotropy | low-freq share | power on 1/8 multiples |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1. Full HSN | 0.000 | 0.624 | 0.099% | 0.15 | 0.36% | 0.40% |
| 2. No per-parent scramble (Bayer hierarchy + tile phase) | 0.000 | 0.624 | 0.578% | 1.34 | 0.53% | 0.19% |
| 3. No tile phase (scrambled hierarchy only) | 0.000 | 192.753 | 0.096% | 0.30 | 0.39% | 0.49% |
| 4. Neither (tiled Bayer 8x8) | 0.000 | 192.753 | 28.285% | 1.78 | 0.01% | 100.00% |
| 5. Hash phase only, no hierarchy | 1.122 | 1.124 | 0.052% | 0.08 | 5.10% | 0.37% |
| 6a. Hierarchy depth 1 (2x2 tiles) | 1.565 | 1.297 | 0.078% | 0.15 | 0.34% | 0.32% |
| 6b. Hierarchy depth 2 (4x4 tiles) | 0.433 | 0.953 | 0.080% | 0.16 | 0.35% | 0.32% |
| 6d. Hierarchy depth 4 (16x16 tiles) | 0.000 | 0.000 | 0.093% | 0.15 | 0.34% | 0.41% |
| 7. Shared temporal step | 0.000 | 0.624 | 0.099% | 0.15 | 0.36% | 0.40% |
| 8. No temporal step (static pattern) | 0.000 | 0.769 | 0.083% | 0.18 | 0.34% | 0.44% |
| 9. uint32 time, frames from 1e5 | 0.000 | 0.471 | 0.102% | 0.14 | 0.35% | 0.46% |
| 9. float32 time, frames from 1e5 | 0.000 | 0.031 | 0.104% | 0.14 | 0.35% | 0.47% |
| 9. uint32 time, frames from 1e6 | 0.000 | 0.573 | 0.095% | 0.14 | 0.37% | 0.42% |
| 9. float32 time, frames from 1e6 | 780.190 | 963.765 | 0.106% | 0.14 | 0.35% | 0.45% |
| 9. uint32 time, frames from 1e7 | 0.000 | 0.631 | 0.097% | 0.15 | 0.35% | 0.43% |
| 9. float32 time, frames from 1e7 | 8061.968 | 8159.875 | 0.087% | 0.14 | 0.35% | 0.43% |

**ABL.2 Single frame, spatial filters: RMSE x 1e-3.** 8x8 window mean of one frame (aligned with the tile grid, and at every other offset), then 3x3 box and Gaussian sigma 1 and 2, for one value (10 1-value integrands) and two values (14 2-value integrands).

| Variant | 1v 8x8 aligned | 1v 8x8 unaligned | 1v 3x3 | 1v Gauss 1 | 1v Gauss 2 | 2v 8x8 aligned | 2v 8x8 unaligned | 2v 3x3 | 2v Gauss 1 | 2v Gauss 2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1. Full HSN | 5.11 | 21.2 | 86.4 | 63.4 | 19.2 | 37.1 | 40.1 | 115.1 | 94.6 | 44.4 |
| 2. No per-parent scramble (Bayer hierarchy + tile phase) | 5.11 | 27.4 | 90.5 | 53.2 | 22.6 | 136.3 | 93.3 | 150.5 | 130.2 | 99.7 |
| 3. No tile phase (scrambled hierarchy only) | 5.41 | 21.6 | 86.9 | 63.9 | 19.7 | 37.1 | 39.6 | 115.5 | 94.5 | 43.7 |
| 4. Neither (tiled Bayer 8x8) | 5.41 | 5.41 | 93.5 | 44.1 | 8.87 | 140.8 | 140.8 | 159.6 | 136.9 | 128.8 |
| 5. Hash phase only, no hierarchy | 49.1 | 48.9 | 130.3 | 110.5 | 55.8 | 49.4 | 49.3 | 131.5 | 111.4 | 55.9 |
| 6a. Hierarchy depth 1 (2x2 tiles) | 19.9 | 26.1 | 89.6 | 67.4 | 26.1 | 40.9 | 42.3 | 116.8 | 96.6 | 47.1 |
| 6b. Hierarchy depth 2 (4x4 tiles) | 9.56 | 21.8 | 87.0 | 63.9 | 20.3 | 38.0 | 40.2 | 115.1 | 94.6 | 44.3 |
| 6d. Hierarchy depth 4 (16x16 tiles) | 5.11 | 21.2 | 86.2 | 63.2 | 19.2 | 37.3 | 39.6 | 115.2 | 94.6 | 44.0 |
| 7. Shared temporal step | 5.11 | 21.2 | 86.4 | 63.4 | 19.2 | 36.8 | 40.2 | 115.0 | 94.4 | 44.4 |
| 8. No temporal step (static pattern) | 5.11 | 21.2 | 86.4 | 63.3 | 19.3 | 37.0 | 40.4 | 115.4 | 94.9 | 44.7 |
| 9. uint32 time, frames from 1e5 | 5.13 | 21.1 | 86.4 | 63.4 | 19.4 | 37.0 | 40.2 | 115.0 | 94.5 | 44.3 |
| 9. float32 time, frames from 1e5 | 5.49 | 21.2 | 86.3 | 63.4 | 19.4 | 37.2 | 40.3 | 115.0 | 94.5 | 44.4 |
| 9. uint32 time, frames from 1e6 | 5.10 | 21.2 | 86.5 | 63.5 | 19.1 | 36.9 | 40.0 | 115.4 | 94.9 | 44.5 |
| 9. float32 time, frames from 1e6 | 30.0 | 36.0 | 89.0 | 67.7 | 34.5 | 47.1 | 49.6 | 117.8 | 98.1 | 53.0 |
| 9. uint32 time, frames from 1e7 | 5.11 | 21.2 | 86.5 | 63.5 | 19.3 | 36.9 | 40.2 | 115.4 | 94.8 | 44.6 |
| 9. float32 time, frames from 1e7 | 228.0 | 228.5 | 238.2 | 232.9 | 228.3 | 242.9 | 243.1 | 265.3 | 257.5 | 243.8 |

**ABL.3 Over time: RMSE x 1e-3.** EMA alpha=0.1 + Gaussian sigma 1 for 1, 2 and 4 values; per-pixel running mean with no spatial filter at N = 64 and 256 for 1 and 2 values; flicker = RMS frame-to-frame change of the EMA + Gaussian sigma 1 output.

| Variant | EMA+G1, 1v | EMA+G1, 2v | EMA+G1, 4v | per-pixel N=64, 1v | N=256, 1v | N=64, 2v | N=256, 2v | flicker 1v | flicker 2v |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1. Full HSN | 6.89 | 14.2 | 17.1 | 10.0 | 2.56 | 16.2 | 5.18 | 6.65 | 9.86 |
| 2. No per-parent scramble (Bayer hierarchy + tile phase) | 6.60 | 15.7 | 24.8 | 10.0 | 2.56 | 16.2 | 5.20 | 5.57 | 13.6 |
| 3. No tile phase (scrambled hierarchy only) | 6.87 | 14.2 | 17.1 | 9.94 | 2.51 | 16.3 | 5.19 | 6.64 | 9.86 |
| 4. Neither (tiled Bayer 8x8) | 6.14 | 16.5 | 27.0 | 9.94 | 2.51 | 16.4 | 5.20 | 4.38 | 15.1 |
| 5. Hash phase only, no hierarchy | 9.93 | 14.2 | 17.5 | 10.0 | 2.58 | 16.3 | 5.18 | 11.6 | 11.6 |
| 6a. Hierarchy depth 1 (2x2 tiles) | 7.21 | 16.0 | 17.4 | 10.2 | 2.58 | 16.3 | 5.19 | 7.08 | 10.0 |
| 6b. Hierarchy depth 2 (4x4 tiles) | 6.94 | 14.3 | 17.0 | 10.0 | 2.56 | 16.2 | 5.17 | 6.67 | 9.89 |
| 6d. Hierarchy depth 4 (16x16 tiles) | 6.86 | 14.2 | 17.0 | 10.0 | 2.57 | 16.3 | 5.17 | 6.63 | 9.85 |
| 7. Shared temporal step | 6.89 | 48.1 | 63.8 | 10.0 | 2.56 | 136.6 | 136.3 | 6.65 | 8.59 |
| 8. No temporal step (static pattern) | 63.3 | 94.9 | 111.9 | 390.6 | 390.6 | 393.5 | 393.5 | 0.00 | 0.00 |
| 9. uint32 time, frames from 1e5 | 6.89 | 14.2 | 17.1 | 9.99 | 2.57 | 16.2 | 5.17 | 6.65 | 9.86 |
| 9. float32 time, frames from 1e5 | 7.10 | 14.5 | 17.3 | 10.1 | 3.20 | 16.5 | 5.98 | 6.64 | 9.86 |
| 9. uint32 time, frames from 1e6 | 6.89 | 14.3 | 17.1 | 9.99 | 2.58 | 16.2 | 5.18 | 6.65 | 9.86 |
| 9. float32 time, frames from 1e6 | 30.6 | 33.1 | 36.9 | 31.8 | 30.1 | 34.3 | 30.6 | 6.38 | 9.76 |
| 9. uint32 time, frames from 1e7 | 6.89 | 14.3 | 17.1 | 9.99 | 2.57 | 16.2 | 5.15 | 6.65 | 9.86 |
| 9. float32 time, frames from 1e7 | 228.0 | 239.3 | 294.8 | 228.3 | 228.0 | 239.7 | 239.2 | 4.99 | 9.95 |

**ABL.4 Short windows with Gaussian sigma 1: RMSE x 1e-3 after N frames, one and two values.**

| Variant | 1v N=1 | 1v N=4 | 1v N=8 | 1v N=16 | 2v N=1 | 2v N=4 | 2v N=8 | 2v N=16 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1. Full HSN | 63.4 | 22.7 | 12.3 | 5.65 | 94.6 | 37.8 | 25.4 | 15.4 |
| 2. No per-parent scramble (Bayer hierarchy + tile phase) | 53.2 | 21.7 | 12.2 | 5.67 | 130.2 | 47.1 | 31.7 | 13.2 |
| 3. No tile phase (scrambled hierarchy only) | 63.9 | 23.1 | 12.2 | 5.64 | 94.5 | 37.8 | 25.5 | 15.3 |
| 4. Neither (tiled Bayer 8x8) | 44.1 | 22.0 | 11.4 | 5.27 | 136.9 | 49.1 | 34.6 | 12.1 |
| 5. Hash phase only, no hierarchy | 110.5 | 35.6 | 14.4 | 9.23 | 111.4 | 37.1 | 23.9 | 14.4 |
| 6a. Hierarchy depth 1 (2x2 tiles) | 67.4 | 23.4 | 13.3 | 5.87 | 96.6 | 39.5 | 27.8 | 18.0 |
| 6b. Hierarchy depth 2 (4x4 tiles) | 63.9 | 23.1 | 12.3 | 5.68 | 94.6 | 37.8 | 25.4 | 15.3 |
| 6d. Hierarchy depth 4 (16x16 tiles) | 63.2 | 22.7 | 12.2 | 5.64 | 94.6 | 37.6 | 25.3 | 15.3 |
| 7. Shared temporal step | 63.4 | 22.7 | 12.3 | 5.65 | 94.4 | 54.7 | 49.8 | 47.8 |
| 8. No temporal step (static pattern) | 63.3 | 63.3 | 63.3 | 63.3 | 94.9 | 94.9 | 94.9 | 94.9 |
| 9. uint32 time, frames from 1e5 | 63.4 | 22.9 | 12.3 | 5.63 | 94.5 | 37.9 | 25.5 | 15.3 |
| 9. float32 time, frames from 1e5 | 63.4 | 22.9 | 12.3 | 5.96 | 94.5 | 37.7 | 25.6 | 15.5 |
| 9. uint32 time, frames from 1e6 | 63.5 | 22.8 | 12.4 | 5.68 | 94.9 | 37.7 | 25.4 | 15.3 |
| 9. float32 time, frames from 1e6 | 67.7 | 35.5 | 31.7 | 30.4 | 98.1 | 47.4 | 39.1 | 33.6 |
| 9. uint32 time, frames from 1e7 | 63.5 | 22.8 | 12.3 | 5.65 | 94.8 | 37.9 | 25.6 | 15.4 |
| 9. float32 time, frames from 1e7 | 232.9 | 228.7 | 228.1 | 228.0 | 257.5 | 240.9 | 240.1 | 239.3 |
