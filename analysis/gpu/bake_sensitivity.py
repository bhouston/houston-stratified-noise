# Does the grain ratio depend on the high-pass width, or on tone/relative scaling? -> results/gpu/bake_sensitivity.json
# Run: pnpm py analysis/gpu/bake_sensitivity.py
import json, numpy as np
from scipy.ndimage import gaussian_filter, binary_erosion
from paths import RAW, OUT
D, N = RAW + 'bake/', 1024
load = lambda name, c=3: np.fromfile(D + name, dtype=np.float32).reshape(N, N, c).astype(np.float64)
ref = load('bake_white_mean.f32'); mask = binary_erosion(load('bake_white_coverage.f32', 1)[..., 0] > 0, iterations=4)
imgs = {m: load(f'bake_{m}_r0.f32') for m in ('prev', 'shared', 'r2')}
out = {}
def grain(img, sigma, rel):
    w = np.maximum(gaussian_filter(mask.astype(float), sigma), 1e-6)[..., None]
    low = np.stack([gaussian_filter(img[..., c] * mask, sigma) for c in range(3)], -1) / w
    r = (img - low) / (np.maximum(low, 1e-3) if rel else 1)
    return float(np.sqrt(np.mean(r[mask] ** 2)))
for rel in (False, True):
    for sigma in (1.0, 1.5, 3.0, 6.0):
        g = {m: grain(i, sigma, rel) for m, i in imgs.items()}
        key = f"{'relative' if rel else 'absolute'} sigma={sigma}"
        out[key] = dict(shared_over_prev=g['shared'] / g['prev'], r2_over_prev=g['r2'] / g['prev'], **g)
        print(key, {k: round(v, 4) for k, v in out[key].items()})
# per-texel error against the reference with no filtering at all
for m, i in imgs.items(): print(m, 'RMSE', np.sqrt(np.mean((i - ref)[mask] ** 2)).round(4), 'relative RMSE', np.sqrt(np.mean((((i - ref) / np.maximum(ref, 1e-3)))[mask] ** 2)).round(4), 'mean signed error', (i - ref)[mask].mean().round(4))
json.dump(out, open(OUT + 'bake_sensitivity.json', 'w'), indent=1)
