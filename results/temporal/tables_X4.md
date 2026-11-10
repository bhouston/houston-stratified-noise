
**X4. 1-value threshold tests (golden step): per-pixel RMSE x 1e-3, no spatial filter**

| Method | N=16 | N=64 | N=256 |
| --- | ---: | ---: | ---: |
| HSN | 36.7 | 11.0 | 2.85 |
| A. Hash + R_d | 36.9 | 11.1 | 2.86 |
| B. IGN + R_d | 36.8 | 11.0 | 2.86 |
| White (PCG hash) | 104.5 | 52.3 | 25.8 |
| FAST 128x128x32 texture | 42.4 | 13.1 | 6.60 |

**X4. 1-value threshold tests (golden step), no blur: RMSE x 1e-3 after N frames (box average) and under EMA alpha=0.1**

| Method | N=1 | N=4 | N=8 | N=16 | EMA 0.1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN | 419.0 | 137.8 | 57.2 | 36.7 | 38.9 |
| A. Hash + R_d | 418.9 | 137.9 | 57.4 | 36.8 | 38.9 |
| B. IGN + R_d | 419.0 | 137.8 | 57.3 | 36.7 | 38.9 |
| White (PCG hash) | 419.0 | 209.9 | 148.3 | 104.8 | 96.3 |
| FAST 128x128x32 texture | 419.3 | 151.4 | 80.4 | 46.7 | 48.1 |

**X4. 1-value threshold tests (golden step), 3x3 box: RMSE x 1e-3 after N frames (box average) and under EMA alpha=0.1**

| Method | N=1 | N=4 | N=8 | N=16 | EMA 0.1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN | 93.4 | 32.3 | 16.7 | 8.41 | 9.77 |
| A. Hash + R_d | 141.1 | 46.3 | 19.2 | 12.3 | 13.0 |
| B. IGN + R_d | 54.0 | 23.9 | 14.7 | 8.87 | 8.26 |
| White (PCG hash) | 139.0 | 70.0 | 49.7 | 35.1 | 32.1 |
| FAST 128x128x32 texture | 78.2 | 30.6 | 17.5 | 10.7 | 10.6 |

**X4. 1-value threshold tests (golden step), Gauss sigma 1: RMSE x 1e-3 after N frames (box average) and under EMA alpha=0.1**

| Method | N=1 | N=4 | N=8 | N=16 | EMA 0.1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN | 68.6 | 24.8 | 13.5 | 6.28 | 7.57 |
| A. Hash + R_d | 119.8 | 39.3 | 16.2 | 10.4 | 11.1 |
| B. IGN + R_d | 40.3 | 19.0 | 11.5 | 6.78 | 6.24 |
| White (PCG hash) | 117.7 | 59.3 | 42.2 | 29.8 | 27.2 |
| FAST 128x128x32 texture | 51.3 | 21.4 | 12.8 | 8.05 | 7.82 |

**X4. 1-value threshold tests (golden step), Gauss sigma 2: RMSE x 1e-3 after N frames (box average) and under EMA alpha=0.1**

| Method | N=1 | N=4 | N=8 | N=16 | EMA 0.1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN | 20.8 | 8.68 | 4.83 | 2.10 | 2.64 |
| A. Hash + R_d | 60.8 | 19.8 | 8.12 | 5.18 | 5.55 |
| B. IGN + R_d | 12.3 | 8.41 | 4.60 | 2.40 | 2.54 |
| White (PCG hash) | 58.9 | 30.0 | 21.3 | 14.9 | 13.6 |
| FAST 128x128x32 texture | 14.0 | 6.68 | 4.49 | 3.09 | 2.92 |

**X4. 1-value threshold tests (golden step): HSN error relative to A and B (below 1.00 means HSN is better)**

| Ratio | N=1 | N=4 | N=8 | N=16 | EMA 0.1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN / Hash + R_d, 3x3 box | 0.66 | 0.70 | 0.87 | 0.68 | 0.75 |
| HSN / Hash + R_d, Gauss s=1 | 0.57 | 0.63 | 0.83 | 0.60 | 0.68 |
| HSN / Hash + R_d, Gauss s=2 | 0.34 | 0.44 | 0.60 | 0.40 | 0.47 |
| HSN / IGN + R_d, 3x3 box | 1.73 | 1.35 | 1.13 | 0.95 | 1.18 |
| HSN / IGN + R_d, Gauss s=1 | 1.70 | 1.30 | 1.18 | 0.93 | 1.21 |
| HSN / IGN + R_d, Gauss s=2 | 1.69 | 1.03 | 1.05 | 0.87 | 1.04 |

**X4. 2-value integrands (R2 steps): per-pixel RMSE x 1e-3, no spatial filter**

| Method | N=16 | N=64 | N=256 |
| --- | ---: | ---: | ---: |
| HSN | 51.3 | 16.2 | 5.18 |
| A. Hash + R_d | 51.1 | 16.2 | 5.18 |
| B. IGN + R_d | 52.0 | 15.8 | 5.27 |
| White (PCG hash) | 97.7 | 49.4 | 24.6 |
| FAST 128x128x32 texture | 51.0 | 19.9 | 9.96 |

**X4. 2-value integrands (R2 steps), no blur: RMSE x 1e-3 after N frames (box average) and under EMA alpha=0.1**

| Method | N=1 | N=4 | N=8 | N=16 | EMA 0.1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN | 394.1 | 131.3 | 84.3 | 51.2 | 50.3 |
| A. Hash + R_d | 393.8 | 131.3 | 84.4 | 51.2 | 50.3 |
| B. IGN + R_d | 391.0 | 129.9 | 84.5 | 51.0 | 50.3 |
| White (PCG hash) | 393.9 | 197.0 | 139.3 | 98.5 | 90.4 |
| FAST 128x128x32 texture | 394.1 | 152.8 | 88.6 | 54.5 | 53.7 |

**X4. 2-value integrands (R2 steps), 3x3 box: RMSE x 1e-3 after N frames (box average) and under EMA alpha=0.1**

| Method | N=1 | N=4 | N=8 | N=16 | EMA 0.1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN | 115.1 | 44.7 | 29.9 | 18.1 | 16.9 |
| A. Hash + R_d | 132.2 | 43.8 | 28.2 | 17.1 | 16.8 |
| B. IGN + R_d | 138.3 | 48.9 | 35.6 | 14.9 | 18.5 |
| White (PCG hash) | 131.4 | 65.7 | 46.5 | 32.8 | 30.2 |
| FAST 128x128x32 texture | 84.0 | 36.9 | 23.4 | 15.1 | 14.4 |

**X4. 2-value integrands (R2 steps), Gauss sigma 1: RMSE x 1e-3 after N frames (box average) and under EMA alpha=0.1**

| Method | N=1 | N=4 | N=8 | N=16 | EMA 0.1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN | 94.6 | 37.8 | 25.4 | 15.4 | 14.2 |
| A. Hash + R_d | 112.1 | 37.1 | 23.9 | 14.5 | 14.2 |
| B. IGN + R_d | 134.0 | 46.8 | 34.0 | 12.4 | 17.0 |
| White (PCG hash) | 111.4 | 55.7 | 39.4 | 27.8 | 25.6 |
| FAST 128x128x32 texture | 60.7 | 28.3 | 18.5 | 12.2 | 11.4 |

**X4. 2-value integrands (R2 steps), Gauss sigma 2: RMSE x 1e-3 after N frames (box average) and under EMA alpha=0.1**

| Method | N=1 | N=4 | N=8 | N=16 | EMA 0.1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN | 44.4 | 18.0 | 11.8 | 6.49 | 6.30 |
| A. Hash + R_d | 56.3 | 18.6 | 11.9 | 7.17 | 7.12 |
| B. IGN + R_d | 129.2 | 42.7 | 31.0 | 5.24 | 13.6 |
| White (PCG hash) | 56.0 | 28.1 | 19.8 | 13.9 | 12.8 |
| FAST 128x128x32 texture | 22.1 | 10.9 | 7.57 | 5.20 | 4.81 |

**X4. 2-value integrands (R2 steps): HSN error relative to A and B (below 1.00 means HSN is better)**

| Ratio | N=1 | N=4 | N=8 | N=16 | EMA 0.1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN / Hash + R_d, 3x3 box | 0.87 | 1.02 | 1.06 | 1.06 | 1.01 |
| HSN / Hash + R_d, Gauss s=1 | 0.84 | 1.02 | 1.07 | 1.06 | 1.00 |
| HSN / Hash + R_d, Gauss s=2 | 0.79 | 0.97 | 0.99 | 0.90 | 0.88 |
| HSN / IGN + R_d, 3x3 box | 0.83 | 0.91 | 0.84 | 1.22 | 0.91 |
| HSN / IGN + R_d, Gauss s=1 | 0.71 | 0.81 | 0.75 | 1.24 | 0.84 |
| HSN / IGN + R_d, Gauss s=2 | 0.34 | 0.42 | 0.38 | 1.24 | 0.46 |

**X4. 4-value integrands (R4 steps): per-pixel RMSE x 1e-3, no spatial filter**

| Method | N=16 | N=64 | N=256 |
| --- | ---: | ---: | ---: |
| HSN | 63.2 | 31.0 | 11.1 |
| A. Hash + R_d | 63.2 | 30.9 | 11.0 |
| B. IGN + R_d | 66.2 | 31.2 | 11.0 |
| White (PCG hash) | 113.8 | 57.3 | 28.4 |
| FAST 128x128x32 texture | 72.5 | 33.9 | 17.0 |

**X4. 4-value integrands (R4 steps), no blur: RMSE x 1e-3 after N frames (box average) and under EMA alpha=0.1**

| Method | N=1 | N=4 | N=8 | N=16 | EMA 0.1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN | 455.9 | 181.2 | 96.1 | 63.4 | 62.4 |
| A. Hash + R_d | 455.7 | 181.3 | 96.1 | 63.4 | 62.4 |
| B. IGN + R_d | 459.9 | 178.0 | 96.0 | 62.1 | 62.1 |
| White (PCG hash) | 455.8 | 227.9 | 161.1 | 114.0 | 104.5 |
| FAST 128x128x32 texture | 455.7 | 179.0 | 111.5 | 74.5 | 70.8 |

**X4. 4-value integrands (R4 steps), 3x3 box: RMSE x 1e-3 after N frames (box average) and under EMA alpha=0.1**

| Method | N=1 | N=4 | N=8 | N=16 | EMA 0.1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN | 135.7 | 58.2 | 33.4 | 21.2 | 20.2 |
| A. Hash + R_d | 152.2 | 60.6 | 32.1 | 21.2 | 20.8 |
| B. IGN + R_d | 188.2 | 82.0 | 41.4 | 26.5 | 28.6 |
| White (PCG hash) | 152.0 | 76.0 | 53.8 | 38.1 | 34.8 |
| FAST 128x128x32 texture | 107.6 | 49.8 | 34.0 | 23.7 | 22.0 |

**X4. 4-value integrands (R4 steps), Gauss sigma 1: RMSE x 1e-3 after N frames (box average) and under EMA alpha=0.1**

| Method | N=1 | N=4 | N=8 | N=16 | EMA 0.1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN | 112.2 | 48.8 | 28.5 | 18.0 | 17.1 |
| A. Hash + R_d | 129.0 | 51.4 | 27.2 | 18.0 | 17.6 |
| B. IGN + R_d | 183.7 | 79.9 | 39.4 | 24.8 | 27.1 |
| White (PCG hash) | 128.8 | 64.4 | 45.5 | 32.3 | 29.5 |
| FAST 128x128x32 texture | 82.7 | 40.5 | 28.3 | 20.0 | 18.4 |

**X4. 4-value integrands (R4 steps), Gauss sigma 2: RMSE x 1e-3 after N frames (box average) and under EMA alpha=0.1**

| Method | N=1 | N=4 | N=8 | N=16 | EMA 0.1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN | 53.3 | 23.6 | 14.0 | 8.97 | 8.37 |
| A. Hash + R_d | 64.8 | 25.9 | 13.6 | 9.06 | 8.84 |
| B. IGN + R_d | 177.1 | 76.7 | 35.7 | 21.2 | 24.1 |
| White (PCG hash) | 64.7 | 32.4 | 22.9 | 16.2 | 14.8 |
| FAST 128x128x32 texture | 38.5 | 19.7 | 14.0 | 10.1 | 9.23 |

**X4. 4-value integrands (R4 steps): HSN error relative to A and B (below 1.00 means HSN is better)**

| Ratio | N=1 | N=4 | N=8 | N=16 | EMA 0.1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| HSN / Hash + R_d, 3x3 box | 0.89 | 0.96 | 1.04 | 1.00 | 0.97 |
| HSN / Hash + R_d, Gauss s=1 | 0.87 | 0.95 | 1.05 | 1.00 | 0.97 |
| HSN / Hash + R_d, Gauss s=2 | 0.82 | 0.91 | 1.03 | 0.99 | 0.95 |
| HSN / IGN + R_d, 3x3 box | 0.72 | 0.71 | 0.81 | 0.80 | 0.71 |
| HSN / IGN + R_d, Gauss s=1 | 0.61 | 0.61 | 0.72 | 0.73 | 0.63 |
| HSN / IGN + R_d, Gauss s=2 | 0.30 | 0.31 | 0.39 | 0.42 | 0.35 |
