# Light map bake metrics from the harness output (RAW, see paths.py) -> results/gpu/bake_metrics.json. Run: pnpm py analysis/gpu/analyze_bake.py
import json, numpy as np
from scipy.ndimage import gaussian_filter, binary_erosion
from paths import RAW, OUT

D, N, SIGMA = RAW + 'bake/', 1024, 3.0
load = lambda name, c=3: np.fromfile(D + name, dtype=np.float32).reshape(N, N, c).astype(np.float64)

ref, half_a, half_b = load('bake_white_mean.f32'), load('bake_white_halfA.f32'), load('bake_white_halfB.f32')
covered = load('bake_white_coverage.f32', 1)[..., 0] > 0
mask = binary_erosion(covered, iterations=4)  # chart interiors only: no padding fill, no partially covered edge texels
m3 = mask[..., None]

def lowpass(img):  # Gaussian restricted to the mask (normalized convolution), so charts do not bleed into each other
    w = gaussian_filter(mask.astype(np.float64), SIGMA)
    return np.stack([gaussian_filter(img[..., c] * mask, SIGMA) for c in range(3)], -1) / np.maximum(w, 1e-6)[..., None]

rms = lambda a: float(np.sqrt(np.mean(a[mask] ** 2)))

def metrics(img):
    err = img - ref
    low = lowpass(err)
    return dict(rmse=rms(err), grain=rms(err - low), bias=rms(low), grain_noref=rms(img - lowpass(img)))

out = dict(method=dict(size=N, samples=64, lowpass_sigma_texels=SIGMA, texels=int(mask.sum()), covered_texels=int(covered.sum()),
                       reference='white noise, 128 x 64 = 8192 samples', mean_irradiance=float(ref[mask].mean())),
           reference_noise={k: v / 2 for k, v in metrics(ref + half_a - half_b).items() if k != 'grain_noref'},  # (A-B)/2 = noise of the full mean
           reference_grain_noref=rms(ref - lowpass(ref)), samplers={})

for mode in ('prev', 'shared', 'r2'):
    runs = [metrics(load(f'bake_{mode}_r{i}.f32')) for i in range(4)]
    out['samplers'][mode] = dict(runs=runs, mean={k: float(np.mean([r[k] for r in runs])) for k in runs[0]}, sd={k: float(np.std([r[k] for r in runs], ddof=1)) for k in runs[0]})

json.dump(out, open(OUT + 'bake_metrics.json', 'w'), indent=1)
print(json.dumps(out['method']), '\nreference noise', out['reference_noise'], 'ref grain_noref', out['reference_grain_noref'])
p = out['samplers']['prev']['mean']
for mode, s in out['samplers'].items():
    print(mode, ' '.join(f"{k}={s['mean'][k]:.5f}±{s['sd'][k]:.5f} ({s['mean'][k] / p[k]:.3f}x prev)" for k in p))
