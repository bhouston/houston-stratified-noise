# Real-time (post-TRAA, linear float readback) metrics from the harness output (RAW, see paths.py) -> results/gpu/realtime_metrics.json.
# Run: pnpm py analysis/gpu/analyze_realtime.py
#
# Per run (256 consecutive steady-state frames f_t, all pixels, RGB, linear scene units):
#   noise   = sqrt( mean over pixels of the per-pixel temporal variance )
#   bias    = RMS over pixels of ( mean_t f_t - reference )
#   rmse    = sqrt( noise^2 + bias^2 )  ==  RMS over frames and pixels of ( f_t - reference )
#   flicker = RMS over frames and pixels of ( f_t - f_{t-1} )
# bias_corrected removes the two known noise floors from bias in quadrature: the residual noise of the 256-frame
# mean (estimated from the disagreement between the repeats' means) and the noise of the reference.
import json, glob, os, itertools, numpy as np
from paths import RAW, OUT

out = {}
rms = lambda a: float(np.sqrt(np.mean(a ** 2)))

for fx in ('vxgi', 'ssr', 'ssr_only'):
    d = f'{RAW}{fx}/'
    mean = lambda name: np.fromfile(d + name + '_mean.f32', dtype=np.float32).astype(np.float64)
    info = lambda name: json.load(open(d + name + '.json'))
    whites = {n: mean(n) for n in ('white_base_s1', 'white_head_s2', 'white_base_s3', 'white_head_s4')}
    w = list(whites.values())
    ref = sum(w) / 4
    ref_noise = rms((w[0] + w[1]) / 2 - (w[2] + w[3]) / 2) / 2
    res = dict(reference='mean of 4 x 1024 post-TRAA linear frames rendered with white noise (2 runs on PR base, 2 on PR head)',
               resolution=[960, 720], frames_per_run=256, rms_signal=rms(ref), reference_noise=ref_noise,
               reference_base_vs_head=rms((w[0] + w[2]) / 2 - (w[1] + w[3]) / 2) / 2, variants={})

    def summarize(names, reference, ref_noise):
        means = [mean(n) for n in names]
        mean_noise = float(np.sqrt(np.mean([np.mean((a - b) ** 2) for a, b in itertools.combinations(means, 2)]) / 2))
        runs = []
        for n, m in zip(names, means):
            r = info(n)['result']
            bias = rms(m - reference)
            runs.append(dict(rmse=float(np.sqrt(r['temporalVariance'] + bias ** 2)), bias=bias,
                             bias_corrected=float(np.sqrt(max(0.0, bias ** 2 - mean_noise ** 2 - ref_noise ** 2))),
                             noise=float(np.sqrt(r['temporalVariance'])), flicker=float(np.sqrt(r['flickerMSE']))))
        keys = list(runs[0])
        return dict(runs=runs, noise_of_run_mean=mean_noise, mean={k: float(np.mean([r[k] for r in runs])) for k in keys},
                    sd={k: float(np.std([r[k] for r in runs], ddof=1)) for k in keys})

    for v in ('base', 'hhw', 'hash', 'ign', 'vc', 'hhwr2', 'e', 'er2', 'f', 'fr2', 'g'):
        names = sorted(os.path.basename(p)[:-5] for p in glob.glob(d + v + '_r?.json'))
        if names: res['variants'][v] = summarize(names, ref, ref_noise)
    # white-noise sampler itself: its 4 x 1024-frame runs, noise/flicker only (it is the reference, so no bias)
    wr = [info(n)['result'] for n in whites]
    res['white'] = dict(noise=float(np.mean([np.sqrt(r['temporalVariance']) for r in wr])), flicker=float(np.mean([np.sqrt(r['flickerMSE']) for r in wr])))

    fps_dir = f'{RAW}fps_{fx}/'
    if os.path.isdir(fps_dir):
        for v in ('base', 'hhw', 'hash', 'ign', 'hhwr2'):
            f = [json.load(open(p))['result']['fps'] for p in sorted(glob.glob(fps_dir + v + '_r?.json'))]
            if f: res['variants'][v]['fps'] = dict(runs=f, median=float(np.median(f)), min=min(f), max=max(f))
        ctl = [json.load(open(p))['result']['fps'] for p in sorted(glob.glob(fps_dir + 'hhwctl_r?.json'))]
        if ctl: res['fps_hhw_control_in_vc_session'] = dict(runs=ctl, median=float(np.median(ctl)), min=min(ctl), max=max(ctl))
        # later sessions on a busier GPU: fps of each variant relative to the HSN control of the same round
        fps = lambda name: {os.path.basename(p)[len(name) + 2:-5]: json.load(open(p))['result']['fps'] for p in glob.glob(fps_dir + name + '_r?.json')}
        for control, names in (('hhwctl', ['vc']), ('hsnctl2', ['hashctl2', 'e', 'er2', 'f', 'fr2']), ('hsnctl3', ['basectl3', 'hashctl3', 'g'])):
            c = fps(control)
            for name in names:
                f = fps(name)
                if f: res.setdefault('fps_relative_to_hsn_control', {})[name] = dict(control=[c[r] for r in sorted(f)], runs=[f[r] for r in sorted(f)], ratios=[f[r] / c[r] for r in sorted(f)], median_ratio=float(np.median([f[r] / c[r] for r in sorted(f)])))
    vc = sorted(glob.glob(d + 'vc_r?.json'))
    if vc: res['vc_texture'] = dict(bytes=json.load(open(vc[0]))['result']['vcTextureBytes'], generate_ms=[json.load(open(p))['result']['vcGenerateMs'] for p in vc])

    res['adapter'] = info('base_r0')['adapter']; res['chrome'] = info('base_r0')['chrome']
    out[fx] = res

    b = res['variants']['base']['mean']
    print(f"== {fx}: signal rms {res['rms_signal']:.4f}; reference noise {ref_noise:.2e}; base-vs-head white refs {res['reference_base_vs_head']:.2e}; white noise={res['white']['noise']:.3e} flicker={res['white']['flicker']:.3e}")
    for v, s in res['variants'].items():
        print(f"{v:6s}", ' '.join(f"{k}={s['mean'][k]:.3e}±{s['sd'][k]:.0e} ({(s['mean'][k] / b[k] - 1) * 100:+.1f}%)" for k in b), f"mean-noise={s['noise_of_run_mean']:.1e}", 'fps=%.1f [%.1f-%.1f]' % (s['fps']['median'], s['fps']['min'], s['fps']['max']) if 'fps' in s else '')

json.dump(out, open(OUT + 'realtime_metrics.json', 'w'), indent=1)
