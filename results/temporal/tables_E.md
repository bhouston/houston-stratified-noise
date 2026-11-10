
**E. Per-pixel temporal power spectrum, 1-value, 256 frames, mean over 4096 pixels.** Share of (non-DC) power below 1/16 and below 1/32 cycles per frame (white expects 11.7% and 5.5%), and the power an alpha=0.1 EMA lets through (white expects 0.053). "value" is the raw sample; "step" is the indicator u<0.3.

| Method | value: <1/16 | value: <1/32 | value: EMA pass | step: <1/16 | step: <1/32 | step: EMA pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| HSN (golden / R2 / R4 steps) | 1.70% | 0.29% | 0.0086 | 1.75% | 0.27% | 0.0082 |
| White (PCG hash) | 11.80% | 5.53% | 0.0492 | 11.76% | 5.48% | 0.0489 |
| Animated IGN (+ fixed pixel offset per dim) | 3.37% | 2.56% | 0.0132 | 4.15% | 3.89% | 0.0160 |
| Animated IGN, 64-frame cycle (old VXGI) | 3.06% | 0.47% | 0.0127 | 4.01% | 0.59% | 0.0152 |
| Analytic R2 (old SSR, RNoise.js) | 25.12% | 22.46% | 0.1313 | 26.04% | 23.22% | 0.1350 |
| R_d Weyl + white per-pixel offset | 1.70% | 0.29% | 0.0086 | 1.76% | 0.28% | 0.0082 |
| R_d Weyl + IGN per-pixel offset | 1.70% | 0.29% | 0.0086 | 1.75% | 0.27% | 0.0082 |
| V&C 64x64 + golden Weyl (shared step) | 1.70% | 0.29% | 0.0086 | 1.75% | 0.27% | 0.0082 |
| STBN 128x128x64 texture | 0.40% | 0.18% | 0.0056 | 1.43% | 0.63% | 0.0096 |
| FAST 128x128x32 texture | 0.91% | 0.30% | 0.0085 | 1.89% | 0.66% | 0.0118 |
