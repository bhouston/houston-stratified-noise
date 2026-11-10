
**G. Per-pixel RMSE x 1e-3 of a 64-frame average starting at frame n0, 1-value threshold tests (64x64 pixels, no spatial filter)**

| Method | n0=0 | n0=1e+02 | n0=1e+03 | n0=1e+04 | n0=1e+05 | n0=1e+06 | n0=1e+07 | n0=1e+08 | n0=1e+09 | n0=4e+09 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| HSN (golden / R2 / R4 steps) | 11.0 | 11.0 | 11.0 | 11.0 | 11.0 | 11.0 | 11.0 | 11.0 | 11.0 | 11.0 |
| White (PCG hash) | 52.3 | 52.7 | 52.2 | 52.1 | 52.2 | 52.4 | 52.2 | 52.6 | 52.2 | 52.0 |
| Animated IGN (+ fixed pixel offset per dim) | 16.2 | 16.2 | 16.3 | 17.7 | 44.5 | 43.6 | 213.7 | 566.4 | 566.4 | 566.4 |
| Animated IGN, 64-frame cycle (old VXGI) | 16.2 | 16.2 | 16.2 | 16.2 | 16.2 | 16.2 | 16.2 | 16.2 | 16.2 | 16.2 |
| Analytic R2 (old SSR, RNoise.js) | 37.3 | 40.8 | 40.3 | 39.5 | 38.9 | 38.4 | 322.0 | 419.0 | 419.0 | 419.0 |
| R_d Weyl + white per-pixel offset | 11.1 | 10.9 | 11.0 | 11.0 | 11.1 | 34.0 | 243.4 | 566.4 | 566.4 | 566.4 |
| R_d Weyl + IGN per-pixel offset | 11.0 | 11.0 | 11.0 | 11.0 | 11.2 | 33.9 | 243.4 | 566.4 | 566.4 | 566.4 |
| V&C 64x64 + golden Weyl (shared step) | 11.0 | 11.0 | 11.0 | 11.0 | 11.2 | 33.9 | 243.4 | 566.4 | 566.4 | 566.4 |
| STBN 128x128x64 texture | 17.8 | 19.7 | 19.8 | 19.7 | 19.7 | 17.8 | 17.8 | 17.8 | 17.7 | 17.7 |
| FAST 128x128x32 texture | 13.1 | 17.5 | 17.5 | 17.5 | 13.2 | 13.1 | 13.1 | 13.2 | 13.2 | 13.2 |

**G. Per-pixel RMSE x 1e-3 of a 64-frame average starting at frame n0, 2-value integrands (64x64 pixels, no spatial filter)**

| Method | n0=0 | n0=1e+02 | n0=1e+03 | n0=1e+04 | n0=1e+05 | n0=1e+06 | n0=1e+07 | n0=1e+08 | n0=1e+09 | n0=4e+09 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| HSN (golden / R2 / R4 steps) | 16.2 | 16.2 | 16.2 | 16.2 | 16.2 | 16.2 | 16.2 | 16.2 | 16.3 | 16.2 |
| HSN, R4 steps 0-1 (as the PR calls it for VXGI) | 24.6 | 24.6 | 24.5 | 24.5 | 24.6 | 24.6 | 24.5 | 24.6 | 24.6 | 24.6 |
| HSN, shared golden step (broken on purpose) | 136.6 | 136.7 | 136.7 | 136.7 | 136.7 | 136.6 | 136.7 | 136.7 | 136.7 | 136.7 |
| White (PCG hash) | 49.4 | 49.0 | 49.5 | 49.5 | 49.3 | 49.0 | 49.6 | 49.5 | 49.4 | 49.2 |
| Animated IGN (+ fixed pixel offset per dim) | 131.6 | 131.6 | 131.9 | 135.0 | 83.3 | 61.2 | 198.4 | 470.8 | 470.8 | 470.8 |
| Animated IGN, 64-frame cycle (old VXGI) | 131.6 | 131.6 | 131.6 | 131.6 | 131.6 | 131.6 | 131.6 | 131.6 | 131.6 | 131.6 |
| Analytic R2 (old SSR, RNoise.js) | 35.2 | 37.2 | 37.6 | 36.3 | 34.4 | 52.5 | 236.1 | 392.5 | 392.5 | 392.5 |
| R_d Weyl + white per-pixel offset | 16.3 | 16.2 | 16.2 | 16.2 | 16.6 | 34.5 | 239.9 | 470.8 | 470.8 | 470.8 |
| R_d Weyl + IGN per-pixel offset | 16.6 | 16.2 | 16.3 | 16.6 | 16.8 | 34.7 | 238.5 | 470.8 | 470.8 | 470.8 |
| V&C 64x64 + golden Weyl (shared step) | 136.2 | 136.1 | 136.1 | 136.1 | 136.1 | 140.2 | 356.8 | 470.8 | 470.8 | 470.8 |
| V&C 64x64 + R_d Weyl steps | 16.3 | 16.3 | 16.3 | 16.1 | 16.5 | 34.3 | 239.8 | 470.8 | 470.8 | 470.8 |
| STBN 128x128x64 texture | 31.8 | 32.8 | 32.9 | 32.8 | 32.9 | 32.0 | 31.8 | 31.7 | 32.0 | 32.0 |
| FAST 128x128x32 texture | 19.9 | 22.7 | 23.0 | 22.9 | 19.8 | 19.9 | 19.8 | 19.8 | 19.9 | 19.8 |

**G. Value diversity at large frame index (1-value).** Mean number of distinct values one pixel sees in 64 consecutive frames (ideal 64) / number of distinct values across the 4096 pixels of frame n0 / share of frames where a pixel repeats its previous value.

| Method | n0=0 | n0=1e+05 | n0=1e+06 | n0=1e+07 | n0=1e+09 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN (golden / R2 / R4 steps) | 64.0 / 4096 / 0% | 64.0 / 4096 / 0% | 64.0 / 4096 / 0% | 64.0 / 4096 / 0% | 64.0 / 4096 / 0% |
| White (PCG hash) | 64.0 / 4096 / 0% | 64.0 / 4095 / 0% | 64.0 / 4095 / 0% | 64.0 / 4093 / 0% | 64.0 / 4095 / 0% |
| Animated IGN (+ fixed pixel offset per dim) | 64.0 / 4096 / 0% | 64.0 / 256 / 0% | 30.8 / 32 / 0% | 4.0 / 4 / 2% | 1.0 / 1 / 100% |
| Animated IGN, 64-frame cycle (old VXGI) | 64.0 / 4096 / 0% | 64.0 / 4096 / 0% | 64.0 / 4096 / 0% | 64.0 / 4096 / 0% | 64.0 / 4096 / 0% |
| Analytic R2 (old SSR, RNoise.js) | 64.0 / 1024 / 0% | 64.0 / 1024 / 0% | 64.0 / 1024 / 0% | 4.0 / 1024 / 5% | 1.0 / 1024 / 100% |
| R_d Weyl + white per-pixel offset | 64.0 / 4096 / 0% | 64.0 / 256 / 0% | 16.0 / 16 / 0% | 2.0 / 2 / 24% | 1.0 / 1 / 100% |
| R_d Weyl + IGN per-pixel offset | 64.0 / 4096 / 0% | 64.0 / 256 / 0% | 16.0 / 16 / 0% | 2.0 / 2 / 24% | 1.0 / 1 / 100% |
| V&C 64x64 + golden Weyl (shared step) | 64.0 / 4096 / 0% | 64.0 / 256 / 0% | 16.0 / 16 / 0% | 2.0 / 2 / 24% | 1.0 / 1 / 100% |
| STBN 128x128x64 texture | 57.5 / 256 / 0% | 57.7 / 256 / 0% | 57.7 / 256 / 0% | 57.5 / 256 / 0% | 57.5 / 256 / 0% |
| FAST 128x128x32 texture | 59.7 / 256 / 0% | 59.5 / 256 / 0% | 59.9 / 256 / 0% | 59.8 / 256 / 0% | 59.7 / 256 / 0% |
