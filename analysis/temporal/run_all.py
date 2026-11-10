"""Temporal and multi-dimensional analysis of the noise against common real-time noises.

From the repository root:
    pnpm analysis:temporal            # everything (about 6 minutes on 8 cores)
    pnpm py analysis/temporal/run_all.py AB C   # selected sections: AB C D E F G X1 X2 X3 X4 X5  (H is produced by C; X* live in extras.py)

Writes results/temporal/<section>.json (raw numbers), tables_<section>.md and tables_<section>.json (the same
tables, for the website) and figures/*.webp.  All seeds are fixed.  The display name of the noise comes from
names.json: labels are written as "HSN" and replaced by the configured short name on output.
"""
import io
import re
import json
import math
import os
import sys
from multiprocessing import Pool

import numpy as np
from scipy import ndimage, signal

import noises as N
from integrands import INTS, PAIRS

OUT = os.path.join(N.ROOT, 'results/temporal')
FIG = os.path.join(OUT, 'figures')


def named(text):
    return text.replace('HSN', N.SHORT)  # labels are written with the default short name


TERMS = [(r'\b([124])D\b', r'\1-value'), ('samples per pixel (N)', 'frames accumulated (N)'), ('frames averaged per pixel (N)', 'frames accumulated (N)'),
         ('frames averaged (N)', 'frames accumulated (N)'), ("first N samples", "first N frames"), (', one dimension', ', one value per pixel'),
         (', two and four dimensions', ', two and four values per pixel'), (r'^Two dimensions \(', 'Two values per pixel ('), (r'^Four dimensions \(', 'Four values per pixel ('),
         (r'^([24]) dimensions$', r'\1 values per pixel')]


def worded(text):
    """Display name plus unambiguous terms in every table and figure: "1-value / 2-value / 4-value" is the number of
    values per pixel (the code calls it D), and N is always the number of frames accumulated."""
    text = named(text)
    for a, b in TERMS:
        text = re.sub(a, b, text, flags=re.M) if a.startswith(('^', r'\b')) else text.replace(a, b)
    return text

# key: (label, fn, colour, linestyle, linewidth, dimension counts it is shown for)
METHODS = {
    'hsn': ('HSN (golden / R2 / R4 steps)', N.hsn, '#2f6fd0', '-', 3.4, (1, 2, 4)),
    'hsn_pr': ('HSN, R4 steps 0-1 (as the PR calls it for VXGI)', N.hsn_pr_vxgi, '#2f6fd0', '--', 1.8, (2,)),
    'hsn_shared': ('HSN, shared golden step (broken on purpose)', N.hsn_shared, '#e0603a', '-', 2.0, (2, 4)),
    'white': ('White (PCG hash)', N.white, '#e8a800', '-', 2.0, (1, 2, 4)),
    'ign': ('Animated IGN (+ fixed pixel offset per dim)', N.ign_anim, '#1fa971', '-', 2.0, (1, 2, 4)),
    'ign64': ('Animated IGN, 64-frame cycle (old VXGI)', N.ign_vxgi, '#1fa971', '--', 1.6, (1, 2, 4)),
    'ar2': ('Analytic R2 (old SSR, RNoise.js)', N.analytic_r2_ssr, '#8e5bd0', '-', 2.0, (1, 2, 4)),
    'rdw': ('R_d Weyl + white per-pixel offset', N.rd_white, '#7a7a7a', '-', 2.0, (1, 2, 4)),
    'rdi': ('R_d Weyl + IGN per-pixel offset', N.rd_ign, '#17a2b8', '-', 2.0, (1, 2, 4)),
    'vcg': ('V&C 64x64 + golden Weyl (shared step)', N.vc_golden, '#a0522d', '--', 1.6, (1, 2, 4)),
    'vcr': ('V&C 64x64 + R_d Weyl steps', N.vc_rd, '#a0522d', '-', 2.0, (2, 4)),
    'stbn': ('STBN 128x128x64 texture', N.stbn, '#d6409f', '-', 2.0, (1, 2, 4)),
    'fast': ('FAST 128x128x32 texture', N.fast, '#222222', '-', 2.0, (1, 2, 4)),
}
SOBOL = ('Scrambled Sobol per pixel (bound)', '#b0b0b0', ':', 2.0)


def keys(D):
    return [k for k, m in METHODS.items() if D in m[5]]


def label(k):
    return SOBOL[0] if k == 'sobol' else METHODS[k][0]


def style(k):
    if k == 'sobol':
        return dict(color=SOBOL[1], ls=SOBOL[2], lw=SOBOL[3])
    m = METHODS[k]
    return dict(color=m[2], ls=m[3], lw=m[4], zorder=5 if k == 'hsn' else 2)


def grid(w, T, start=0, x0=0):
    y, x = np.mgrid[0:w, 0:w]
    return x[None] + x0, y[None] + x0, (np.arange(T, dtype=np.int64) + start)[:, None, None]


def samples(k, D, w, T, start=0):
    x, y, n = grid(w, T, start)
    return METHODS[k][1](x, y, n, D)  # (D, T, w, w)


def groups(D):
    g = {}
    for i, (name, grp, f, truth) in enumerate(INTS[D]):
        g.setdefault(grp, []).append(i)
    g['all'] = list(range(len(INTS[D])))
    return g


def rms(a, axis=None):
    return np.sqrt(np.mean(np.square(a), axis=axis))


# ---------------------------------------------------------------- output helpers

def md_table(headers, rows):
    out = ['| ' + ' | '.join(headers) + ' |', '| --- |' + ' ---: |' * (len(headers) - 1)]
    out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return '\n'.join(out) + '\n'


def e3(v):
    return f'{v * 1e3:.2f}' if v * 1e3 < 10 else f'{v * 1e3:.1f}'


def tables_json(md):
    """Markdown produced with md_table -> [{heading, title, head, rows}], so the website renders the same tables."""
    out, heading, text = [], '', []
    lines = md.split('\n')
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith('| ') and i + 1 < len(lines) and lines[i + 1].startswith('| ---'):
            cells = lambda s: [c.strip() for c in re.split(r'(?<!\\) \| ', s.strip()[2:-2])]
            j = i + 2
            while j < len(lines) and lines[j].startswith('| '):
                j += 1
            out.append(dict(heading=heading, title=' '.join(text).strip(), head=cells(ln), rows=[cells(r) for r in lines[i + 2:j]]))
            text, i = [], j
            continue
        if ln.startswith('#'):
            heading, text = ln.lstrip('# '), []
        elif ln.strip():
            text.append(ln.strip())
        i += 1
    return out


def save(section, data, tables, out=None):
    out = out or OUT
    os.makedirs(out, exist_ok=True)
    tables = worded(tables)
    open(os.path.join(out, f'{section}.json'), 'w').write(named(json.dumps(data, indent=1)) + '\n')
    open(os.path.join(out, f'tables_{section}.md'), 'w').write(tables)
    open(os.path.join(out, f'tables_{section}.json'), 'w').write(json.dumps(tables_json(tables), indent=1, ensure_ascii=False) + '\n')
    print(tables)


import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BG = '#fbfaf6'
plt.rcParams.update({'font.family': ['Helvetica Neue', 'Helvetica', 'Arial', 'DejaVu Sans'], 'font.size': 12,
                     'axes.facecolor': BG, 'figure.facecolor': BG, 'savefig.facecolor': BG,
                     'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': '#cccccc',
                     'axes.grid': True, 'grid.color': '#e6e3dc', 'axes.titleweight': 'bold', 'axes.titlesize': 13,
                     'axes.titlelocation': 'left', 'xtick.color': '#555', 'ytick.color': '#555', 'axes.labelcolor': '#333'})


def newfig(title, subtitle, nrows, ncols, height, top_in=1.25, **kw):
    fig, axs = plt.subplots(nrows, ncols, figsize=(16, height), dpi=100, squeeze=False, **kw)
    fig.text(0.025, 1 - 0.42 / height, title, fontsize=20, weight='bold', va='center')
    fig.text(0.025, 1 - 0.78 / height, subtitle, fontsize=12, color='#555', va='center')
    fig.subplots_adjust(top=1 - top_in / height, left=0.06, right=0.975, bottom=0.6 / height, wspace=0.22, hspace=0.35)
    return fig, axs


def legend(fig, handles_labels, height, y_in=1.08, ncol=4):
    h, l = handles_labels
    fig.legend(h, l, loc='upper left', bbox_to_anchor=(0.02, 1 - y_in / height), ncol=ncol, frameon=False, fontsize=11, handlelength=2.6, columnspacing=1.6)


def savefig(fig, name, out=None):
    from PIL import Image
    out = out or FIG
    os.makedirs(out, exist_ok=True)
    for t in fig.findobj(matplotlib.text.Text):  # titles, labels, legends: the display name comes from names.json
        t.set_text(worded(t.get_text()))
    png = io.BytesIO()
    fig.savefig(png, dpi=100, format='png')
    plt.close(fig)
    Image.open(png).convert('RGB').save(os.path.join(out, name + '.webp'), quality=90, method=6)
    print('wrote', name + '.webp')


# ---------------------------------------------------------------- A + B: per-pixel convergence, no spatial filter

T_CONV = 1024
POW2 = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]


def running_rmse(s, D):
    """s: (D, T, npix) -> {integrand: rmse[T]} of the running mean over frames 0..N-1."""
    out = {}
    for name, grp, f, truth in INTS[D]:
        v = f(s)
        rm = np.cumsum(v, 0) / np.arange(1, v.shape[0] + 1)[:, None]
        out[name] = rms(rm - truth, 1)
    return out


def section_AB():
    data, tables = {}, ''
    for D in (1, 2, 4):
        data[D] = {}
        for k in keys(D) + ['sobol']:
            s = N.sobol_bound(D, T_CONV, 1024) if k == 'sobol' else samples(k, D, 64, T_CONV).reshape(D, T_CONV, -1)
            per = running_rmse(s, D)
            g = {gn: np.sqrt(np.mean([per[INTS[D][i][0]] ** 2 for i in idx], 0)) for gn, idx in groups(D).items()}
            slope = {gn: float(np.polyfit(np.log(POW2[3:]), np.log([c[n - 1] for n in POW2[3:]]), 1)[0]) for gn, c in g.items()}
            data[D][k] = dict(curve={gn: [float(c[n - 1]) for n in POW2] for gn, c in g.items()}, slope=slope,
                              per256={name: float(c[255]) for name, c in per.items()}, per64={name: float(c[63]) for name, c in per.items()},
                              full={gn: c.tolist() for gn, c in g.items()})
        for gn in groups(D):
            tables += f'\n**{D}D, integrand group "{gn}" ({len(groups(D)[gn])} integrands): per-pixel RMSE x 1e-3 of the running mean, no spatial filter**\n\n'
            tables += md_table(['Method'] + [f'N={n}' for n in (1, 4, 16, 64, 256, 1024)] + ['slope (N=8..1024)'],
                               [[label(k)] + [e3(data[D][k]['curve'][gn][POW2.index(n)]) for n in (1, 4, 16, 64, 256, 1024)] + [f"{data[D][k]['slope'][gn]:.2f}"] for k in data[D]])
        tables += f'\n**{D}D, every integrand at N=256: per-pixel RMSE x 1e-3**\n\n'
        ks = list(data[D])
        tables += md_table(['Integrand'] + ks, [[name] + [e3(data[D][k]['per256'][name]) for k in ks] for name, *_ in INTS[D]])
    # the 1024-point curves are only needed for the figures below; the JSON keeps the powers of two
    save('AB', {D: {k: {a: b for a, b in v.items() if a != 'full'} for k, v in d.items()} for D, d in data.items()}, tables)

    xs = np.arange(1, T_CONV + 1)
    for name, title, sub, panels in [
        ('A_convergence_1d', 'Per-pixel temporal convergence, one dimension',
         'RMSE of each pixel\'s running mean over N frames against the exact integral, 64x64 pixels, no spatial filter. Log-log; lower is better; white noise falls as N^-0.5.',
         [(1, 'smooth', 'Smooth 1D integrands (u, u², cosine)'), (1, 'step', 'Step integrands (7 thresholds)')]),
        ('B_convergence_2d_4d', 'Per-pixel temporal convergence, two and four dimensions',
         'RMSE of each pixel\'s running mean over N frames, 64x64 pixels, no spatial filter. 14 two-dimensional and 19 four-dimensional integrands (smooth, edges on the diagonals, AO- and GGX-like).',
         [(2, 'all', 'Two dimensions (14 integrands)'), (4, 'all', 'Four dimensions (19 integrands)')]),
    ]:
        fig, axs = newfig(title, sub, 1, 2, 9.4, top_in=2.5)
        seen = {}
        for ax, (D, gn, ttl) in zip(axs[0], panels):
            for k in list(reversed(keys(D))) + ['sobol']:
                ln, = ax.loglog(xs, data[D][k]['full'][gn], **style(k))
                seen[k] = ln
            ax.set_title(ttl); ax.set_xlabel('frames averaged per pixel (N)'); ax.set_ylabel('RMSE')
            ax.set_xscale('log', base=2); ax.set_xlim(1, 1024)
            ax.set_xticks(POW2); ax.set_xticklabels(POW2)
        order = [k for k in list(METHODS) + ['sobol'] if k in seen]
        legend(fig, ([seen[k] for k in order], [label(k) for k in order]), 9.4)
        savefig(fig, name)


# ---------------------------------------------------------------- C + H: sample-set quality

def l2_star(pts, sizes):
    """Warnock L2 star discrepancy of the prefixes pts[:n] for n in sizes; pts (T, D) float64."""
    T, D = pts.shape
    a = np.cumsum(np.prod(1 - pts ** 2, 1))
    M = np.ones((T, T))
    for d in range(D):
        M *= 1 - np.maximum(pts[:, None, d], pts[None, :, d])
    C = M.cumsum(0).cumsum(1)
    return [math.sqrt(max(0.0, 3.0 ** -D - 2.0 ** (1 - D) / n * a[n - 1] + C[n - 1, n - 1] / n ** 2)) for n in sizes]


def chi2_pair(a, b, bins):
    """a, b: (count, groups) -> mean over groups of chi-square / dof for the bins x bins joint histogram."""
    cnt, G = a.shape
    idx = (np.minimum((a * bins).astype(np.int64), bins - 1) * bins + np.minimum((b * bins).astype(np.int64), bins - 1)) + np.arange(G)[None] * bins * bins
    h = np.bincount(idx.ravel(), minlength=G * bins * bins).reshape(G, -1)
    e = cnt / bins ** 2
    return float((((h - e) ** 2 / e).sum(1) / (bins * bins - 1)).mean())


def pearson(a, b):
    a = a - a.mean(0); b = b - b.mean(0)
    return (a * b).sum(0) / np.sqrt((a * a).sum(0) * (b * b).sum(0) + 1e-30)


SCATTER_PIXEL = (21, 13)


def section_C():
    data, tables = {}, ''
    rng = np.random.default_rng(42)
    pix = rng.choice(4096, 128, replace=False)
    sizes = [4, 8, 16, 32, 64, 128, 256, 512, 1024]
    for D in (2, 4):
        data[D] = {}
        for k in keys(D) + ['sobol']:
            if k == 'sobol':
                s = N.sobol_bound(D, 1024, 128)
                data[D][k] = dict(disc=np.mean([l2_star(s[:, :, i].T.astype(np.float64), sizes) for i in range(128)], 0).tolist())
                continue
            s = samples(k, D, 64, 1024).reshape(D, 1024, -1)
            disc = np.mean([l2_star(s[:, :, i].T.astype(np.float64), sizes) for i in pix], 0)
            sp = samples(k, D, 128, 16).reshape(D, 16, -1)
            r = dict(disc=disc.tolist(), t_r={}, t_chi={}, s_r={}, s_chi={})
            for i, j in PAIRS if D == 4 else [(0, 1)]:
                p = f'{i + 1}-{j + 1}'
                r['t_r'][p] = float(np.abs(pearson(s[i], s[j])).mean())
                r['t_chi'][p] = chi2_pair(s[i], s[j], 8)
                r['s_r'][p] = float(np.abs(pearson(sp[i].T, sp[j].T)).mean())
                r['s_chi'][p] = chi2_pair(sp[i].T, sp[j].T, 16)
            if D == 4:  # joint 4D histogram, 4 bins per axis, over time at each pixel
                b = np.minimum((s * 4).astype(np.int64), 3)
                idx = ((b[0] * 4 + b[1]) * 4 + b[2]) * 4 + b[3] + np.arange(4096)[None] * 256
                h = np.bincount(idx.ravel(), minlength=4096 * 256).reshape(4096, 256)
                r['t_chi4'] = float((((h - 4.0) ** 2 / 4.0).sum(1) / 255).mean())
            data[D][k] = r
        tables += f'\n**{D}D: L2 star discrepancy x 1e-3 of one pixel\'s first N samples (mean over 128 pixels)**\n\n'
        tables += md_table(['Method'] + [f'N={n}' for n in sizes], [[label(k)] + [e3(v) for v in data[D][k]['disc']] for k in data[D]])
    tables += '\n**2D: correlation between dimension 1 and 2.** Over time at a pixel: 1024 frames, mean over 4096 pixels of |Pearson r| (independent white expects 0.025) and of chi-square/dof for an 8x8 joint histogram (independent white expects 1.0; below 1 is more even than random). Across pixels within a frame: 128x128 pixels, mean over 16 frames, 16x16 histogram (white expects |r| 0.006, chi-square/dof 1.0).\n\n'
    tables += md_table(['Method', 'time |r|', 'time chi2/dof', 'space |r|', 'space chi2/dof'],
                       [[label(k), f"{v['t_r']['1-2']:.3f}", f"{v['t_chi']['1-2']:.2f}", f"{v['s_r']['1-2']:.3f}", f"{v['s_chi']['1-2']:.2f}"] for k, v in data[2].items() if k != 'sobol'])
    tables += '\n**4D: the six pairwise projections.** Worst pair (and mean over pairs) of the same statistics, plus the joint 4D histogram over time (4 bins per axis, 1024 frames, chi-square/dof; white expects 1.0).\n\n'
    rows = []
    for k, v in data[4].items():
        if k == 'sobol':
            continue
        w = lambda d, fmt: f"{format(max(d.values()), fmt)} ({max(d, key=d.get)}; mean {format(np.mean(list(d.values())), fmt)})"
        rows.append([label(k), w(v['t_r'], '.3f'), w(v['t_chi'], '.2f'), w(v['s_r'], '.3f'), w(v['s_chi'], '.2f'), f"{v['t_chi4']:.2f}"])
    tables += md_table(['Method', 'time |r| worst pair', 'time chi2/dof worst pair', 'space |r| worst pair', 'space chi2/dof worst pair', 'time 4D chi2/dof'], rows)
    tables += '\n**4D: chi-square/dof over time for each pair (8x8 histogram, 1024 frames)**\n\n'
    pn = [f'{i + 1}-{j + 1}' for i, j in PAIRS]
    tables += md_table(['Method'] + pn, [[label(k)] + [f"{v['t_chi'][p]:.2f}" for p in pn] for k, v in data[4].items() if k != 'sobol'])
    save('C', data, tables)

    # discrepancy figure
    fig, axs = newfig('Discrepancy of one pixel\'s sample set over time',
                      'L2 star discrepancy of a pixel\'s first N samples, mean over 128 pixels. Lower is more evenly spread; white noise falls as N^-0.5.', 1, 2, 9.4, top_in=2.5)
    seen = {}
    for ax, D in zip(axs[0], (2, 4)):
        for k in list(reversed(keys(D))) + ['sobol']:
            seen[k], = ax.loglog(sizes, data[D][k]['disc'], marker='o', ms=4, **style(k))
        ax.set_xscale('log', base=2); ax.set_xticks(sizes); ax.set_xticklabels(sizes)
        ax.set_title(f'{D} dimensions'); ax.set_xlabel('samples per pixel (N)'); ax.set_ylabel('L2 star discrepancy')
    order = [k for k in list(METHODS) + ['sobol'] if k in seen]
    legend(fig, ([seen[k] for k in order], [label(k) for k in order]), 9.4)
    savefig(fig, 'C_discrepancy')

    # scatter figure (2D)
    ks = ['hsn', 'hsn_shared', 'white', 'ign', 'ign64', 'ar2', 'rdi', 'vcg', 'vcr', 'stbn', 'fast']
    px, py = SCATTER_PIXEL
    fig, axs = newfig(f'One pixel\'s first 16, 64 and 256 two-dimensional samples',
                      f'Each dot is the (u, v) pair pixel ({px}, {py}) uses on one frame. Rows: 16, 64 and 256 frames.', 3, len(ks), 6.3, top_in=1.45)
    fig.subplots_adjust(left=0.03, right=0.995, wspace=0.06, hspace=0.06, bottom=0.02)
    for c, k in enumerate(ks):
        x, y, n = np.array([[[px]]]), np.array([[[py]]]), np.arange(256)[:, None, None]
        s = METHODS[k][1](x, y, n, 2).reshape(2, -1)
        for r, cnt in enumerate((16, 64, 256)):
            ax = axs[r][c]
            ax.scatter(s[0, :cnt], s[1, :cnt], s=[14, 7, 3][r], color=METHODS[k][2], linewidths=0)
            ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
            for sp in ax.spines.values():
                sp.set_visible(True)
            if r == 0:
                ax.set_title(label(k).split(' (')[0].replace(' 64x64', '').replace(' 128x128x64 texture', '').replace(' 128x128x32 texture', '').replace(', 64-frame cycle', ' 64-cycle').replace(' per-pixel offset', '').replace('Animated ', 'Anim. ').replace('shared golden step', 'shared step'), fontsize=9.5, weight='bold' if k == 'hsn' else 'normal')
            if c == 0:
                ax.set_ylabel(f'N = {cnt}')
    savefig(fig, 'C_scatter_2d')

    # H: 4D pairwise projections for one pixel
    ks = ['hsn', 'hsn_shared', 'white', 'ign', 'ar2', 'rdi', 'vcr', 'stbn', 'fast']
    fig, axs = newfig('Pairwise projections of one pixel\'s 256 four-dimensional samples',
                      f'Pixel ({px}, {py}), frames 0-255. Columns are the six dimension pairs; a diagonal line or lattice means the two dimensions are not independent over time.', len(ks), 6, 2.05 * len(ks) + 1.2, top_in=1.25)
    fig.subplots_adjust(left=0.2, right=0.8, wspace=0.05, hspace=0.05, bottom=0.01)
    for r, k in enumerate(ks):
        s = METHODS[k][1](np.array([[[px]]]), np.array([[[py]]]), np.arange(256)[:, None, None], 4).reshape(4, -1)
        for c, (i, j) in enumerate(PAIRS):
            ax = axs[r][c]
            ax.scatter(s[i], s[j], s=4, color=METHODS[k][2], linewidths=0)
            ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
            for sp in ax.spines.values():
                sp.set_visible(True)
            if r == 0:
                ax.set_title(f'dims {i + 1}, {j + 1}', fontsize=11, loc='center')
            if c == 0:
                ax.set_ylabel(label(k).replace(' (', '\n('), rotation=0, ha='right', va='center', fontsize=10.5, weight='bold' if k == 'hsn' else 'normal')
    savefig(fig, 'H_pairs_4d')


# ---------------------------------------------------------------- D + E: temporal + spatial filtering as used in real time

W, PAD, T_EMA, T0 = 128, 8, 256, 128
ALPHAS = (0.05, 0.1, 0.2)
BOX_N = (1, 4, 8, 16, 32)
BOX_STARTS = [3 + 41 * j for j in range(5)]  # deliberately not aligned with the 32/64-frame texture cycles
FILTERS = ('none', 'box3', 'gauss1', 'gauss2')


def spatial(e, name):
    """e: (frames, W+2PAD, W+2PAD) -> filtered and cropped to the central WxW."""
    if name == 'box3':
        e = ndimage.uniform_filter(e, (1, 3, 3), mode='nearest')
    elif name != 'none':
        e = ndimage.gaussian_filter(e, (0, float(name[5:]), float(name[5:])), mode='nearest', truncate=3.0)
    return e[:, PAD:-PAD, PAD:-PAD]


def d_worker(k):
    out = {}
    for D in (1, 2, 4):
        if D not in METHODS[k][5]:
            continue
        s = samples(k, D, W + 2 * PAD, T_EMA)
        res = {}
        for name, grp, f, truth in INTS[D]:
            v = (f(s) - truth).astype(np.float32)
            r = {}
            for a in ALPHAS:
                e = signal.lfilter([a], [1, -(1 - a)], v, axis=0, zi=((1 - a) * v[:1]))[0][T0:].astype(np.float32)
                for fl in FILTERS:
                    ef = spatial(e, fl)
                    r[f'ema{a}/{fl}'] = float(rms(ef))
                    r[f'ema{a}/{fl}/flicker'] = float(rms(np.diff(ef, axis=0)))
                    r[f'ema{a}/{fl}/fixed'] = float(rms(ef.mean(0)))  # error that persists over the 128 measured frames
            for n in BOX_N:
                m = np.stack([v[st:st + n].mean(0) for st in BOX_STARTS])
                for fl in FILTERS:
                    r[f'box{n}/{fl}'] = float(rms(spatial(m, fl)))
            res[name] = r
        agg = {}
        for gn, idx in groups(D).items():
            agg[gn] = {key: float(np.sqrt(np.mean([res[INTS[D][i][0]][key] ** 2 for i in idx]))) for key in res[INTS[D][0][0]]}
        out[D] = dict(agg=agg, per=res)
    return k, out


def section_D():
    with Pool(min(8, os.cpu_count())) as pool:
        data = dict(pool.map(d_worker, list(METHODS)))
    tables = ''
    views = [(1, 'step', '1D threshold tests (7 thresholds)'), (1, 'smooth', '1D smooth integrands'), (2, 'all', '2D integrands (14)'), (4, 'all', '4D integrands (19)')]
    get = lambda k, D, gn, key: data[k][D]['agg'][gn][key]
    for a in (0.1, 0.05, 0.2):
        for D, gn, ttl in views:
            tables += f'\n**EMA alpha={a}, {ttl}: steady-state RMSE x 1e-3 (frames 128-255, 128x128 pixels)**\n\n'
            tables += md_table(['Method', 'no blur', '3x3 box', 'Gauss s=1', 'Gauss s=2'], [[label(k)] + [e3(get(k, D, gn, f'ema{a}/{fl}')) for fl in FILTERS] for k in keys(D)])
    for D, gn, ttl in views:
        tables += f'\n**N-frame box average, {ttl}: RMSE x 1e-3 (5 windows starting at frames {BOX_STARTS})**\n\n'
        tables += md_table(['Method'] + [f'N={n}, {fl}' for n in BOX_N for fl in ('none', 'gauss1')], [[label(k)] + [e3(get(k, D, gn, f'box{n}/{fl}')) for n in BOX_N for fl in ('none', 'gauss1')] for k in keys(D)])
        tables += f'\n**N-frame box average, {ttl}: RMSE x 1e-3 with 3x3 box and Gauss s=2**\n\n'
        tables += md_table(['Method'] + [f'N={n}, {fl}' for n in BOX_N for fl in ('box3', 'gauss2')], [[label(k)] + [e3(get(k, D, gn, f'box{n}/{fl}')) for n in BOX_N for fl in ('box3', 'gauss2')] for k in keys(D)])
    for D, gn, ttl in views:
        tables += f'\n**E. Temporal stability at EMA alpha=0.1, {ttl} (x 1e-3).** Flicker = RMS frame-to-frame change of the filtered output. Fixed = RMS of the error that stays put over the 128 measured frames (per-pixel time-mean error); total^2 = fixed^2 + fluctuating^2.\n\n'
        tables += md_table(['Method', 'flicker, no blur', 'flicker, Gauss s=1', 'fixed, no blur', 'fixed, Gauss s=1', 'total, no blur', 'total, Gauss s=1'],
                           [[label(k)] + [e3(get(k, D, gn, f'ema0.1/{fl}{sfx}')) for sfx in ('/flicker', '/fixed', '') for fl in ('none', 'gauss1')] for k in keys(D)])
    tables += '\n**2D, every integrand: EMA alpha=0.1 + Gauss s=1 steady-state RMSE x 1e-3**\n\n'
    ks = keys(2)
    tables += md_table(['Integrand'] + ks, [[name] + [e3(data[k][2]['per'][name]['ema0.1/gauss1']) for k in ks] for name, *_ in INTS[2]])
    tables += '\n**1D, every integrand: EMA alpha=0.1 + Gauss s=1 steady-state RMSE x 1e-3**\n\n'
    ks = keys(1)
    tables += md_table(['Integrand'] + ks, [[name] + [e3(data[k][1]['per'][name]['ema0.1/gauss1']) for k in ks] for name, *_ in INTS[1]])
    save('D', data, tables)

    # headline figure: EMA 0.1 with each spatial filter
    fig, axs = newfig('Error left after temporal accumulation and a spatial filter',
                      'Steady-state RMSE under an exponential moving average (alpha = 0.1) followed by no blur, a 3x3 box, or a Gaussian (sigma 1, 2). Flat test field, 128x128 pixels. Log scale; lower is better.', 1, 3, 9.6, top_in=1.95)
    fig.subplots_adjust(left=0.275, wspace=0.08, bottom=0.075)
    shades = [1.0, 0.75, 0.5, 0.3]
    for ax, (D, gn, ttl) in zip(axs[0], [views[0], views[2], views[3]]):
        ks = [k for k in METHODS if D in METHODS[k][5]] if D != 1 else [k for k in METHODS]
        for r, k in enumerate(METHODS):
            if D not in METHODS[k][5]:
                continue
            for i, fl in enumerate(FILTERS):
                ax.barh(r + (i - 1.5) * 0.2, get(k, D, gn, f'ema0.1/{fl}'), height=0.19, color=METHODS[k][2], alpha=shades[i], label=['no blur', '3x3 box', 'Gauss σ=1', 'Gauss σ=2'][i] if k == 'hsn' else None)
        ax.set_xscale('log'); ax.set_ylim(len(METHODS) - 0.5, -0.5); ax.set_title(ttl); ax.set_xlabel('steady-state RMSE'); ax.grid(axis='y', visible=False)
        ax.set_yticks(range(len(METHODS)))
        ax.set_yticklabels([label(k) for k in METHODS] if ax is axs[0][0] else [])
        if ax is axs[0][0]:
            ax.get_yticklabels()[0].set_weight('bold')
            fig.legend(*ax.get_legend_handles_labels(), loc='upper left', bbox_to_anchor=(0.02, 1 - 1.0 / 9.6), ncol=4, frameon=False, fontsize=11, title='Spatial filter (darkest to lightest):', title_fontsize=11, alignment='left')
    savefig(fig, 'D_ema_spatial')

    # box-average figure: RMSE vs N for no blur / gauss 1
    fig, axs = newfig('Short temporal windows: N-frame average, then a spatial filter',
                      'RMSE of an N-frame box average (N = 1, 4, 8, 16, 32; windows not aligned to texture cycles). Top: no spatial filter. Bottom: Gaussian sigma = 1.', 2, 3, 12.5, top_in=2.5)
    seen = {}
    for c, (D, gn, ttl) in enumerate([views[0], views[2], views[3]]):
        for r, fl in enumerate(('none', 'gauss1')):
            ax = axs[r][c]
            for k in reversed(keys(D)):
                seen[k], = ax.loglog(BOX_N, [get(k, D, gn, f'box{n}/{fl}') for n in BOX_N], marker='o', ms=4, **style(k))
            ax.set_xscale('log', base=2); ax.set_xticks(BOX_N); ax.set_xticklabels(BOX_N)
            ax.set_title(f'{ttl}, ' + ('no blur' if fl == 'none' else 'Gauss σ=1')); ax.set_xlabel('frames averaged (N)'); ax.set_ylabel('RMSE')
    order = [k for k in METHODS if k in seen]
    legend(fig, ([seen[k] for k in order], [label(k) for k in order]), 12.5)
    savefig(fig, 'D_box_windows')

    # E: flicker vs error scatter
    fig, axs = newfig('Flicker against error under EMA (alpha = 0.1) + Gaussian sigma 1',
                      'Each point is one method. x: steady-state RMSE. y: RMS frame-to-frame change of the filtered output. Lower-left is better.', 1, 3, 8.6, top_in=2.5)
    seen = {}
    for ax, (D, gn, ttl) in zip(axs[0], [views[0], views[2], views[3]]):
        for k in keys(D):
            seen[k] = ax.scatter(get(k, D, gn, 'ema0.1/gauss1'), get(k, D, gn, 'ema0.1/gauss1/flicker'), s=220 if k == 'hsn' else 90, color=METHODS[k][2],
                                 marker='o' if METHODS[k][3] == '-' else 'D', edgecolors='white', linewidths=1, zorder=5 if k == 'hsn' else 3)
        ax.set_xscale('log'); ax.set_yscale('log'); ax.set_title(ttl); ax.set_xlabel('steady-state RMSE'); ax.set_ylabel('flicker (RMS frame difference)')
    order = [k for k in METHODS if k in seen]
    legend(fig, ([seen[k] for k in order], [label(k) + ('' if METHODS[k][3] == '-' else ' [diamond]') for k in order]), 8.6)
    savefig(fig, 'E_flicker_vs_error')


def section_E():
    """Per-pixel temporal power spectrum of the 1D signal over 256 frames (64x64 pixels)."""
    data, tables = {}, ''
    freqs = np.fft.rfftfreq(256)
    for k in keys(1):
        s = samples(k, 1, 64, 256)[0].reshape(256, -1).astype(np.float64)
        r = {}
        for nm, v in (('value', s), ('step0.3', (s < 0.3).astype(np.float64))):
            p = (np.abs(np.fft.rfft(v - v.mean(0), axis=0)) ** 2).mean(1)[1:]
            p /= p.sum()
            r[nm] = dict(lf=float(p[:15].sum()), lf32=float(p[:7].sum()), cum=np.cumsum(p).tolist(), p=p.tolist(),
                         ema_gain=float((p * (0.1 ** 2 / (1 + 0.81 - 1.8 * np.cos(2 * np.pi * freqs[1:])))).sum()))
        data[k] = r
    tables += '\n**E. Per-pixel temporal power spectrum, 1D, 256 frames, mean over 4096 pixels.** Share of (non-DC) power below 1/16 and below 1/32 cycles per frame (white expects 11.7% and 5.5%), and the power an alpha=0.1 EMA lets through (white expects 0.053). "value" is the raw sample; "step" is the indicator u<0.3.\n\n'
    tables += md_table(['Method', 'value: <1/16', 'value: <1/32', 'value: EMA pass', 'step: <1/16', 'step: <1/32', 'step: EMA pass'],
                       [[label(k)] + [f"{data[k][nm]['lf'] * 100:.2f}%" if q == 'lf' else f"{data[k][nm]['lf32'] * 100:.2f}%" if q == 'lf32' else f"{data[k][nm]['ema_gain']:.4f}" for nm in ('value', 'step0.3') for q in ('lf', 'lf32', 'ema')] for k in keys(1)])
    save('E', data, tables)
    fig, axs = newfig('Where each pixel\'s noise sits in temporal frequency',
                      'Cumulative share of per-pixel temporal noise power below each frequency (256 frames, 4096 pixels, 1D). Curves below the white diagonal push energy to high frequencies, which temporal filters remove.', 1, 2, 9.0, top_in=2.5)
    seen = {}
    for ax, (nm, ttl) in zip(axs[0], (('value', 'Raw sample value u'), ('step0.3', 'Thresholded sample, u < 0.3'))):
        for k in reversed(keys(1)):
            seen[k], = ax.plot(freqs[1:], data[k][nm]['cum'], **style(k))
        ax.set_xscale('log'); ax.set_yscale('log'); ax.set_ylim(1e-4, 1.2); ax.set_xlim(freqs[1], 0.5)
        ax.set_title(ttl); ax.set_xlabel('temporal frequency (cycles per frame)'); ax.set_ylabel('cumulative share of noise power')
    order = [k for k in METHODS if k in seen]
    legend(fig, ([seen[k] for k in order], [label(k) for k in order]), 9.0)
    savefig(fig, 'E_temporal_spectrum')


# ---------------------------------------------------------------- F: spatial quality over time

F_FRAMES = [0, 1, 7, 100, 10 ** 6]
F_TAUS = [0.1, 0.3, 0.5]
_fy, _fx = np.meshgrid(np.fft.fftfreq(128), np.fft.fftfreq(128), indexing='ij')
_LOW = np.hypot(_fx, _fy) < 1 / 8
_HANN = np.outer(np.hanning(128), np.hanning(128))


def lf_fraction(field):
    """Share of spectral power below 1/8 cycles per pixel (Hann window, mean removed). White expects pi/64 = 4.9%."""
    p = np.abs(np.fft.fft2((field - field.mean()) * _HANN)) ** 2
    p[0, 0] = 0
    return float(p[_LOW].sum() / p.sum())


def section_F():
    data, tables = {}, ''
    for k in keys(1):
        r = {}
        for n in F_FRAMES:
            u = samples(k, 1, 128, 1, start=n)[0, 0]
            r[f'frame{n}'] = float(np.mean([lf_fraction((u < t).astype(np.float64)) for t in F_TAUS]))
            r[f'frame{n}/value'] = lf_fraction(u.astype(np.float64))
        s = samples(k, 1, 128, 64)[0]
        for cnt in (4, 16, 64):
            errs = [(s[:cnt] < t).mean(0) - t for t in F_TAUS]
            r[f'avg{cnt}/lf'] = float(np.mean([lf_fraction(e) for e in errs]))
            r[f'avg{cnt}/rms'] = float(np.sqrt(np.mean([rms(e) ** 2 for e in errs])))
        # rigidity: does the circular difference between horizontal neighbours ever change?
        d = np.mod(s[:, :, 1:].astype(np.float64) - s[:, :, :-1] + 0.5, 1.0) - 0.5
        d0 = np.mod(d - d[:1] + 0.5, 1.0) - 0.5
        r['rigid'] = float(rms(d0))
        # frame-to-frame mask overlap: correlation between the u<0.3 masks of consecutive frames
        m = (s < 0.3).astype(np.float64).reshape(64, -1)
        r['mask_corr'] = float(np.mean([np.corrcoef(m[i], m[i + 1])[0, 1] for i in range(63)]))
        data[k] = r
    tables += '\n**F. Single-frame spatial quality at different frame indices.** Share of the threshold mask\'s spectral power below 1/8 cycles/pixel (mean over thresholds 0.1, 0.3, 0.5; 128x128, Hann window). White noise expects 4.9%; lower is bluer.\n\n'
    tables += md_table(['Method'] + [f'frame {n}' for n in F_FRAMES], [[label(k)] + [f"{data[k][f'frame{n}'] * 100:.2f}%" for n in F_FRAMES] for k in keys(1)])
    tables += '\n**F. The same for the raw value field (not thresholded).**\n\n'
    tables += md_table(['Method'] + [f'frame {n}' for n in F_FRAMES], [[label(k)] + [f"{data[k][f'frame{n}/value'] * 100:.2f}%" for n in F_FRAMES] for k in keys(1)])
    tables += '\n**F. Spatial character of the error left after averaging N frames (threshold tests, no spatial filter).** Low-frequency share of the residual error field (white 4.9%) and its RMS x 1e-3. "Neighbour drift" is the RMS change over 64 frames of the wrapped difference between horizontally adjacent pixels: 0 means the pattern only ever shifts rigidly in value. "Mask corr." is the correlation between the u<0.3 masks of consecutive frames (independent frames expect 0; a perfectly anti-correlated pair with a 30% mask gives -0.43).\n\n'
    tables += md_table(['Method', 'N=4 LF share', 'N=4 RMS', 'N=16 LF share', 'N=16 RMS', 'N=64 LF share', 'N=64 RMS', 'neighbour drift', 'mask corr.'],
                       [[label(k)] + [f"{data[k][f'avg{c}/lf'] * 100:.2f}%" if q == 'lf' else e3(data[k][f'avg{c}/rms']) for c in (4, 16, 64) for q in ('lf', 'rms')] + [f"{data[k]['rigid']:.4f}", f"{data[k]['mask_corr']:+.3f}"] for k in keys(1)])
    save('F', data, tables)

    ks = ['hsn', 'white', 'ign', 'ar2', 'rdi', 'vcg', 'stbn', 'fast']
    rows = ['frame 0: u < 0.3', 'frame 1: u < 0.3', 'error of 4-frame mean', 'error of 16-frame mean']
    fig, axs = newfig('What the pattern looks like on consecutive frames, and what is left after averaging',
                      '96x96 pixel crops. Rows 1-2: threshold mask on frames 0 and 1. Rows 3-4: error of the 4- and 16-frame mean of that mask (grey = no error; ±0.3 and ±0.15 full scale).', 4, len(ks), 9.6, top_in=1.45)
    fig.subplots_adjust(left=0.09, right=0.995, wspace=0.03, hspace=0.03, bottom=0.01)
    for c, k in enumerate(ks):
        s = samples(k, 1, 96, 16)[0]
        m = (s < 0.3).astype(np.float64)
        ims = [(m[0], 0, 1), (m[1], 0, 1), (m[:4].mean(0) - 0.3, -0.3, 0.3), (m.mean(0) - 0.3, -0.15, 0.15)]
        for r, (im, lo, hi) in enumerate(ims):
            ax = axs[r][c]
            ax.imshow(im, cmap='gray', vmin=lo, vmax=hi, interpolation='nearest')
            ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
            if r == 0:
                ax.set_title(label(k).split(' (')[0].replace(' 128x128x64 texture', '').replace(' 128x128x32 texture', '').replace(' per-pixel offset', '').replace(' 64x64', ''), fontsize=11, weight='bold' if k == 'hsn' else 'normal')
            if c == 0:
                ax.set_ylabel(rows[r], fontsize=10.5)
    savefig(fig, 'F_frames_and_residual')


# ---------------------------------------------------------------- G: long-run robustness

G_STARTS = [0, 10 ** 2, 10 ** 3, 10 ** 4, 10 ** 5, 10 ** 6, 10 ** 7, 10 ** 8, 10 ** 9, 4 * 10 ** 9]


def section_G():
    data, tables = {}, ''
    for k in METHODS:
        r = {}
        for D in (1, 2):
            if D not in METHODS[k][5]:
                continue
            for n0 in G_STARTS:
                s = samples(k, D, 64, 64, start=n0).reshape(D, 64, -1)
                per = running_rmse(s, D)
                idx = groups(D)['step' if D == 1 else 'all']
                r[f'{D}d/{n0}'] = float(np.sqrt(np.mean([per[INTS[D][i][0]][63] ** 2 for i in idx])))
                if D == 1:
                    r[f'distinct_t/{n0}'] = float(np.mean([len(np.unique(s[0, :, i])) for i in range(0, 4096, 16)]))
                    r[f'distinct_s/{n0}'] = int(len(np.unique(s[0, 0])))
                    r[f'repeat/{n0}'] = float(np.mean(s[0, 1:] == s[0, :-1]))
        data[k] = r
    for D, ttl in ((1, '1D threshold tests'), (2, '2D integrands')):
        tables += f'\n**G. Per-pixel RMSE x 1e-3 of a 64-frame average starting at frame n0, {ttl} (64x64 pixels, no spatial filter)**\n\n'
        tables += md_table(['Method'] + [f'n0={n:.0e}' if n else 'n0=0' for n in G_STARTS], [[label(k)] + [e3(data[k][f'{D}d/{n}']) for n in G_STARTS] for k in keys(D)])
    tables += '\n**G. Value diversity at large frame index (1D).** Mean number of distinct values one pixel sees in 64 consecutive frames (ideal 64) / number of distinct values across the 4096 pixels of frame n0 / share of frames where a pixel repeats its previous value.\n\n'
    gs = [0, 10 ** 5, 10 ** 6, 10 ** 7, 10 ** 9]
    tables += md_table(['Method'] + [f'n0={n:.0e}' if n else 'n0=0' for n in gs],
                       [[label(k)] + [f"{data[k][f'distinct_t/{n}']:.1f} / {data[k][f'distinct_s/{n}']} / {data[k][f'repeat/{n}'] * 100:.0f}%" for n in gs] for k in keys(1)])
    save('G', data, tables)
    fig, axs = newfig('Long-run robustness: error of a 64-frame average started at frame n0',
                      'Per-pixel RMSE of a 64-frame average, no spatial filter. Float32 time (animated IGN, float Weyl) loses precision as the frame index grows; integer time (HSN) and looping textures do not.', 1, 2, 9.0, top_in=2.5)
    xs = [max(n, 10) for n in G_STARTS]
    seen = {}
    for ax, (D, ttl) in zip(axs[0], ((1, '1D threshold tests'), (2, '2D integrands'))):
        for k in reversed(keys(D)):
            seen[k], = ax.loglog(xs, [data[k][f'{D}d/{n}'] for n in G_STARTS], marker='o', ms=4, **style(k))
        ax.set_xticks(xs); ax.set_xticklabels(['0'] + [f'1e{int(round(math.log10(n)))}' for n in G_STARTS[1:-1]] + ['4e9'])
        ax.set_title(ttl); ax.set_xlabel('starting frame index n0 (60 fps: 1e5 = 28 min, 1e6 = 4.6 h, 1e7 = 46 h)'); ax.set_ylabel('RMSE of 64-frame average')
    order = [k for k in METHODS if k in seen]
    legend(fig, ([seen[k] for k in order], [label(k) for k in order]), 9.0)
    savefig(fig, 'G_long_run')


SECTIONS = {'AB': section_AB, 'C': section_C, 'D': section_D, 'E': section_E, 'F': section_F, 'G': section_G}

if __name__ == '__main__':
    N._selfcheck()
    import extras  # follow-up sections X1-X4 (bit-reversed pairing, lockstep figure, step constants, cheaper phases)
    todo = sys.argv[1:] or list(SECTIONS) + list(extras.SECTIONS)
    for name in todo:
        print(f'===== section {name}')
        (SECTIONS.get(name) or extras.SECTIONS[name])()
