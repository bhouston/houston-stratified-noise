
**F. Single-frame spatial quality at different frame indices.** Share of the threshold mask's spectral power below 1/8 cycles/pixel (mean over thresholds 0.1, 0.3, 0.5; 128x128, Hann window). White noise expects 4.9%; lower is bluer.

| Method | frame 0 | frame 1 | frame 7 | frame 100 | frame 1000000 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN (golden / R2 / R4 steps) | 0.97% | 0.92% | 0.90% | 0.95% | 0.90% |
| White (PCG hash) | 5.12% | 5.03% | 5.17% | 5.57% | 5.07% |
| Animated IGN (+ fixed pixel offset per dim) | 0.42% | 0.42% | 0.42% | 0.41% | 11.34% |
| Animated IGN, 64-frame cycle (old VXGI) | 0.42% | 0.42% | 0.42% | 0.43% | 0.42% |
| Analytic R2 (old SSR, RNoise.js) | 0.19% | 0.19% | 0.19% | 0.19% | 0.19% |
| R_d Weyl + white per-pixel offset | 4.60% | 4.75% | 4.72% | 4.88% | 4.84% |
| R_d Weyl + IGN per-pixel offset | 0.42% | 0.42% | 0.41% | 0.43% | 0.15% |
| V&C 64x64 + golden Weyl (shared step) | 0.14% | 0.31% | 0.33% | 0.34% | 0.30% |
| STBN 128x128x64 texture | 0.28% | 0.34% | 0.28% | 0.31% | 0.30% |
| FAST 128x128x32 texture | 0.32% | 0.29% | 0.33% | 0.31% | 0.30% |

**F. The same for the raw value field (not thresholded).**

| Method | frame 0 | frame 1 | frame 7 | frame 100 | frame 1000000 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN (golden / R2 / R4 steps) | 0.93% | 0.86% | 0.82% | 0.91% | 0.89% |
| White (PCG hash) | 5.83% | 5.47% | 4.98% | 5.75% | 4.98% |
| Animated IGN (+ fixed pixel offset per dim) | 0.32% | 0.32% | 0.33% | 0.33% | 10.09% |
| Animated IGN, 64-frame cycle (old VXGI) | 0.32% | 0.32% | 0.33% | 0.32% | 0.32% |
| Analytic R2 (old SSR, RNoise.js) | 0.14% | 0.14% | 0.14% | 0.14% | 0.14% |
| R_d Weyl + white per-pixel offset | 4.98% | 4.74% | 4.61% | 4.71% | 5.12% |
| R_d Weyl + IGN per-pixel offset | 0.32% | 0.32% | 0.32% | 0.32% | 0.13% |
| V&C 64x64 + golden Weyl (shared step) | 0.00% | 0.29% | 0.30% | 0.31% | 0.31% |
| STBN 128x128x64 texture | 0.06% | 0.09% | 0.07% | 0.07% | 0.06% |
| FAST 128x128x32 texture | 0.02% | 0.03% | 0.02% | 0.02% | 0.03% |

**F. Spatial character of the error left after averaging N frames (threshold tests, no spatial filter).** Low-frequency share of the residual error field (white 4.9%) and its RMS x 1e-3. "Neighbour drift" is the RMS change over 64 frames of the wrapped difference between horizontally adjacent pixels: 0 means the pattern only ever shifts rigidly in value. "Mask corr." is the correlation between the u<0.3 masks of consecutive frames (independent frames expect 0; a perfectly anti-correlated pair with a 30% mask gives -0.43).

| Method | N=4 LF share | N=4 RMS | N=16 LF share | N=16 RMS | N=64 LF share | N=64 RMS | neighbour drift | mask corr. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| HSN (golden / R2 / R4 steps) | 1.43% | 147.0 | 1.07% | 38.2 | 2.62% | 11.9 | 0.0000 | -0.429 |
| White (PCG hash) | 5.11% | 215.1 | 5.34% | 107.2 | 4.95% | 53.4 | 0.2866 | -0.000 |
| Animated IGN (+ fixed pixel offset per dim) | 0.43% | 145.2 | 0.13% | 71.7 | 0.73% | 17.0 | 0.0060 | -0.429 |
| Animated IGN, 64-frame cycle (old VXGI) | 0.43% | 145.2 | 0.13% | 71.7 | 0.73% | 17.0 | 0.0060 | -0.429 |
| Analytic R2 (old SSR, RNoise.js) | 0.15% | 252.3 | 0.04% | 184.0 | 0.03% | 38.5 | 0.0381 | +0.229 |
| R_d Weyl + white per-pixel offset | 4.62% | 146.7 | 4.74% | 38.4 | 4.89% | 11.9 | 0.0000 | -0.429 |
| R_d Weyl + IGN per-pixel offset | 1.41% | 146.9 | 1.09% | 38.2 | 1.33% | 11.9 | 0.0000 | -0.429 |
| V&C 64x64 + golden Weyl (shared step) | 0.58% | 146.9 | 1.95% | 38.2 | 2.33% | 11.9 | 0.0000 | -0.429 |
| STBN 128x128x64 texture | 0.73% | 123.8 | 1.52% | 44.1 | 2.25% | 18.2 | 0.2822 | -0.421 |
| FAST 128x128x32 texture | 0.50% | 143.4 | 1.10% | 42.5 | 2.17% | 13.2 | 0.2802 | -0.267 |
