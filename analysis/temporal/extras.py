"""Follow-up sections, run by run_all.py (or alone: pnpm py analysis/temporal/extras.py X1 X2 X3 X4 X5).
`pnpm py analysis/temporal/extras.py vectors` rewrites src/noise/temporal-vectors.json and src/noise/vc64.js,
which tie the JavaScript modules to the implementations measured here.

X1  bit-reversed rank pairing of the two dimensions inside each 8x8 tile, against standard HSN with R2 steps
X2  replacement for lockstep.webp (two-panel and four-panel)
X3  the temporal step constants as the upstream PR uses them (golden, R2_STEPS, R4_STEPS; singly, in pairs, all four)
X4  HSN against two cheaper spatial phases with the same temporal steps: Hash + R_d and IGN + R_d
"""
import itertools
import math
import sys
from fractions import Fraction

import numpy as np
from scipy import signal

import noises as N
from integrands import INTS
from run_all import (BG, BOX_STARTS, METHODS, PAD, T0, T_EMA, W, e3, grid, groups, legend, md_table, newfig, plt, rms, running_rmse, save, savefig, spatial)

U = np.uint32
PIXEL = (21, 13)


def agg(per, D, gn='all'):
    """per: {integrand: value or array} -> RMS over the integrands of a group."""
    return np.sqrt(np.mean([np.square(per[INTS[D][i][0]]) for i in groups(D)[gn]], 0))


def per_pixel(fn, D, counts, gn='all'):
    x, y, n = grid(64, max(counts))
    c = agg(running_rmse(fn(x, y, n, D).reshape(D, max(counts), -1), D), D, gn)
    return [float(c[k - 1]) for k in counts]


def ema_blur(fn, D, fl='box3', a=0.1, gn='all'):
    """Steady-state RMSE under EMA(alpha) + spatial filter, same protocol as section D."""
    x, y, n = grid(W + 2 * PAD, T_EMA)
    s = fn(x, y, n, D)
    per = {}
    for name, grp, f, truth in INTS[D]:
        v = (f(s) - truth).astype(np.float32)
        e = signal.lfilter([a], [1, -(1 - a)], v, axis=0, zi=((1 - a) * v[:1]))[0][T0:].astype(np.float32)
        per[name] = float(rms(spatial(e, fl)))
    return float(agg(per, D, gn))


# ---------------------------------------------------------------- X1: bit-reversed pairing

def bitrev6(r):
    out = np.zeros_like(r)
    for b in range(6):
        out |= ((r >> U(b)) & U(1)) << U(5 - b)
    return out


def hsn_bitrev(x, y, n, D=2):
    """Dimension 1 is standard HSN (seed 1).  Dimension 2 reuses dimension 1's six-bit in-tile rank, bit-reversed,
    so the 64 pixels of a tile hold the Hammersley-like set (r/64, bitrev(r)/64), then adds its own hashed tile
    phase (seed 2).  Temporal steps are R2_STEPS, as in standard two-dimensional HSN."""
    xu, yu = N._u(x), N._u(y)
    nu = N._u(n)
    spatial1 = N.hsn_u32(x, y, 0, 1)
    phase1 = N.pixel_hash(xu >> U(3), yu >> U(3), 1 ^ 0x02e5be93)
    rank = (spatial1 - phase1) >> U(26)
    phase2 = N.pixel_hash(xu >> U(3), yu >> U(3), 2 ^ 0x02e5be93)
    v1 = spatial1 + nu * U(N.R2_STEPS[0])
    v2 = (bitrev6(rank) << U(26)) + phase2 + nu * U(N.R2_STEPS[1])
    return np.stack([(v >> U(8)).astype(np.float32) / np.float32(16777216) for v in np.broadcast_arrays(v1, v2)])


def single_frame(fn, frames=16):
    """Mean over frames of the single-frame 2D error after a spatial filter / per aligned 8x8 tile mean."""
    x, y, n = grid(W + 2 * PAD, frames)
    s = fn(x, y, n, 2)
    out = {k: {} for k in ('none', 'box3', 'gauss1', 'gauss2', 'tile8')}
    for name, grp, f, truth in INTS[2]:
        v = (f(s) - truth).astype(np.float32)
        for fl in ('none', 'box3', 'gauss1', 'gauss2'):
            out[fl][name] = float(rms(spatial(v, fl)))
        c = v[:, PAD:-PAD, PAD:-PAD]
        out['tile8'][name] = float(rms(c.reshape(frames, W // 8, 8, W // 8, 8).mean((2, 4))))
    return out


def section_X1():
    # the 64 pixels of every tile form a (0,6,2)-net in base 2 before the tile phases are added
    y, x = np.mgrid[0:8, 0:8]
    r = (N.hsn_u32(x, y, 0, 1) - N.pixel_hash(N._u(x) >> U(3), N._u(y) >> U(3), 1 ^ 0x02e5be93)) >> U(26)
    pts = np.stack([r.ravel(), bitrev6(r).ravel()])
    for k in range(7):
        assert len(set(zip((pts[0] >> U(6 - k)).tolist(), (pts[1] >> U(k)).tolist()))) == 64
    fns = {'HSN, R2 steps (standard, independent seeds)': lambda x, y, n, D: N.hsn(x, y, n, 2),
           'HSN, R2 steps, bit-reversed rank pairing': hsn_bitrev,
           'White (PCG hash)': N.white, 'FAST 128x128x32 texture': N.fast}
    data, counts = {}, [1, 4, 16, 64, 256]
    for name, fn in fns.items():
        sf = single_frame(fn)
        data[name] = dict(per_pixel=per_pixel(fn, 2, counts), single={k: float(agg(v, 2)) for k, v in sf.items()},
                          single_groups={g: {k: float(agg(v, 2, g)) for k, v in sf.items()} for g in ('smooth', 'edge', 'render')},
                          single_per={k: v for k, v in sf.items()}, ema={fl: ema_blur(fn, 2, fl) for fl in ('none', 'box3', 'gauss1')})
    t = '\n**X1 (a). Per-pixel 2D convergence, RMSE x 1e-3 over the 14 2D integrands, 64x64 pixels, no spatial filter**\n\n'
    t += md_table(['Method'] + [f'N={c}' for c in counts], [[k] + [e3(v) for v in d['per_pixel']] for k, d in data.items()])
    t += '\n**X1 (b). Single-frame 2D error, RMSE x 1e-3 over the 14 2D integrands (mean of frames 0-15, 128x128 pixels)**\n\n'
    cols = ['none', 'box3', 'gauss1', 'gauss2', 'tile8']
    t += md_table(['Method', 'no filter', '3x3 box', 'Gauss s=1', 'Gauss s=2', 'aligned 8x8 tile mean'], [[k] + [e3(d['single'][c]) for c in cols] for k, d in data.items()])
    for g in ('smooth', 'edge', 'render'):
        t += f'\n**X1 (b). The same, integrand group "{g}"**\n\n'
        t += md_table(['Method', 'no filter', '3x3 box', 'Gauss s=1', 'Gauss s=2', 'aligned 8x8 tile mean'], [[k] + [e3(d['single_groups'][g][c]) for c in cols] for k, d in data.items()])
    t += '\n**X1. Under EMA alpha=0.1, steady-state RMSE x 1e-3 over the 14 2D integrands**\n\n'
    t += md_table(['Method', 'no blur', '3x3 box', 'Gauss s=1'], [[k] + [e3(d['ema'][c]) for c in ('none', 'box3', 'gauss1')] for k, d in data.items()])
    a, b = list(data)[:2]
    t += '\n**X1. Every 2D integrand, single frame: standard vs bit-reversed (x 1e-3)**\n\n'
    t += md_table(['Integrand', 'std, 3x3 box', 'bitrev, 3x3 box', 'std, Gauss s=1', 'bitrev, Gauss s=1', 'std, tile mean', 'bitrev, tile mean'],
                  [[nm] + [e3(data[m]['single_per'][c][nm]) for c in ('box3', 'gauss1', 'tile8') for m in (a, b)] for nm, *_ in INTS[2]])
    save('X1', data, t)


# ---------------------------------------------------------------- X2: lockstep figure

def pixel_samples(fn, count=256, D=2):
    return fn(np.array([[[PIXEL[0]]]]), np.array([[[PIXEL[1]]]]), np.arange(count)[:, None, None], D).reshape(D, -1)


def scatter_panel(ax, s, color, title, size=16):
    ax.scatter(s[0], s[1], s=size, color=color, linewidths=0, zorder=3)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect('equal')
    ax.set_xticks([0.25, 0.5, 0.75]); ax.set_yticks([0.25, 0.5, 0.75]); ax.set_xticklabels([]); ax.set_yticklabels([])
    ax.tick_params(length=0); ax.grid(True, color='#ecebe6')
    for sp in ax.spines.values():
        sp.set_visible(True); sp.set_color('#d8d6d0')
    ax.set_title(title, fontsize=13)
    ax.set_xlabel('dimension 1 (u)'); ax.set_ylabel('dimension 2 (v)')


def section_X2():
    panels = [('Shared golden-ratio step', N.hsn_shared, METHODS['hsn_shared'][2]),
              ('Separate R2 steps per dimension', N.hsn, METHODS['hsn'][2]),
              ('Previous VXGI sampler: two offset IGN copies', N.ign_vxgi, METHODS['ign'][2]),
              ('White noise', N.white, METHODS['white'][2])]
    fig, axs = newfig('One pixel\'s 256 samples of two HSN dimensions',
                      'Each dot is the (u, v) pair one pixel uses on one frame. With a shared temporal step both values advance together, so the pairs never leave a\nfew diagonal lines. Separate R2 steps fill the square.', 1, 2, 8.6, top_in=1.75)
    fig.subplots_adjust(left=0.05, right=0.95, wspace=0.1, bottom=0.07)
    for ax, (ttl, fn, col) in zip(axs[0], panels[:2]):
        scatter_panel(ax, pixel_samples(fn), METHODS['hsn'][2], ttl, 22)
    savefig(fig, 'lockstep')
    fig, axs = newfig('One pixel\'s 256 two-dimensional samples',
                      'Each dot is the (u, v) pair one pixel uses on one frame. HSN with a shared step and the previous VXGI sampler (two pixel-offset copies of interleaved gradient noise)\nboth keep the pair on a few diagonal lines; HSN with separate R2 steps fills the square more evenly than white noise.', 1, 4, 5.9, top_in=1.75)
    fig.subplots_adjust(left=0.03, right=0.99, wspace=0.12, bottom=0.07)
    names = ['HSN, shared golden step', 'HSN, separate R2 steps', 'Previous VXGI: two offset IGN copies', 'White noise']
    for ax, (ttl, fn, col), nm in zip(axs[0], panels, names):
        scatter_panel(ax, pixel_samples(fn), col, nm, 12)
        ax.title.set_fontsize(12)
    savefig(fig, 'lockstep_four')


# ---------------------------------------------------------------- X3: step constants

STEPS = [('golden', N.GOLDEN_STEP), ('R2_STEPS[0]', N.R2_STEPS[0]), ('R2_STEPS[1]', N.R2_STEPS[1])] + [(f'R4_STEPS[{i}]', s) for i, s in enumerate(N.R4_STEPS)]
SQRT_PRIMES = [int(math.sqrt(p) % 1 * 2 ** 32) | 1 for p in (2, 3, 5, 7)]  # neutral reference, not tuned
COUNTS = [7, 8, 16, 32, 64, 256]


def with_steps(steps):
    return lambda x, y, n, D: np.stack([N.hsn1(x, y, n, k + 1, s) for k, s in enumerate(steps)])


def cf(step, terms=8):
    f, out = Fraction(step, 2 ** 32), []
    for _ in range(terms):
        a = f.numerator // f.denominator
        out.append(a)
        f -= a
        if f == 0:
            break
        f = 1 / f
    return out


def best_rational(step, max_q=64):
    a = step / 2 ** 32
    q = min(range(1, max_q + 1), key=lambda q: abs(a * q - round(a * q)) * q)  # smallest q * |q a - p|: 1/sqrt(5) is the best possible
    return q, round(a * q), abs(a * q - round(a * q)) * q


def pair_resonance(s1, s2, max_k=8):
    """Smallest |k1 a1 + k2 a2 - m| over small integer (k1, k2): near zero means the 2D points sit on few lines."""
    a1, a2 = s1 / 2 ** 32, s2 / 2 ** 32
    best = min(((abs(k1 * a1 + k2 * a2 - round(k1 * a1 + k2 * a2)), k1, k2) for k1 in range(0, max_k + 1) for k2 in range(-max_k, max_k + 1) if (k1, k2) != (0, 0) and (k1 > 0 or k2 > 0)), key=lambda t: t[0] * (abs(t[1]) + abs(t[2])) ** 2)
    return best


def section_X3():
    data = {'1d': {}, '2d': {}, '4d': {}}
    t = '\n**X3 (a). Each step alone as a 1D sequence.** Per-pixel RMSE x 1e-3 over the 10 1D integrands (64x64 pixels, no spatial filter), then steady-state RMSE under EMA alpha=0.1 with no blur and with a 3x3 box. "Nearest fraction" is the p/q (q <= 64) minimising q|q*step - p|; the theoretical optimum for that product is 0.447 (golden ratio), and small values mean the sequence nearly repeats every q frames.\n\n'
    rows = []
    for name, s in STEPS:
        fn = with_steps([s])
        q, p, d = best_rational(s)
        r = dict(value=s / 2 ** 32, cf=cf(s), frac=[p, q, d], per_pixel=per_pixel(fn, 1, COUNTS), ema_none=ema_blur(fn, 1, 'none'), ema_box3=ema_blur(fn, 1, 'box3'),
                 per_pixel_step=per_pixel(fn, 1, COUNTS, 'step'))
        data['1d'][name] = r
        rows.append([name, f"{r['value']:.6f}", f'{p}/{q} ({d:.3f})', str(r['cf'])] + [e3(v) for v in r['per_pixel']] + [e3(r['ema_none']), e3(r['ema_box3'])])
    t += md_table(['Step', 'value', 'nearest fraction (q|q a - p|)', 'continued fraction'] + [f'N={c}' for c in COUNTS] + ['EMA, no blur', 'EMA + 3x3'], rows)

    t += '\n**X3 (b). Pairs of steps for two dimensions (seeds 1, 2 in every row).** Per-pixel RMSE x 1e-3 over the 14 2D integrands, then EMA alpha=0.1 without blur and with a 3x3 box. "Resonance" is the small integer combination k1*a1 + k2*a2 closest to an integer (|k| <= 8): the pair\'s samples lie on lines when it is near zero.\n\n'
    pairs = [('R2_STEPS', N.R2_STEPS)] + [(f'R4_STEPS[{i}],[{j}]' + (' (PR VXGI)' if (i, j) == (0, 1) else ''), [N.R4_STEPS[i], N.R4_STEPS[j]]) for i, j in itertools.combinations(range(4), 2)] \
        + [('golden, golden (shared)', [N.GOLDEN_STEP] * 2)]
    rows = []
    for name, st in pairs:
        fn = with_steps(st)
        res = pair_resonance(*st)
        r = dict(per_pixel=per_pixel(fn, 2, COUNTS), ema_none=ema_blur(fn, 2, 'none'), ema_box3=ema_blur(fn, 2, 'box3'), resonance=list(res))
        data['2d'][name] = r
        rows.append([name, f'{res[1]}*a1 {res[2]:+d}*a2: {res[0]:.4f}'] + [e3(v) for v in r['per_pixel']] + [e3(r['ema_none']), e3(r['ema_box3'])])
    t += md_table(['Steps', 'resonance'] + [f'N={c}' for c in COUNTS] + ['EMA, no blur', 'EMA + 3x3'], rows)

    t += '\n**X3 (c). Four dimensions.** Per-pixel RMSE x 1e-3 over the 19 4D integrands, then EMA alpha=0.1 without blur and with a 3x3 box. The sqrt-primes row uses fract(sqrt(2, 3, 5, 7)) as steps: a neutral, untuned Kronecker alternative.\n\n'
    rows = []
    for name, st in [('R4_STEPS (PR SSR)', N.R4_STEPS), ('sqrt-primes steps', SQRT_PRIMES), ('golden x4 (shared)', [N.GOLDEN_STEP] * 4)]:
        fn = with_steps(st)
        r = dict(per_pixel=per_pixel(fn, 4, COUNTS), ema_none=ema_blur(fn, 4, 'none'), ema_box3=ema_blur(fn, 4, 'box3'))
        data['4d'][name] = r
        rows.append([name] + [e3(v) for v in r['per_pixel']] + [e3(r['ema_none']), e3(r['ema_box3'])])
    wfn = N.white
    rows.append(['White (PCG hash)'] + [e3(v) for v in per_pixel(wfn, 4, COUNTS)] + [e3(ema_blur(wfn, 4, 'none')), e3(ema_blur(wfn, 4, 'box3'))])
    t += md_table(['Steps'] + [f'N={c}' for c in COUNTS] + ['EMA, no blur', 'EMA + 3x3'], rows)
    save('X3', data, t)

    # scatter: R2 and all six R4 pairs, one pixel, 64 and 256 frames
    fig, axs = newfig('One pixel\'s two-dimensional samples for each pair of HSN temporal steps',
                      f'Pixel {PIXEL}, first 64 (top) and 256 (bottom) frames. R2_STEPS against every pair of R4_STEPS; the upstream PR draws the VXGI cone with R4_STEPS[0],[1].', 2, 7, 6.6, top_in=1.5)
    fig.subplots_adjust(left=0.035, right=0.995, wspace=0.05, hspace=0.05, bottom=0.02)
    for c, (name, st) in enumerate(pairs[:7]):
        s = pixel_samples(with_steps(st))
        for r, cnt in enumerate((64, 256)):
            ax = axs[r][c]
            ax.scatter(s[0, :cnt], s[1, :cnt], s=[9, 4][r], color=METHODS['hsn'][2], linewidths=0)
            ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
            for sp in ax.spines.values():
                sp.set_visible(True)
            if r == 0:
                ax.set_title(name, fontsize=11, loc='center')
            if c == 0:
                ax.set_ylabel(f'N = {cnt}')
    savefig(fig, 'X3_step_pairs_scatter')

    # 1D figure: where each step puts the first 64 samples, and convergence
    fig, axs = newfig('Each HSN temporal step as a one-dimensional sequence',
                      'Left: per-pixel RMSE of the running mean over the 10 one-dimensional integrands. Right: the first 28 values each step generates from 0 (R4_STEPS[0] is close to 6/7 and revisits seven clusters).', 1, 2, 8.6, top_in=2.0)
    cols = ['#2f6fd0', '#1fa971', '#17a2b8', '#e0603a', '#8e5bd0', '#a0522d', '#7a7a7a']
    x, y, n = grid(64, 256)
    hs = []
    for (name, s), col in zip(STEPS, cols):
        c = agg(running_rmse(with_steps([s])(x, y, n, 1).reshape(1, 256, -1), 1), 1)
        h, = axs[0][0].loglog(np.arange(1, 257), c, color=col, lw=3.2 if name == 'golden' else 1.8)
        hs.append(h)
    axs[0][0].set_xscale('log', base=2); axs[0][0].set_xticks([1, 2, 4, 8, 16, 32, 64, 128, 256]); axs[0][0].set_xticklabels([1, 2, 4, 8, 16, 32, 64, 128, 256])
    axs[0][0].set_xlabel('frames averaged per pixel (N)'); axs[0][0].set_ylabel('RMSE'); axs[0][0].set_title('Per-pixel convergence, 1D')
    for r, ((name, s), col) in enumerate(zip(STEPS, cols)):
        v = (np.arange(28) * (s / 2 ** 32)) % 1
        axs[0][1].scatter(v, np.full(28, r), s=40, color=col, linewidths=0)
    axs[0][1].set_yticks(range(7)); axs[0][1].set_yticklabels([nm for nm, _ in STEPS]); axs[0][1].set_ylim(6.6, -0.6); axs[0][1].set_xlim(0, 1)
    axs[0][1].set_xlabel('sample value'); axs[0][1].set_title('First 28 values'); axs[0][1].grid(axis='y', visible=False)
    legend(fig, (hs, [nm for nm, _ in STEPS]), 8.6, y_in=1.1, ncol=7)
    savefig(fig, 'X3_steps_1d')


# ---------------------------------------------------------------- X4: is HSN needed at all?  Hash + R_d and IGN + R_d in fixed point

IGN_LARGE_OFFSETS = [(0.0, 0.0), (47.0, 17.0), (101.0, 59.0), (173.0, 113.0)]


def hash_rd(x, y, n, D):
    """A. One PCG hash per pixel and dimension as a Cranley-Patterson offset, plus frame * HSN's step (uint32)."""
    xu, yu, nu = N._u(x), N._u(y), N._u(n)
    out = [N.pcg(xu ^ N.pcg(yu ^ N.pcg(np.array(d + 7001, np.uint32)))) + nu * U(s) for d, s in enumerate(N._steps(D))]
    return np.stack([(v >> U(8)).astype(np.float32) / np.float32(16777216) for v in np.broadcast_arrays(*out)])


def ign_rd(x, y, n, D):
    """B. IGN(pixel centre + a large fixed offset per dimension) as the phase, plus frame * HSN's step (uint32)."""
    px, py, nu = np.asarray(x).astype(np.float32) + np.float32(0.5), np.asarray(y).astype(np.float32) + np.float32(0.5), N._u(n)
    out = []
    for d, s in enumerate(N._steps(D)):
        ox, oy = IGN_LARGE_OFFSETS[d]
        phase = (N.ign(px + np.float32(ox), py + np.float32(oy)) * np.float32(16777216)).astype(np.uint32) << U(8)
        out.append(phase + nu * U(s))
    return np.stack([(v >> U(8)).astype(np.float32) / np.float32(16777216) for v in np.broadcast_arrays(*out)])


X4_FILTERS = ('none', 'box3', 'gauss1', 'gauss2')
X4_BOX = (1, 4, 8, 16)


def short_history(fn, D, gn):
    x, y, n = grid(W + 2 * PAD, T_EMA)
    s = fn(x, y, n, D)
    per = {}
    for name, grp, f, truth in INTS[D]:
        v = (f(s) - truth).astype(np.float32)
        r = {}
        e = signal.lfilter([0.1], [1, -0.9], v, axis=0, zi=(0.9 * v[:1]))[0][T0:].astype(np.float32)
        for fl in X4_FILTERS:
            r[f'ema/{fl}'] = float(rms(spatial(e, fl)))
            for c in X4_BOX:
                r[f'box{c}/{fl}'] = float(rms(spatial(np.stack([v[st:st + c].mean(0) for st in BOX_STARTS]), fl)))
        per[name] = r
    return {k: float(np.sqrt(np.mean([per[INTS[D][i][0]][k] ** 2 for i in groups(D)[gn]]))) for k in r}


def section_X4():
    fns = {'HSN': N.hsn, 'A. Hash + R_d': hash_rd, 'B. IGN + R_d': ign_rd, 'White (PCG hash)': N.white, 'FAST 128x128x32 texture': N.fast}
    views = [(1, 'step', '1D threshold tests (golden step)'), (2, 'all', '2D integrands (R2 steps)'), (4, 'all', '4D integrands (R4 steps)')]
    data, t = {}, ''
    for D, gn, ttl in views:
        data[D] = {k: short_history(fn, D, gn) for k, fn in fns.items()}
        data[D]['per_pixel'] = {k: per_pixel(fn, D, [16, 64, 256], gn) for k, fn in fns.items()}
        t += f'\n**X4. {ttl}: per-pixel RMSE x 1e-3, no spatial filter**\n\n'
        t += md_table(['Method', 'N=16', 'N=64', 'N=256'], [[k] + [e3(v) for v in data[D]['per_pixel'][k]] for k in fns])
        for fl, fname in zip(X4_FILTERS, ('no blur', '3x3 box', 'Gauss sigma 1', 'Gauss sigma 2')):
            t += f'\n**X4. {ttl}, {fname}: RMSE x 1e-3 after N frames (box average) and under EMA alpha=0.1**\n\n'
            t += md_table(['Method'] + [f'N={c}' for c in X4_BOX] + ['EMA 0.1'], [[k] + [e3(data[D][k][f'box{c}/{fl}']) for c in X4_BOX] + [e3(data[D][k][f'ema/{fl}'])] for k in fns])
        t += f'\n**X4. {ttl}: HSN error relative to A and B (below 1.00 means HSN is better)**\n\n'
        rows = []
        for ref in ('A. Hash + R_d', 'B. IGN + R_d'):
            for fl, fname in zip(X4_FILTERS[1:], ('3x3 box', 'Gauss s=1', 'Gauss s=2')):
                rows.append([f'HSN / {ref[3:]}, {fname}'] + [f"{data[D]['HSN'][f'box{c}/{fl}'] / data[D][ref][f'box{c}/{fl}']:.2f}" for c in X4_BOX] + [f"{data[D]['HSN'][f'ema/{fl}'] / data[D][ref][f'ema/{fl}']:.2f}"])
        t += md_table(['Ratio'] + [f'N={c}' for c in X4_BOX] + ['EMA 0.1'], rows)
    save('X4', data, t)


# ---------------------------------------------------------------- X5: does the temporal step interact with HSN's base-4 hierarchy?

def hash_steps(steps):
    def fn(x, y, n, D):
        xu, yu, nu = N._u(x), N._u(y), N._u(n)
        out = [N.pcg(xu ^ N.pcg(yu ^ N.pcg(np.array(d + 7001, np.uint32)))) + nu * U(s) for d, s in enumerate(steps)]
        return np.stack([(v >> U(8)).astype(np.float32) / np.float32(16777216) for v in np.broadcast_arrays(*out)])
    return fn


def section_X5():
    data, rows = {}, []
    cases = [(1, nm, [s]) for nm, s in STEPS] + [(2, 'R2_STEPS', N.R2_STEPS), (2, 'R4_STEPS[0],[1] (PR VXGI)', N.R4_STEPS[:2]), (2, 'R4_STEPS[0],[3]', [N.R4_STEPS[0], N.R4_STEPS[3]])]
    for D, nm, st in cases:
        a = [ema_blur(with_steps(st), D, fl) for fl in ('box3', 'gauss1')]
        b = [ema_blur(hash_steps(st), D, fl) for fl in ('box3', 'gauss1')]
        data[f'{D}d/{nm}'] = dict(hsn=a, hash=b)
        rows.append([f'{D}D, {nm}', e3(a[0]), e3(b[0]), f'{a[0] / b[0]:.2f}', e3(a[1]), e3(b[1]), f'{a[1] / b[1]:.2f}'])
    t = '\n**X5. HSN phase against a plain per-pixel hash phase, for the same temporal step(s).** Steady-state RMSE x 1e-3 under EMA alpha=0.1 plus a spatial filter (1D: 10 integrands; 2D: 14). A ratio below 1.00 means HSN\'s spatial hierarchy helps.\n\n'
    t += md_table(['Steps', 'HSN, 3x3', 'hash, 3x3', 'ratio', 'HSN, Gauss s=1', 'hash, Gauss s=1', 'ratio'], rows)
    save('X5', data, t)


def write_vectors():
    """Values of hash + R_d, IGN + R_d, V&C + R_d and animated IGN for the JavaScript self-check, and the V&C texture itself."""
    import json, os
    k = np.arange(48)
    x, y, n = 1024 + (k * 37) % 1300, 1024 + (k * 91) % 1300, (k * k * 7919) % 100000
    out = {'x': x.tolist(), 'y': y.tolist(), 'index': n.tolist()}
    for name, fn in (('hsn', N.hsn), ('hashRd', hash_rd), ('ignRd', ign_rd), ('vcRd', N.vc_rd), ('animatedIgn', N.ign_anim), ('white', N.white)):
        out[name] = {D: fn(x, y, n, D).astype(np.float64).tolist() for D in (1, 2, 4)}
    json.dump(out, open(os.path.join(N.ROOT, 'src/noise/temporal-vectors.json'), 'w'), indent='\t')
    ranks = np.rint(N.vc_texture().astype(np.float64) * 4096 - 0.5).astype(int).ravel()
    assert sorted(ranks) == list(range(4096))
    rows = '\n'.join('\t' + ', '.join(map(str, ranks[i:i + 32])) + ',' for i in range(0, 4096, 32))
    open(os.path.join(N.ROOT, 'src/noise/vc64.js'), 'w').write(
        '// Generated by `pnpm py analysis/temporal/extras.py vectors`: the 64x64 void-and-cluster rank texture (Ulichney 1993,\n'
        '// toroidal, sigma 1.5, seed 1) used by the temporal analysis. Row-major, rank 0..4095; value = ( rank + 0.5 ) / 4096.\n'
        'export const VC64 = new Uint16Array( [\n' + rows + '\n] );\n')


SECTIONS = {'X1': section_X1, 'X2': section_X2, 'X3': section_X3, 'X4': section_X4, 'X5': section_X5, 'vectors': write_vectors}

if __name__ == '__main__':
    for name in (sys.argv[1:] or list(SECTIONS)):
        print(f'===== section {name}')
        SECTIONS[name]()
