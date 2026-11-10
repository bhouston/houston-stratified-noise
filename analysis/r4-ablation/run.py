"""Analytic R4 comparisons (part 1) and the HSN component ablation (part 2), on the temporal analysis harness.

From the repository root:
    pnpm analysis:r4-ablation                      # both parts, about 4 minutes on 8 cores
    pnpm py analysis/r4-ablation/run.py R4         # one part: R4 or ABL
    pnpm py analysis/r4-ablation/run.py vectors    # rewrite src/noise/r4-vectors.json for the JavaScript self-check

Writes results/r4-ablation/{R4,ABL}.json, tables_{R4,ABL}.md and .json, and figures/*.webp.  All seeds are fixed.
"""
import os
import itertools
import sys
from multiprocessing import Pool

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../temporal'))

import noises as N
from run_all import (BOX_STARTS, METHODS, PAD, T0, T_EMA, W, chi2_pair, e3, groups, md_table, newfig, pearson, plt, rms, running_rmse, save, savefig, spatial)
from extras import hash_rd
from integrands import INTS

U, F = np.uint32, np.float32
OUT = os.path.join(N.ROOT, 'results/r4-ablation')
_save, _savefig = save, savefig
save = lambda section, data, tables: _save(section, data, tables, OUT)
savefig = lambda fig, name: _savefig(fig, name, os.path.join(OUT, 'figures'))
FILTERS = ('none', 'box3', 'gauss1', 'gauss2')
FNAME = dict(none='no blur', box3='3x3 box', gauss1='Gauss s=1', gauss2='Gauss s=2')
BOX = (1, 4, 8, 16)


def coords(w, T, start=0):
    y, x = np.mgrid[0:w, 0:w]
    return x[None], y[None], (np.arange(T, dtype=np.int64) + start)[:, None, None]


def to_float(v):
    return (v >> U(8)).astype(F) / F(16777216)


def from_float(p):
    """float32 phase in [0,1) -> uint32 fixed point (24 significant bits)."""
    return (p * F(16777216)).astype(np.uint32) << U(8)


# ================================================================ part 1 samplers

P2 = 1.32471795724474602596  # plastic number (R2)
P4 = 1.1673039782614187      # root of x^5 = x + 1 (R4)


def analytic_r4_pr42(x, y, n, D, seed=47):
    """bhouston/three.js PR #42 (branch swarm/65-rnoise-channels, commit 8899ba3e) RNoise.js, verbatim, float32:
    the 32x32 tile is shifted by an R2 sequence of integer offsets; inside it t = cx + 32 cy + seed is an integer
    index and the output is fract((1/P, 1/P^2, 1/P^3, 1/P^4) * t + 0.5) with P^5 = P + 1."""
    fi = (np.asarray(n, np.int64) + seed).astype(F)
    ox = np.floor(N.fract(fi * F(0.7548776662)) * F(32))
    oy = np.floor(N.fract(fi * F(0.5698402910)) * F(32))
    cx = np.mod(np.asarray(x).astype(F) + ox, F(32))
    cy = np.mod(np.asarray(y).astype(F) + oy, F(32))
    t = cx + cy * F(32) + F(seed)
    return np.stack(np.broadcast_arrays(*[N.fract(F(1 / P4 ** (k + 1)) * t + F(0.5)) for k in range(D)])).astype(F)


SINGLE_K = 1.0


def analytic_single(x, y, n, D):
    """(i) Single lattice: t = x/P + y/P^2 (plastic P), u_k = fract((K t + n) * alpha_k), K = 1, float32.
    alpha = R4 constants for D = 4 and R2 constants for D = 2.  All values are functions of one scalar."""
    t = np.asarray(x).astype(F) * F(1 / P2) + np.asarray(y).astype(F) * F(1 / P2 ** 2)
    s = t * F(SINGLE_K) + np.asarray(n).astype(F)
    return np.stack(np.broadcast_arrays(*[N.fract(s * F(a)) for a in N.ALPHAS[D]])).astype(F)


A1, A2 = 1 / P2, 1 / P2 ** 2
# direction pairs (a_k, b_k): the R2 lattice, its 90 degree rotation, and the two 45 degree (index 2) images
PERDIM_DIRS = [(A1, A2), (-A2, A1), (A1 + A2, A2 - A1), (A1 - A2, A1 + A2)]


def analytic_perdim(x, y, n, D):
    """(ii) Per-dimension lattices: phase_k = fract(x a_k + y b_k) (float32, no hashing) + n * step_k in uint32,
    with HSN's steps (R2_STEPS for D = 2, R4_STEPS for D = 4)."""
    xf, yf, nu = np.asarray(x).astype(F), np.asarray(y).astype(F), N._u(n)
    out = [from_float(N.fract(xf * F(a) + yf * F(b))) + nu * U(s) for (a, b), s in zip(PERDIM_DIRS, N._steps(D))]
    return np.stack([to_float(v) for v in np.broadcast_arrays(*out)])


def plain_rd(x, y, n, D):
    """(iii) The R_d sequence indexed by frame with no spatial offset: every pixel identical.  0.5 + n * step."""
    shape = np.broadcast(np.asarray(x), np.asarray(y), np.asarray(n)).shape
    return np.stack([np.broadcast_to(to_float(U(0x80000000) + N._u(n) * U(s)), shape) for s in N._steps(D)])


# ---- variants E and F exactly as the in-engine harness measures them (analysis/gpu/harness/MeasureAnalyticR4.js):
# everything in uint32 0.32 fixed point, constants from Math.round(fract(v) * 2^32).

def fixed(v):
    return int(round((v - np.floor(v)) * 4294967296)) & 0xffffffff


R4_ALPHAS = [1 / P4 ** k for k in (1, 2, 3, 4)]
R2_ALPHAS = [1 / P2, 1 / P2 ** 2]
LATTICE_DIRECTIONS = [(A1, A2), (A2, 1 - A1), (A2, A1), (A1, 1 - A2)]


def engine_e(alphas, seed, K=1):
    """E, single lattice: value_k = fract((t K + n) alpha_k), t = x/P + y/P^2 + seed, computed as
    x * fixed(K a / P) + y * fixed(K a / P^2) + fixed(K a seed) + n * fixed(a) in uint32."""
    def fn(x, y, n, D):
        xu, yu, nu = N._u(x), N._u(y), N._u(n)
        out = [xu * U(fixed(K * a / P2)) + yu * U(fixed(K * a / P2 ** 2)) + U(fixed(K * a * seed)) + nu * U(fixed(a)) for a in alphas[:D]]
        return np.stack([to_float(v) for v in np.broadcast_arrays(*out)])
    return fn


def engine_f(alphas):
    """F, per-dimension lattices: value_k = fract(x a_k + y b_k + n alpha_k) in uint32, no seed."""
    def fn(x, y, n, D):
        xu, yu, nu = N._u(x), N._u(y), N._u(n)
        out = [xu * U(fixed(a)) + yu * U(fixed(b)) + nu * U(fixed(al)) for (a, b), al in zip(LATTICE_DIRECTIONS, alphas[:D])]
        return np.stack([to_float(v) for v in np.broadcast_arrays(*out)])
    return fn


def engine_e_auto(x, y, n, D):  # natural constants for the dimension count; seeds as the in-engine call sites (29 VXGI, 47 SSR)
    return engine_e(R4_ALPHAS, 47)(x, y, n, D) if D == 4 else engine_e(R2_ALPHAS, 29)(x, y, n, D)


def engine_f_auto(x, y, n, D):
    return engine_f(R4_ALPHAS if D == 4 else R2_ALPHAS)(x, y, n, D)


# the uint32 constants the in-engine harness uses
assert [fixed(a) for a in R4_ALPHAS] == [3679390609, 3152041523, 2700274806, 2313257605] and [fixed(a) for a in R2_ALPHAS] == [3242174889, 2447445414]
assert [fixed(a / P2) for a in R4_ALPHAS] == [2777489796, 2379405749, 2038377144, 1746226503] and [fixed(a / P2 ** 2) for a in R4_ALPHAS] == [2096665016, 1796160259, 1538725381, 1318187387]
assert [fixed(a / P2) for a in R2_ALPHAS] == [2447445414, 1847521882] and [fixed(a / P2 ** 2) for a in R2_ALPHAS] == [1847521882, 1394653007]
assert [(fixed(a), fixed(b)) for a, b in LATTICE_DIRECTIONS] == [(3242174889, 2447445414), (2447445414, 1052792407), (2447445414, 3242174889), (3242174889, 1847521882)]

ONLY_2 = {'E_r4', 'F_r4'}  # the two-value "first two R4 constants" forms that VXGI was measured with

R4_METHODS = {
    'hsn': ('HSN (R2 / R4 steps)', N.hsn, '#2f6fd0'),
    'hash': ('R_d sequence, hashed per-pixel offset', hash_rd, '#7a7a7a'),
    'vcr': ('V&C 64x64 + R_d steps', N.vc_rd, '#a0522d'),
    'fast': ('FAST 128x128x32 texture', N.fast, '#222222'),
    'stbn': ('STBN 128x128x64 texture', N.stbn, '#d6409f'),
    'ar2': ('Analytic R2 (old SSR, RNoise.js on dev)', N.analytic_r2_ssr, '#8e5bd0'),
    'pr42': ('Analytic R4, RNoise variant (fork PR #42)', analytic_r4_pr42, '#f28e2b'),
    'single': ('Analytic R_d, single lattice (i)', analytic_single, '#59a14f'),
    'perdim': ('Analytic R_d, per-dimension lattices (ii)', analytic_perdim, '#17a2b8'),
    'E': ('E (in-engine): single lattice, fixed point (R4; R2 constants for 2 values)', engine_e_auto, '#2ca02c'),
    'E_r4': ('E (in-engine): single lattice, first two R4 constants', engine_e(R4_ALPHAS, 29), '#98df8a'),
    'F': ('F (in-engine): per-dimension lattices (R4 steps; R2 steps for 2 values)', engine_f_auto, '#0b7285'),
    'F_r4': ('F (in-engine): per-dimension lattices, first two R4 steps', engine_f(R4_ALPHAS), '#66c2d1'),
    'plain': ('Plain R_d, no spatial offset (iii)', plain_rd, '#c9a227'),
    'white': ('White (PCG hash)', N.white, '#e8a800'),
}


# ================================================================ shared metrics

def evaluate(fn, D, gn='all', start=0):
    """Short-history errors, EMA and flicker for one sampler: {key: RMS over the integrand group}."""
    x, y, n = coords(W + 2 * PAD, T_EMA, start)
    s = fn(x, y, n, D)
    per = {}
    for name, grp, f, truth in INTS[D]:
        v = (f(s) - truth).astype(F)
        r = {}
        e = signal.lfilter([0.1], [1, -0.9], v, axis=0, zi=(0.9 * v[:1]))[0][T0:].astype(F)
        for fl in FILTERS:
            ef = spatial(e, fl)
            r[f'ema/{fl}'] = float(rms(ef))
            r[f'flicker/{fl}'] = float(rms(np.diff(ef, axis=0)))
            for c in BOX:
                r[f'box{c}/{fl}'] = float(rms(spatial(np.stack([v[st:st + c].mean(0) for st in BOX_STARTS]), fl)))
        c8 = v[:8, PAD:-PAD, PAD:-PAD]  # 8x8 window means of single frames: aligned to the tile grid and at every offset
        r['win8/aligned'] = float(rms(c8.reshape(8, W // 8, 8, W // 8, 8).mean((2, 4))))
        cs = np.cumsum(np.cumsum(np.pad(v[:8], ((0, 0), (1, 0), (1, 0))), 1), 2)
        allw = (cs[:, 8:, 8:] - cs[:, :-8, 8:] - cs[:, 8:, :-8] + cs[:, :-8, :-8]) / 64  # window whose corner is window pixel (i, j)
        unal = np.ones(allw.shape[1:], bool)
        unal[PAD % 8::8, PAD % 8::8] = False
        r['win8/unaligned'] = float(rms(allw[:, unal]))
        per[name] = r
    return {k: float(np.sqrt(np.mean([per[INTS[D][i][0]][k] ** 2 for i in groups(D)[gn]]))) for k in r}


def per_pixel(fn, D, counts, gn='all', start=0):
    x, y, n = coords(64, max(counts), start)
    per = running_rmse(fn(x, y, n, D).reshape(D, max(counts), -1), D)
    c = np.sqrt(np.mean([per[INTS[D][i][0]] ** 2 for i in groups(D)[gn]], 0))
    return [float(c[k - 1]) for k in counts], c.tolist()


_fy, _fx = np.meshgrid(np.fft.fftfreq(128), np.fft.fftfreq(128), indexing='ij')
_R = np.hypot(_fx, _fy)
_SECTOR = (np.floor((np.arctan2(_fy, _fx) % np.pi) / np.pi * 16).astype(int)) % 16
_BAND = (_R > 0.03) & (_R < 0.5)
_HANN = np.outer(np.hanning(128), np.hanning(128))
_GRID8 = np.zeros((128, 128), bool)
_GRID8[::16, ::16] = True
_GRID8[0, 0] = False


def mask_stats(u):
    """50% threshold mask of one 128x128 frame: largest spectral bin share, angular anisotropy, low-frequency share
    (Hann window), and the share of power exactly on multiples of 1/8 cycle per pixel (no window)."""
    m = (u < 0.5).astype(np.float64)
    p = np.abs(np.fft.fft2((m - m.mean()) * _HANN)) ** 2
    p[0, 0] = 0
    sect = np.array([p[_BAND & (_SECTOR == k)].mean() for k in range(16)])
    q = np.abs(np.fft.fft2(m - m.mean())) ** 2
    return dict(peak=float(p.max() / p.sum()), aniso=float(sect.std() / sect.mean()), lf=float(p[_R < 1 / 8].sum() / p.sum()), grid8=float(q[_GRID8].sum() / q.sum()))


def frame_stats(fn, D, frames=(0, 1, 2, 3), start=0):
    """Mean over frames (and worst dimension) of the mask statistics, plus histogram uniformity of the value field."""
    x, y, n = coords(128, len(frames), start)
    s = fn(x, y, np.asarray(frames, np.int64)[:, None, None] + start, D)
    st = [[mask_stats(s[d, i]) for i in range(len(frames))] for d in range(D)]
    out = {}
    for k in ('peak', 'aniso', 'lf', 'grid8'):
        per_dim = [float(np.mean([f[k] for f in st[d]])) for d in range(D)]
        out[k] = float(np.mean(per_dim)); out[k + '_worst'] = float(max(per_dim))
    for bins in (64, 256):
        h = np.stack([np.bincount(np.minimum((s[0, i] * bins).astype(int), bins - 1).ravel(), minlength=bins) for i in range(len(frames))])
        ex = 128 * 128 / bins
        out[f'hist{bins}'] = float((((h - ex) ** 2 / ex).sum(1) / (bins - 1)).mean())
    return out


def correlations(fn, D):
    x, y, n = coords(64, 1024)
    s = fn(x, y, n, D).reshape(D, 1024, -1)
    x, y, n = coords(128, 16)
    sp = fn(x, y, n, D).reshape(D, 16, -1)
    r = dict(t_r=0, t_chi=0, s_r=0, s_chi=0)
    for i, j in itertools.combinations(range(D), 2):
        r['t_r'] = max(r['t_r'], float(np.abs(pearson(s[i], s[j])).mean()))
        r['t_chi'] = max(r['t_chi'], chi2_pair(s[i], s[j], 8))
        r['s_r'] = max(r['s_r'], float(np.abs(pearson(sp[i].T, sp[j].T)).mean()))
        r['s_chi'] = max(r['s_chi'], chi2_pair(sp[i].T, sp[j].T, 16))
    return r


# ================================================================ part 1 driver

STARTS = [0, 10 ** 5, 10 ** 6, 10 ** 7]


def r4_worker(args):
    k, D = args
    fn = R4_METHODS[k][1]
    pp, curve = per_pixel(fn, D, [16, 64, 256, 1024])
    return (k, D), dict(ev=evaluate(fn, D), pp=pp, curve=curve, long=[per_pixel(fn, D, [64], start=s0)[0][0] for s0 in STARTS], corr=correlations(fn, D), frame=frame_stats(fn, D))


def part_r4():
    with Pool(8) as pool:
        res = dict(pool.map(r4_worker, [(k, D) for D in (4, 2) for k in R4_METHODS if D == 2 or k not in ONLY_2]))
    t = ''
    lab = lambda k: R4_METHODS[k][0]
    for D in (4, 2):
        ttl = f'{D} values per pixel ({len(INTS[D])} {D}D integrands' + (', R4 constants)' if D == 4 else ', R2 constants; the two RNoise variants use their first two outputs)')
        g = lambda k: res[(k, D)]
        MK = [k for k in R4_METHODS if (k, D) in res]
        t += f'\n**R4-{D}.1 {ttl}: per-pixel RMSE x 1e-3 with no spatial filter, and a 64-frame average started at a large frame index**\n\n'
        t += md_table(['Method', 'N=16', 'N=64', 'N=256', 'N=1024', '64 fr. @1e5', '64 fr. @1e6', '64 fr. @1e7'], [[lab(k)] + [e3(v) for v in g(k)['pp']] + [e3(v) for v in g(k)['long'][1:]] for k in MK])
        for fl in FILTERS[1:]:
            t += f'\n**R4-{D}.2 {ttl}, {FNAME[fl]}: RMSE x 1e-3 after N frames (box average) and under EMA alpha=0.1; flicker = RMS frame-to-frame change of the EMA output**\n\n'
            t += md_table(['Method'] + [f'N={c}' for c in BOX] + ['EMA 0.1', 'flicker'], [[lab(k)] + [e3(g(k)['ev'][f'box{c}/{fl}']) for c in BOX] + [e3(g(k)['ev'][f'ema/{fl}']), e3(g(k)['ev'][f'flicker/{fl}'])] for k in MK])
        t += f'\n**R4-{D}.3 {ttl}: error relative to HSN (above 1.00 means worse than HSN)**\n\n'
        rows = []
        for k in [m for m in ('pr42', 'single', 'perdim', 'E', 'E_r4', 'F', 'F_r4', 'plain', 'hash', 'ar2') if m in MK]:
            for fl in FILTERS[1:]:
                rows.append([f'{lab(k)}, {FNAME[fl]}'] + [f"{g(k)['ev'][f'box{c}/{fl}'] / g('hsn')['ev'][f'box{c}/{fl}']:.2f}" for c in BOX] + [f"{g(k)['ev'][f'ema/{fl}'] / g('hsn')['ev'][f'ema/{fl}']:.2f}"])
        t += md_table(['Method / HSN'] + [f'N={c}' for c in BOX] + ['EMA 0.1'], rows)
        t += f'\n**R4-{D}.4 {ttl}: dependence between dimensions and single-frame spectrum.** Worst pair of |Pearson r| and chi-square/dof over time at a pixel (1024 frames; white expects 0.025 and 1.0) and across pixels in a frame (128x128; white expects 0.006 and 1.0). Spectrum of each dimension\'s 50% threshold mask (128x128, Hann window, mean of frames 0-3): largest single bin as a share of total power and angular anisotropy (std/mean of power over 16 direction sectors), mean over dimensions and worst dimension.\n\n'
        t += md_table(['Method', 'time |r|', 'time chi2', 'space |r|', 'space chi2', 'peak bin (mean)', 'peak bin (worst)', 'anisotropy (mean)', 'anisotropy (worst)', 'low-freq share'],
                      [[lab(k), f"{g(k)['corr']['t_r']:.3f}", f"{g(k)['corr']['t_chi']:.2f}", f"{g(k)['corr']['s_r']:.3f}", f"{g(k)['corr']['s_chi']:.1f}", f"{g(k)['frame']['peak'] * 100:.3f}%", f"{g(k)['frame']['peak_worst'] * 100:.3f}%",
                        f"{g(k)['frame']['aniso']:.2f}", f"{g(k)['frame']['aniso_worst']:.2f}", f"{g(k)['frame']['lf'] * 100:.2f}%"] for k in MK])
    save('R4', {f'{k}/{D}': v for (k, D), v in res.items()}, t)

    # swatches
    ks = ['hsn', 'hash', 'pr42', 'E', 'F', 'ar2', 'fast', 'white']
    rows = ['value, dimension 1', '50% mask, dimension 1', '50% mask, dimension 3', '50% mask, dimension 4']
    fig, axs = newfig('Analytic R4 samplers against HSN: one frame of four values per pixel',
                      '96x96 pixel crops of frame 0. The hash-free lattice samplers show diagonal lattice lines or bands; HSN, the hashed offset and FAST do not.', 4, len(ks), 9.6, top_in=1.45)
    fig.subplots_adjust(left=0.09, right=0.995, wspace=0.03, hspace=0.03, bottom=0.01)
    x, y, n = coords(96, 1)
    for c, k in enumerate(ks):
        s = R4_METHODS[k][1](x, y, n, 4)[:, 0]
        for r, im in enumerate([s[0], s[0] < 0.5, s[2] < 0.5, s[3] < 0.5]):
            ax = axs[r][c]
            ax.imshow(im.astype(float), cmap='gray', vmin=0, vmax=1, interpolation='nearest')
            ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
            if r == 0:
                ax.set_title(R4_METHODS[k][0].split(' (')[0].replace(' 128x128x32 texture', '').replace(', hashed per-pixel offset', ' + hash').replace('Analytic R_d, ', '').replace('Analytic R4, ', 'R4 ').replace('R_d sequence', 'R4').replace('E (in-engine): single lattice, fixed point', 'E: single lattice').replace('F (in-engine): per-dimension lattices', 'F: per-dimension lattices'), fontsize=10.5, weight='bold' if k == 'hsn' else 'normal')
            if c == 0:
                ax.set_ylabel(rows[r], fontsize=10.5)
    savefig(fig, 'r4_swatches')

    # EMA bars
    fig, axs = newfig('Analytic R4 samplers against HSN: error after temporal accumulation and a spatial filter',
                      'Steady-state RMSE under an exponential moving average (alpha = 0.1) with no blur, a 3x3 box, or a Gaussian (sigma 1, 2). Log scale; lower is better.', 1, 2, 8.4, top_in=1.95)
    fig.subplots_adjust(left=0.36, wspace=0.08, bottom=0.085)
    for ax, D in zip(axs[0], (2, 4)):
        for r, k in enumerate(R4_METHODS):
            if (k, D) not in res:
                continue
            for i, fl in enumerate(FILTERS):
                ax.barh(r + (i - 1.5) * 0.2, res[(k, D)]['ev'][f'ema/{fl}'], height=0.19, color=R4_METHODS[k][2], alpha=[1.0, 0.75, 0.5, 0.3][i], label=FNAME[fl].replace('s=', 'σ=') if k == 'hsn' else None)
        ax.set_xscale('log'); ax.set_ylim(len(R4_METHODS) - 0.5, -0.5); ax.set_title(f'{D} values per pixel'); ax.set_xlabel('steady-state RMSE'); ax.grid(axis='y', visible=False)
        ax.set_yticks(range(len(R4_METHODS))); ax.set_yticklabels([lab(k) for k in R4_METHODS] if D == 2 else [])
        if D == 2:
            ax.get_yticklabels()[0].set_weight('bold')
            fig.legend(*ax.get_legend_handles_labels(), loc='upper left', bbox_to_anchor=(0.02, 1 - 1.0 / 8.4), ncol=4, frameon=False, fontsize=11, title='Spatial filter (darkest to lightest):', title_fontsize=11, alignment='left')
    savefig(fig, 'r4_ema_spatial')

    # per-pixel convergence
    fig, axs = newfig('Analytic R4 samplers against HSN: per-pixel convergence',
                      'RMSE of each pixel\'s running mean over N frames, 64x64 pixels, no spatial filter. Log-log; lower is better.', 1, 2, 9.0, top_in=2.3)
    hs = {}
    for ax, D in zip(axs[0], (2, 4)):
        for k in reversed([m for m in R4_METHODS if (m, D) in res]):
            hs[k], = ax.loglog(np.arange(1, 1025), res[(k, D)]['curve'], color=R4_METHODS[k][2], lw=3.4 if k == 'hsn' else 1.9, zorder=5 if k == 'hsn' else 2)
        ax.set_xscale('log', base=2); ax.set_xlim(1, 1024); ax.set_xticks([2 ** i for i in range(11)]); ax.set_xticklabels([2 ** i for i in range(11)])
        ax.set_title(f'{D} values per pixel'); ax.set_xlabel('frames averaged per pixel (N)'); ax.set_ylabel('RMSE')
    fig.legend([hs[k] for k in R4_METHODS], [lab(k) for k in R4_METHODS], loc='upper left', bbox_to_anchor=(0.02, 1 - 1.05 / 9.0), ncol=4, frameon=False, fontsize=11)
    savefig(fig, 'r4_convergence')


# ================================================================ part 2: HSN ablation

def hsn_variant(levels=3, scramble=True, phase=True, hierarchy=True, steps='per', time='int'):
    """Generalised HSN.  levels: hierarchy depth (tile = 2^levels pixels); scramble: per-parent hashed permutation
    (off = plain Bayer order); phase: hashed per-tile offset; hierarchy=False: a per-pixel hash is the whole phase;
    steps: 'per' (golden / R2 / R4) or 'shared' (golden everywhere); time: 'int' (uint32), 'float' (float32
    frame * alpha) or 'static' (no temporal step).  The defaults reproduce noises.hsn exactly."""
    def fn(x, y, n, D):
        xu, yu, nu = N._u(x), N._u(y), N._u(n)
        out = []
        for k in range(D):
            seed = k + 1
            step = N.GOLDEN_STEP if steps == 'shared' else N._steps(D)[k]
            if hierarchy:
                v = np.zeros(np.broadcast(xu, yu).shape, np.uint32)
                for level in range(levels):
                    a, b = (xu >> U(level)) & U(1), (yu >> U(level)) & U(1)
                    if scramble:
                        scr = N.pixel_hash(xu >> U(level + 1), yu >> U(level + 1), seed ^ (((level + 1) * 0x632be5ab) & 0xffffffff))
                        child = (((a ^ b) << U(1)) | np.where((scr & U(4)) != 0, a, b)) ^ (scr & U(3))
                    else:
                        child = ((a ^ b) << U(1)) | b
                    v = v | (child << U(30 - 2 * level))
                if phase:
                    v = v + N.pixel_hash(xu >> U(levels), yu >> U(levels), seed ^ 0x02e5be93)
            else:
                v = N.pixel_hash(xu, yu, seed ^ 0x02e5be93)
            if time == 'int':
                out.append(to_float(v + nu * U(step)))
            elif time == 'static':
                out.append(to_float(v + np.zeros_like(nu)))
            else:
                out.append(N.fract(to_float(v) + np.asarray(n).astype(F) * F(step / 2 ** 32)))
        return np.stack(np.broadcast_arrays(*out)).astype(F)
    return fn


VARIANTS = {
    'full': ('1. Full HSN', dict(), 0),
    'bayer_phase': ('2. No per-parent scramble (Bayer hierarchy + tile phase)', dict(scramble=False), 0),
    'scr_nophase': ('3. No tile phase (scrambled hierarchy only)', dict(phase=False), 0),
    'bayer': ('4. Neither (tiled Bayer 8x8)', dict(scramble=False, phase=False), 0),
    'hash': ('5. Hash phase only, no hierarchy', dict(hierarchy=False), 0),
    'depth1': ('6a. Hierarchy depth 1 (2x2 tiles)', dict(levels=1), 0),
    'depth2': ('6b. Hierarchy depth 2 (4x4 tiles)', dict(levels=2), 0),
    'depth4': ('6d. Hierarchy depth 4 (16x16 tiles)', dict(levels=4), 0),
    'shared': ('7. Shared temporal step', dict(steps='shared'), 0),
    'static': ('8. No temporal step (static pattern)', dict(time='static'), 0),
    'int1e5': ('9. uint32 time, frames from 1e5', dict(), 10 ** 5),
    'float1e5': ('9. float32 time, frames from 1e5', dict(time='float'), 10 ** 5),
    'int1e6': ('9. uint32 time, frames from 1e6', dict(), 10 ** 6),
    'float1e6': ('9. float32 time, frames from 1e6', dict(time='float'), 10 ** 6),
    'int1e7': ('9. uint32 time, frames from 1e7', dict(), 10 ** 7),
    'float1e7': ('9. float32 time, frames from 1e7', dict(time='float'), 10 ** 7),
}


def abl_worker(k):
    name, kw, start = VARIANTS[k]
    fn = hsn_variant(**kw)
    r = dict(frame=frame_stats(fn, 1, start=start))
    for D in (1, 2, 4):
        r[f'ev{D}'] = evaluate(fn, D, start=start)
        if D < 4:
            r[f'pp{D}'] = per_pixel(fn, D, [64, 256], start=start)[0]
    return k, r


def part_abl():
    x, y, n = coords(64, 8)
    assert np.array_equal(hsn_variant()(x, y, n, 4), N.hsn(x, y, n, 4)) and np.array_equal(hsn_variant()(x, y, n, 1), N.hsn(x, y, n, 1))
    with Pool(8) as pool:
        res = dict(pool.map(abl_worker, list(VARIANTS)))
    lab = lambda k: VARIANTS[k][0]
    g = lambda k, key, sub: res[k][key][sub]
    t = '\n**ABL.1 Single frame, one value per pixel: histogram and spectrum.** Histogram: chi-square/dof of the 128x128 value field in 64 and 256 equal bins (white expects 1.0; 0 is exactly uniform). 50% threshold mask (Hann window, mean of 4 frames): largest spectral bin as a share of power (white about 0.05%), angular anisotropy (std/mean over 16 direction sectors), share of power below 1/8 cycle/pixel (white 4.9%), and share of power exactly on multiples of 1/8 cycle/pixel (no window; white expects 0.38%).\n\n'
    t += md_table(['Variant', 'hist 64 bins', 'hist 256 bins', 'largest bin', 'anisotropy', 'low-freq share', 'power on 1/8 multiples'],
                  [[lab(k), f"{g(k, 'frame', 'hist64'):.3f}", f"{g(k, 'frame', 'hist256'):.3f}", f"{g(k, 'frame', 'peak') * 100:.3f}%", f"{g(k, 'frame', 'aniso'):.2f}", f"{g(k, 'frame', 'lf') * 100:.2f}%", f"{g(k, 'frame', 'grid8') * 100:.2f}%"] for k in VARIANTS])
    t += '\n**ABL.2 Single frame, spatial filters: RMSE x 1e-3.** 8x8 window mean of one frame (aligned with the tile grid, and at every other offset), then 3x3 box and Gaussian sigma 1 and 2, for one value (10 1D integrands) and two values (14 2D integrands).\n\n'
    t += md_table(['Variant', '1v 8x8 aligned', '1v 8x8 unaligned', '1v 3x3', '1v Gauss 1', '1v Gauss 2', '2v 8x8 aligned', '2v 8x8 unaligned', '2v 3x3', '2v Gauss 1', '2v Gauss 2'],
                  [[lab(k)] + [e3(g(k, f'ev{D}', key)) for D in (1, 2) for key in ('win8/aligned', 'win8/unaligned', 'box1/box3', 'box1/gauss1', 'box1/gauss2')] for k in VARIANTS])
    t += '\n**ABL.3 Over time: RMSE x 1e-3.** EMA alpha=0.1 + Gaussian sigma 1 for 1, 2 and 4 values; per-pixel running mean with no spatial filter at N = 64 and 256 for 1 and 2 values; flicker = RMS frame-to-frame change of the EMA + Gaussian sigma 1 output.\n\n'
    t += md_table(['Variant', 'EMA+G1, 1v', 'EMA+G1, 2v', 'EMA+G1, 4v', 'per-pixel N=64, 1v', 'N=256, 1v', 'N=64, 2v', 'N=256, 2v', 'flicker 1v', 'flicker 2v'],
                  [[lab(k)] + [e3(g(k, f'ev{D}', 'ema/gauss1')) for D in (1, 2, 4)] + [e3(v) for D in (1, 2) for v in res[k][f'pp{D}']] + [e3(g(k, f'ev{D}', 'flicker/gauss1')) for D in (1, 2)] for k in VARIANTS])
    t += '\n**ABL.4 Short windows with Gaussian sigma 1: RMSE x 1e-3 after N frames, one and two values.**\n\n'
    t += md_table(['Variant'] + [f'{D}v N={c}' for D in (1, 2) for c in BOX], [[lab(k)] + [e3(g(k, f'ev{D}', f'box{c}/gauss1')) for D in (1, 2) for c in BOX] for k in VARIANTS])

    # summary: component -> purpose -> metric -> with / without
    pct = lambda v: f'{v * 100:.3f}%'
    S = []
    add = lambda comp, purpose, metric, with_, without, fmt=e3: S.append([comp, purpose, metric, fmt(with_), fmt(without), f'{without / with_:.2f}x' if with_ else '-'])
    # note: the 'Tile phase (vs none, without scramble)' rows compare variant 2 (with) against variant 4 (without)
    add('Hierarchy (vs per-pixel hash phase)', 'stratify values inside every small footprint', 'single frame, Gauss s=1, 1 value', g('full', 'ev1', 'box1/gauss1'), g('hash', 'ev1', 'box1/gauss1'))
    add('', '', 'single frame, Gauss s=1, 2 values', g('full', 'ev2', 'box1/gauss1'), g('hash', 'ev2', 'box1/gauss1'))
    add('', '', 'EMA 0.1 + Gauss s=1, 1 value', g('full', 'ev1', 'ema/gauss1'), g('hash', 'ev1', 'ema/gauss1'))
    add('', '', 'EMA 0.1 + Gauss s=1, 2 values', g('full', 'ev2', 'ema/gauss1'), g('hash', 'ev2', 'ema/gauss1'))
    add('', '', 'low-frequency share of 50% mask', g('full', 'frame', 'lf'), g('hash', 'frame', 'lf'), pct)
    add('Per-parent scramble (vs Bayer order, tile phase kept)', 'remove the regular ordered-dither pattern', 'largest spectral bin of 50% mask', g('full', 'frame', 'peak'), g('bayer_phase', 'frame', 'peak'), pct)
    add('', '', 'anisotropy of 50% mask', g('full', 'frame', 'aniso'), g('bayer_phase', 'frame', 'aniso'), lambda v: f'{v:.2f}')
    add('', 'decorrelate the dimensions (Bayer gives every seed the same rank order)', 'single frame, Gauss s=1, 2 values', g('full', 'ev2', 'box1/gauss1'), g('bayer_phase', 'ev2', 'box1/gauss1'))
    add('', '', 'EMA 0.1 + Gauss s=1, 2 values', g('full', 'ev2', 'ema/gauss1'), g('bayer_phase', 'ev2', 'ema/gauss1'))
    add('', '', 'EMA 0.1 + Gauss s=1, 4 values', g('full', 'ev4', 'ema/gauss1'), g('bayer_phase', 'ev4', 'ema/gauss1'))
    add('', 'cost', 'single frame, Gauss s=1, 1 value', g('full', 'ev1', 'box1/gauss1'), g('bayer_phase', 'ev1', 'box1/gauss1'))
    add('', 'cost', 'EMA 0.1 + Gauss s=1, 1 value', g('full', 'ev1', 'ema/gauss1'), g('bayer_phase', 'ev1', 'ema/gauss1'))
    add('', 'cost', 'flicker, EMA + Gauss s=1, 1 value', g('full', 'ev1', 'flicker/gauss1'), g('bayer_phase', 'ev1', 'flicker/gauss1'))
    add('Tile phase (vs none, scramble kept)', 'hide the 8-pixel tile grid; continuous values', 'power on multiples of 1/8 cycle/pixel', g('full', 'frame', 'grid8'), g('scr_nophase', 'frame', 'grid8'), pct)
    add('', '', 'histogram chi2/dof, 256 bins', g('full', 'frame', 'hist256'), g('scr_nophase', 'frame', 'hist256'), lambda v: f'{v:.3f}')
    add('', '(no measurable effect)', 'unaligned 8x8 window mean, 1 value', g('full', 'ev1', 'win8/unaligned'), g('scr_nophase', 'ev1', 'win8/unaligned'))
    add('', '(no measurable effect)', 'single frame, Gauss s=2, 1 value', g('full', 'ev1', 'box1/gauss2'), g('scr_nophase', 'ev1', 'box1/gauss2'))
    add('', '(no measurable effect)', 'EMA 0.1 + Gauss s=1, 2 values', g('full', 'ev2', 'ema/gauss1'), g('scr_nophase', 'ev2', 'ema/gauss1'))
    add('Tile phase (vs none, without scramble)', 'breaks up the tiled Bayer matrix', 'largest spectral bin of 50% mask', g('bayer_phase', 'frame', 'peak'), g('bayer', 'frame', 'peak'), pct)
    add('', '', 'power on multiples of 1/8 cycle/pixel', g('bayer_phase', 'frame', 'grid8'), g('bayer', 'frame', 'grid8'), pct)
    add('Scramble + phase (vs tiled Bayer 8x8)', 'both together', 'largest spectral bin of 50% mask', g('full', 'frame', 'peak'), g('bayer', 'frame', 'peak'), pct)
    add('', 'cost', 'single frame, Gauss s=1, 1 value', g('full', 'ev1', 'box1/gauss1'), g('bayer', 'ev1', 'box1/gauss1'))
    add('', 'cost', 'single frame, Gauss s=2, 1 value', g('full', 'ev1', 'box1/gauss2'), g('bayer', 'ev1', 'box1/gauss2'))
    add('', 'cost', 'unaligned 8x8 window mean, 1 value', g('full', 'ev1', 'win8/unaligned'), g('bayer', 'ev1', 'win8/unaligned'))
    add('Hierarchy', 'exact stratification of every aligned 8x8 tile', 'aligned 8x8 window mean, 1 value', g('full', 'ev1', 'win8/aligned'), g('hash', 'ev1', 'win8/aligned'))
    add('', '(lost when the window straddles tiles)', 'unaligned 8x8 window mean, 1 value', g('full', 'ev1', 'win8/unaligned'), g('hash', 'ev1', 'win8/unaligned'))
    add('Three levels (vs one level)', 'stratify at 2, 4 and 8 pixels', 'single frame, Gauss s=2, 1 value', g('full', 'ev1', 'box1/gauss2'), g('depth1', 'ev1', 'box1/gauss2'))
    add('', '', 'EMA 0.1 + Gauss s=1, 2 values', g('full', 'ev2', 'ema/gauss1'), g('depth1', 'ev2', 'ema/gauss1'))
    add('Three levels (vs two)', '', 'single frame, Gauss s=2, 1 value', g('full', 'ev1', 'box1/gauss2'), g('depth2', 'ev1', 'box1/gauss2'))
    add('Three levels (vs four)', 'a fourth level', 'single frame, Gauss s=2, 1 value', g('full', 'ev1', 'box1/gauss2'), g('depth4', 'ev1', 'box1/gauss2'))
    add('', '', 'EMA 0.1 + Gauss s=1, 1 value', g('full', 'ev1', 'ema/gauss1'), g('depth4', 'ev1', 'ema/gauss1'))
    add('Per-dimension steps (vs shared golden step)', 'keep a pixel\'s dimensions independent over time', 'per pixel, N=256, 2 values', res['full']['pp2'][1], res['shared']['pp2'][1])
    add('', '', 'EMA 0.1 + Gauss s=1, 2 values', g('full', 'ev2', 'ema/gauss1'), g('shared', 'ev2', 'ema/gauss1'))
    add('', '', 'EMA 0.1 + Gauss s=1, 4 values', g('full', 'ev4', 'ema/gauss1'), g('shared', 'ev4', 'ema/gauss1'))
    add('Weyl temporal step (vs static pattern)', 'converge over time at each pixel', 'per pixel, N=64, 1 value', res['full']['pp1'][0], res['static']['pp1'][0])
    add('', '', 'EMA 0.1 + Gauss s=1, 1 value', g('full', 'ev1', 'ema/gauss1'), g('static', 'ev1', 'ema/gauss1'))
    add('', 'cost', 'flicker, EMA + Gauss s=1, 1 value', g('full', 'ev1', 'flicker/gauss1'), g('static', 'ev1', 'flicker/gauss1'))
    for nm in ('1e5', '1e6', '1e7'):
        add(f'uint32 time (vs float32) from frame {nm}', 'no precision loss at large frame index', 'per pixel, N=64, 1 value', res['int' + nm]['pp1'][0], res['float' + nm]['pp1'][0])
        add('', '', 'EMA 0.1 + Gauss s=1, 2 values', g('int' + nm, 'ev2', 'ema/gauss1'), g('float' + nm, 'ev2', 'ema/gauss1'))
    t = '\n**ABL.0 Summary: what each HSN component buys.** RMSE values x 1e-3; "ratio" is without / with (above 1 means the component helps on that metric, below 1 means it costs).\n\n' + md_table(['Component', 'What it is for', 'Metric', 'With (full HSN)', 'Without', 'Ratio'], S) + t
    save('ABL', dict(results=res, summary=S), t)

    # swatches: mask and spectrum of each spatial variant
    ks = ['full', 'bayer_phase', 'scr_nophase', 'bayer', 'hash', 'depth1', 'depth2', 'depth4']
    names = ['Full HSN', 'No scramble\n(Bayer + tile phase)', 'No tile phase', 'Neither\n(tiled Bayer 8x8)', 'Hash phase only', 'Depth 1', 'Depth 2', 'Depth 4']
    fig, axs = newfig('HSN with one spatial component removed at a time', 'Top: 50% threshold mask of one frame (96x96 pixels). Bottom: its power spectrum (128x128, log scale, zero frequency in the centre).', 2, len(ks), 5.9, top_in=1.75)
    fig.subplots_adjust(left=0.035, right=0.995, wspace=0.03, hspace=0.03, bottom=0.01)
    x, y, n = coords(128, 1)
    for c, k in enumerate(ks):
        u = hsn_variant(**VARIANTS[k][1])(x, y, n, 1)[0, 0]
        m = (u < 0.5).astype(float)
        p = np.fft.fftshift(np.abs(np.fft.fft2((m - m.mean()) * _HANN)) ** 2)
        axs[0][c].imshow(m[:96, :96], cmap='gray', vmin=0, vmax=1, interpolation='nearest')
        axs[1][c].imshow(np.log10(p / p.sum() + 1e-9), cmap='gray', vmin=-6.5, vmax=-2.5, interpolation='nearest')
        axs[0][c].set_title(names[c], fontsize=10.5, weight='bold' if k == 'full' else 'normal')
        for r in (0, 1):
            axs[r][c].set_xticks([]); axs[r][c].set_yticks([]); axs[r][c].grid(False)
    axs[0][0].set_ylabel('50% mask'); axs[1][0].set_ylabel('spectrum')
    savefig(fig, 'ablation_swatches')

    # metric bars
    panels = [('Single frame, Gauss σ=1, 1 value', lambda k: g(k, 'ev1', 'box1/gauss1')), ('Single frame, Gauss σ=1, 2 values', lambda k: g(k, 'ev2', 'box1/gauss1')),
              ('EMA 0.1 + Gauss σ=1, 1 value', lambda k: g(k, 'ev1', 'ema/gauss1')), ('EMA 0.1 + Gauss σ=1, 2 values', lambda k: g(k, 'ev2', 'ema/gauss1')),
              ('Per pixel, N=256, 2 values, no filter', lambda k: res[k]['pp2'][1]), ('Largest spectral bin of 50% mask', lambda k: g(k, 'frame', 'peak'))]
    ks = [k for k in VARIANTS if not k.startswith('int')]
    from matplotlib.ticker import NullFormatter
    fig, axs = newfig('What each part of HSN contributes', 'Each row removes or replaces one component. Bars are RMSE (or the spectral share in the last panel); log scale; shorter is better. The dashed line marks full HSN.', 2, 3, 12.6, top_in=1.45)
    fig.subplots_adjust(left=0.265, right=0.985, wspace=0.07, hspace=0.22, bottom=0.04)
    for ax, (ttl, f) in zip(axs.ravel(), panels):
        ax.xaxis.set_minor_formatter(NullFormatter())
        vals = [f(k) for k in ks]
        ax.barh(range(len(ks)), vals, color=['#2f6fd0' if k == 'full' else '#9aa5b5' for k in ks], height=0.7)
        ax.axvline(vals[0], color='#2f6fd0', ls='--', lw=1)
        ax.set_xscale('log'); ax.set_ylim(len(ks) - 0.5, -0.5); ax.set_title(ttl, fontsize=12); ax.grid(axis='y', visible=False)
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_yticks(range(len(ks))); ax.set_yticklabels([lab(k) for k in ks] if ax in (axs[0][0], axs[1][0]) else [], fontsize=10.5)
    for r in (0, 1):
        axs[r][0].get_yticklabels()[0].set_weight('bold')
    savefig(fig, 'ablation_metrics')


def write_vectors():
    """Values of the analytic lattice samplers for the JavaScript self-check (src/noise/analytic-r4.js)."""
    import json
    k = np.arange(48)
    x, y, n = 1024 + (k * 37) % 1300, 1024 + (k * 91) % 1300, (k * k * 7919) % 100000
    out = {'x': x.tolist(), 'y': y.tolist(), 'index': n.tolist()}
    for name, fn in (('pr42', analytic_r4_pr42), ('single', analytic_single), ('perDimension', analytic_perdim), ('engineE', engine_e_auto), ('engineF', engine_f_auto)):
        out[name] = {D: fn(x, y, n, D).astype(np.float64).tolist() for D in (2, 4)}
    json.dump(out, open(os.path.join(N.ROOT, 'src/noise/r4-vectors.json'), 'w'), indent='\t')


PARTS = {'R4': part_r4, 'ABL': part_abl, 'vectors': write_vectors}

if __name__ == '__main__':
    N._selfcheck()
    for name in (sys.argv[1:] or ['R4', 'ABL']):
        print(f'===== part {name}')
        PARTS[name]()
