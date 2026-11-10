
**2-value: L2 star discrepancy x 1e-3 of one pixel's first N frames (mean over 128 pixels)**

| Method | N=4 | N=8 | N=16 | N=32 | N=64 | N=128 | N=256 | N=512 | N=1024 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| HSN (golden / R2 / R4 steps) | 128.3 | 83.4 | 56.3 | 35.7 | 17.3 | 11.5 | 5.81 | 3.28 | 1.63 |
| HSN, R4 steps 0-1 (as the PR calls it for VXGI) | 149.0 | 77.1 | 58.5 | 41.6 | 30.4 | 20.7 | 7.57 | 5.19 | 2.67 |
| HSN, shared golden step (broken on purpose) | 136.1 | 88.9 | 79.8 | 75.0 | 74.4 | 74.3 | 74.0 | 74.0 | 74.0 |
| White (PCG hash) | 173.2 | 122.9 | 86.2 | 64.4 | 43.8 | 30.9 | 21.8 | 15.5 | 11.1 |
| Animated IGN (+ fixed pixel offset per dim) | 141.5 | 102.6 | 86.9 | 70.4 | 68.4 | 67.8 | 67.3 | 67.2 | 67.2 |
| Animated IGN, 64-frame cycle (old VXGI) | 141.5 | 102.6 | 86.9 | 70.4 | 68.4 | 68.4 | 68.4 | 68.4 | 68.4 |
| Analytic R2 (old SSR, RNoise.js) | 185.3 | 132.7 | 111.3 | 80.9 | 34.0 | 22.9 | 16.3 | 11.6 | 9.30 |
| R_d Weyl + white per-pixel offset | 123.2 | 81.5 | 55.9 | 37.5 | 18.1 | 11.6 | 5.86 | 3.25 | 1.63 |
| R_d Weyl + IGN per-pixel offset | 123.1 | 83.0 | 55.2 | 35.7 | 17.2 | 11.4 | 5.84 | 3.26 | 1.65 |
| V&C 64x64 + golden Weyl (shared step) | 140.5 | 92.3 | 81.0 | 76.5 | 75.0 | 74.4 | 74.0 | 74.0 | 74.0 |
| V&C 64x64 + R_d Weyl steps | 124.9 | 82.1 | 56.2 | 35.8 | 17.9 | 11.5 | 5.91 | 3.27 | 1.60 |
| STBN 128x128x64 texture | 137.5 | 92.5 | 61.8 | 42.4 | 29.7 | 21.0 | 14.9 | 10.5 | 7.50 |
| FAST 128x128x32 texture | 135.3 | 81.5 | 49.0 | 28.1 | 19.9 | 14.1 | 9.88 | 7.02 | 5.05 |
| Scrambled Sobol per pixel (bound) | 116.3 | 64.1 | 34.7 | 18.4 | 9.75 | 5.13 | 2.69 | 1.40 | 0.73 |

**4-value: L2 star discrepancy x 1e-3 of one pixel's first N frames (mean over 128 pixels)**

| Method | N=4 | N=8 | N=16 | N=32 | N=64 | N=128 | N=256 | N=512 | N=1024 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| HSN (golden / R2 / R4 steps) | 97.4 | 60.6 | 41.2 | 29.1 | 20.4 | 12.5 | 8.05 | 5.94 | 5.08 |
| HSN, shared golden step (broken on purpose) | 95.9 | 72.4 | 65.9 | 62.8 | 62.5 | 62.3 | 62.2 | 62.2 | 62.1 |
| White (PCG hash) | 106.3 | 75.3 | 52.4 | 37.9 | 26.5 | 18.7 | 13.4 | 9.45 | 6.75 |
| Animated IGN (+ fixed pixel offset per dim) | 87.3 | 74.6 | 64.0 | 55.2 | 54.7 | 54.2 | 53.9 | 53.9 | 53.8 |
| Animated IGN, 64-frame cycle (old VXGI) | 87.3 | 74.6 | 64.0 | 55.2 | 54.7 | 54.7 | 54.7 | 54.7 | 54.7 |
| Analytic R2 (old SSR, RNoise.js) | 105.8 | 72.3 | 57.4 | 41.2 | 25.8 | 17.6 | 12.3 | 10.1 | 8.87 |
| R_d Weyl + white per-pixel offset | 95.5 | 59.6 | 41.5 | 29.6 | 20.5 | 12.4 | 8.11 | 6.05 | 5.15 |
| R_d Weyl + IGN per-pixel offset | 92.7 | 56.3 | 41.2 | 28.9 | 19.9 | 12.0 | 8.15 | 6.01 | 5.13 |
| V&C 64x64 + golden Weyl (shared step) | 99.6 | 73.9 | 68.9 | 65.5 | 64.2 | 63.9 | 63.7 | 63.7 | 63.8 |
| V&C 64x64 + R_d Weyl steps | 95.0 | 60.2 | 41.8 | 29.3 | 20.5 | 12.5 | 8.14 | 6.00 | 5.07 |
| STBN 128x128x64 texture | 96.0 | 67.9 | 46.3 | 33.2 | 22.9 | 16.2 | 11.6 | 8.16 | 5.80 |
| FAST 128x128x32 texture | 93.8 | 63.9 | 43.1 | 29.2 | 20.9 | 14.7 | 10.3 | 7.45 | 5.31 |
| Scrambled Sobol per pixel (bound) | 89.9 | 60.7 | 36.2 | 21.4 | 12.1 | 7.48 | 4.67 | 2.52 | 1.32 |

**2-value: correlation between dimension 1 and 2.** Over time at a pixel: 1024 frames, mean over 4096 pixels of |Pearson r| (independent white expects 0.025) and of chi-square/dof for an 8x8 joint histogram (independent white expects 1.0; below 1 is more even than random). Across pixels within a frame: 128x128 pixels, mean over 16 frames, 16x16 histogram (white expects |r| 0.006, chi-square/dof 1.0).

| Method | time |r| | time chi2/dof | space |r| | space chi2/dof |
| --- | ---: | ---: | ---: | ---: |
| HSN (golden / R2 / R4 steps) | 0.007 | 0.06 | 0.006 | 0.84 |
| HSN, R4 steps 0-1 (as the PR calls it for VXGI) | 0.006 | 0.07 | 0.006 | 0.93 |
| HSN, shared golden step (broken on purpose) | 0.386 | 70.39 | 0.005 | 0.85 |
| White (PCG hash) | 0.025 | 1.00 | 0.008 | 0.99 |
| Animated IGN (+ fixed pixel offset per dim) | 0.229 | 70.39 | 0.229 | 461.66 |
| Animated IGN, 64-frame cycle (old VXGI) | 0.229 | 73.52 | 0.229 | 461.66 |
| Analytic R2 (old SSR, RNoise.js) | 0.033 | 5.24 | 0.033 | 40.44 |
| R_d Weyl + white per-pixel offset | 0.007 | 0.06 | 0.005 | 0.88 |
| R_d Weyl + IGN per-pixel offset | 0.007 | 0.06 | 0.382 | 637.94 |
| V&C 64x64 + golden Weyl (shared step) | 0.382 | 69.92 | 0.014 | 3.57 |
| V&C 64x64 + R_d Weyl steps | 0.007 | 0.06 | 0.014 | 3.53 |
| STBN 128x128x64 texture | 0.017 | 0.91 | 0.003 | 0.96 |
| FAST 128x128x32 texture | 0.007 | 0.71 | 0.000 | 0.00 |

**4-value: the six pairwise projections.** Worst pair (and mean over pairs) of the same statistics, plus the joint 4-value histogram over time (4 bins per axis, 1024 frames, chi-square/dof; white expects 1.0).

| Method | time |r| worst pair | time chi2/dof worst pair | space |r| worst pair | space chi2/dof worst pair | time 4-value chi2/dof |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN (golden / R2 / R4 steps) | 0.071 (1-3; mean 0.018) | 6.44 (1-3; mean 1.15) | 0.009 (1-4; mean 0.007) | 1.14 (3-4; mean 0.96) | 0.54 |
| HSN, shared golden step (broken on purpose) | 0.392 (2-4; mean 0.384) | 71.30 (2-4; mean 70.56) | 0.010 (1-4; mean 0.007) | 1.17 (3-4; mean 0.95) | 98.94 |
| White (PCG hash) | 0.026 (1-3; mean 0.025) | 1.01 (2-4; mean 1.00) | 0.008 (1-4; mean 0.007) | 1.02 (2-3; mean 0.99) | 1.00 |
| Animated IGN (+ fixed pixel offset per dim) | 0.641 (3-4; mean 0.445) | 99.95 (1-4; mean 66.74) | 0.641 (3-4; mean 0.445) | 811.44 (3-4; mean 621.20) | 79.59 |
| Animated IGN, 64-frame cycle (old VXGI) | 0.642 (3-4; mean 0.446) | 102.92 (1-4; mean 70.02) | 0.641 (3-4; mean 0.445) | 811.44 (3-4; mean 621.20) | 82.97 |
| Analytic R2 (old SSR, RNoise.js) | 0.121 (1-4; mean 0.053) | 8.49 (2-4; mean 4.40) | 0.121 (1-4; mean 0.051) | 80.97 (1-3; mean 40.14) | 1.79 |
| R_d Weyl + white per-pixel offset | 0.072 (1-3; mean 0.019) | 6.43 (1-3; mean 1.15) | 0.009 (1-4; mean 0.006) | 1.16 (1-4; mean 1.00) | 0.54 |
| R_d Weyl + IGN per-pixel offset | 0.072 (1-3; mean 0.019) | 6.43 (1-3; mean 1.15) | 0.410 (1-4; mean 0.400) | 633.08 (1-2; mean 607.39) | 0.54 |
| V&C 64x64 + golden Weyl (shared step) | 0.387 (1-3; mean 0.383) | 70.86 (1-3; mean 70.36) | 0.015 (3-4; mean 0.013) | 4.06 (2-3; mean 3.80) | 98.88 |
| V&C 64x64 + R_d Weyl steps | 0.072 (1-3; mean 0.018) | 6.43 (1-3; mean 1.15) | 0.015 (1-3; mean 0.013) | 4.08 (2-3; mean 3.75) | 0.54 |
| STBN 128x128x64 texture | 0.029 (2-3; mean 0.024) | 0.96 (2-3; mean 0.94) | 0.007 (2-4; mean 0.006) | 0.99 (2-3; mean 0.97) | 0.98 |
| FAST 128x128x32 texture | 0.030 (1-4; mean 0.025) | 0.88 (1-4; mean 0.84) | 0.009 (2-4; mean 0.006) | 0.91 (3-4; mean 0.74) | 0.96 |

**4-value: chi-square/dof over time for each pair (8x8 histogram, 1024 frames)**

| Method | 1-2 | 1-3 | 1-4 | 2-3 | 2-4 | 3-4 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| HSN (golden / R2 / R4 steps) | 0.08 | 6.44 | 0.07 | 0.05 | 0.16 | 0.10 |
| HSN, shared golden step (broken on purpose) | 70.39 | 70.93 | 69.55 | 70.87 | 71.30 | 70.33 |
| White (PCG hash) | 1.00 | 1.00 | 1.00 | 1.00 | 1.01 | 1.00 |
| Animated IGN (+ fixed pixel offset per dim) | 70.39 | 49.36 | 99.95 | 55.89 | 75.99 | 48.83 |
| Animated IGN, 64-frame cycle (old VXGI) | 73.52 | 52.75 | 102.92 | 59.48 | 78.95 | 52.49 |
| Analytic R2 (old SSR, RNoise.js) | 5.24 | 3.99 | 7.36 | 0.58 | 8.49 | 0.72 |
| R_d Weyl + white per-pixel offset | 0.07 | 6.43 | 0.07 | 0.05 | 0.16 | 0.10 |
| R_d Weyl + IGN per-pixel offset | 0.08 | 6.43 | 0.07 | 0.05 | 0.16 | 0.10 |
| V&C 64x64 + golden Weyl (shared step) | 69.92 | 70.86 | 70.13 | 70.63 | 70.20 | 70.44 |
| V&C 64x64 + R_d Weyl steps | 0.07 | 6.43 | 0.07 | 0.05 | 0.16 | 0.10 |
| STBN 128x128x64 texture | 0.91 | 0.96 | 0.95 | 0.96 | 0.96 | 0.91 |
| FAST 128x128x32 texture | 0.71 | 0.87 | 0.88 | 0.87 | 0.88 | 0.86 |
