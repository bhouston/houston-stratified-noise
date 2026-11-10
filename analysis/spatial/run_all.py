"""Single-frame spatial analysis of screen-space noises. Entry point (from the repository root): npm run analysis:spatial

Writes results/spatial/results.json (raw numbers), tables.json and tables.md (the formatted tables) and
figures/*.webp. Everything is deterministic. The void-and-cluster textures are generated on first run
(about a minute) and cached in analysis/spatial/cache/.
"""
import io
import json
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, uniform_filter

import noises as nz
import vnc

OUT = nz.ROOT / 'results/spatial'
SHORT = nz.SHORT  # display name of the noise, set in names.json
PAD, N, R = 32, 256, 8  # padding for filters, analysis domain, realizations per method
# crop origins for methods without a seed: 8 tile-aligned 256x256 crops inside a ~2300x2300 screen
CROPS = [(1024 + 256 * a, 1024 + 256 * b) for a, b in ((0, 0), (1, 0), (0, 1), (1, 1), (2, 0), (2, 1), (3, 2), (4, 3))]
SIGMAS = [0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 8]
BOXES = [3, 5]
THRESHOLDS = [(i + 0.5) / 16 for i in range(16)]
WINDOWS = [2, 4, 8, 16]
LAGS = [(1, 0), (0, 1), (1, 1), (1, -1), (2, 0), (0, 2), (4, 0), (8, 0)]
CUTS = [1 / 32, 1 / 16, 1 / 8, 1 / 4]  # cycles/pixel = 1/16, 1/8, 1/4, 1/2 of Nyquist

# key: (label, colour, linestyle, linewidth, native period for FFT)
METHODS = {
    'hsn': (SHORT, '#2f6fd0', '-', 3.6, 256),
    'white': ('White (PCG3D)', '#e8a202', '-', 1.8, 256),
    'sin': ('fract(sin) hash', '#9a9a9a', ':', 1.8, 256),
    'hash12': ('Hoskins hash12', '#9a9a9a', '--', 1.5, 256),
    'ign': ('IGN', '#1aa772', '-', 1.8, 256),
    'r2': ('R2 (Roberts)', '#e0603a', '-', 1.8, 256),
    'tjs': ('Three.js Analytic R²', '#a0522d', '--', 1.8, 256),
    'bayer': ('Bayer 8×8', '#8e5bd0', '-', 1.8, 256),
    'vnc256': ('Void-and-cluster 256²', '#111111', '-', 1.8, 256),
    'peters': ('Peters blue noise 256²', '#111111', '--', 1.5, 256),
    'fast': ('FAST (EA) 128²', '#c2318f', '-', 1.8, 128),
}
EXTRA = {
    'white_hsn': (f'White ({SHORT}\'s own hash)', '#e8a202', ':', 1, 256),
    'vnc128': ('Void-and-cluster 128² tiled', '#111111', ':', 1, 128),
    'vnc64': ('Void-and-cluster 64² tiled', '#111111', ':', 1, 64),
    'fast_st': ('FAST spatio-temporal 128²', '#c2318f', ':', 1, 128),
    'tjs1': ('Three.js Analytic ch.1 (y)', '#a0522d', ':', 1, 256),
    'tjs2': ('Three.js Analytic ch.2 (z)', '#a0522d', ':', 1, 256),
    'tjs3': ('Three.js Analytic ch.3 (w)', '#a0522d', ':', 1, 256),
}
ALL = {**METHODS, **EXTRA}
PANELS = list(METHODS) + ['vnc64']


def fields(key, count=R):
    """count realizations, each (N+2*PAD)^2, pixel (PAD, PAD) is a tile-aligned screen coordinate."""
    span = np.arange(-PAD, N + PAD)

    def grid(k):
        ox, oy = CROPS[k % len(CROPS)]
        return np.meshgrid(ox + span, oy + span)  # x, y

    seeded = {'hsn': nz.hsn, 'white': nz.white_pcg, 'white_hsn': nz.white_hsn_hash}
    cropped = {'sin': nz.sin_hash, 'hash12': nz.hash12, 'ign': nz.ign, 'r2': nz.r2_roberts, 'bayer': nz.bayer}
    if key in seeded:
        return np.stack([seeded[key](*grid(0), seed=k + 1) for k in range(count)])
    if key in cropped:
        return np.stack([cropped[key](*grid(k)) for k in range(count)])
    if key.startswith('tjs'):
        return np.stack([nz.threejs_analytic(*grid(0), seed=47, index=k, channel=int(key[3:] or 0)) for k in range(count)])
    textures = {'vnc256': lambda: [vnc.cached(256, s) for s in range(1, 9)], 'vnc128': lambda: [vnc.cached(128, s) for s in range(1, 9)],
                'vnc64': lambda: [vnc.cached(64, s) for s in range(1, 9)], 'peters': nz.load_peters,
                'fast': nz.load_fast, 'fast_st': lambda: nz.load_fast('gauss1-ema01-spatio-temporal')}[key]()
    return np.stack([nz.tile(textures[k % len(textures)])(*grid(0)) for k in range(count)])


def power(v):
    """Periodogram with DC removed, normalised so ideal uniform white noise averages 1 in every bin."""
    v = v - v.mean(axis=(-2, -1), keepdims=True)
    n = v.shape[-1]
    return np.abs(np.fft.fft2(v)) ** 2 / (n * n / 12)


def radius(n):
    k = np.fft.fftfreq(n) * n
    return np.hypot(*np.meshgrid(k, k))


def max_bin(p):
    return float(p.max() / p.sum())


def compute(key):
    n = ALL[key][4]
    f = fields(key)
    c = f[:, PAD:PAD + N, PAD:PAD + N]
    out = {}

    # A. histogram / uniformity
    hist = {}
    for bins in (64, 256):
        h = np.stack([np.histogram(r, bins, (0, 1))[0] for r in c])
        e = N * N / bins
        hist[f'chi2_{bins}'] = float((((h - e) ** 2) / e).sum(1).mean())
        hist[f'maxdev_{bins}'] = float((np.abs(h - e) / e).max(1).mean())
    hist.update(mean=float(c.mean()), var12=float(c.var(axis=(1, 2)).mean() * 12), distinct=int(len(np.unique(c[0]))))
    out['hist'] = hist
    out['hist64'] = (np.histogram(c, 64, (0, 1))[0] / (c.size / 64)).tolist()

    # B-D. spectra at the native period (tiling a texture would put zeros between its bins)
    s = c[:, :n, :n]
    p = power(s).mean(0)
    r = radius(n)
    ring = np.rint(r).astype(int)
    rad, ani = [], []
    for k in range(1, n // 2 + 1):
        q = p[ring == k]
        m = q.mean()
        rad.append(m)
        ani.append(q.var(ddof=1) / m ** 2 if m > 1e-12 else np.nan)
    ani_db = 10 * np.log10(np.maximum(ani, 1e-12))
    valid = np.isfinite(ani_db) & (np.arange(1, n // 2 + 1) >= 4)
    total = p.sum()
    mask = (s < 0.5).astype(float)
    crop128 = (c[:, :128, :128] < 0.5).astype(float)
    hann = np.outer(np.hanning(128), np.hanning(128))
    line = 256 // 8 * n // 256  # bin spacing of 1/8 cycle/pixel
    kk = (np.fft.fftfreq(n) * n).astype(int)
    kx, ky = np.meshgrid(kk, kk)
    lattice = (kx % line == 0) & (ky % line == 0) & (r > 0)
    comb = ((kx % line == 0) | (ky % line == 0)) & (r > 0)
    out['spec'] = dict(
        low={str(cut): float(p[(r > 0) & (r < cut * n)].sum() / total) for cut in CUTS},
        low_white={str(cut): float(((r > 0) & (r < cut * n)).sum() / (n * n - 1)) for cut in CUTS},
        peak_value=max_bin(p), peak_mask=max_bin(power(mask).mean(0)), peak_mask128=max_bin(power(crop128).mean(0)),
        peak_mask128_hann=max_bin(power((crop128 - crop128.mean(axis=(1, 2), keepdims=True)) * hann).mean(0)),
        ani_mean=float(ani_db[valid].mean()), ani_median=float(np.median(ani_db[valid])), ani_max=float(ani_db[valid].max()),
        lattice_frac=float(p[lattice].sum() / total), lattice_white=float(lattice.sum() / (n * n - 1)), lattice_max=float(p[lattice].max()),
        comb_frac=float(p[comb].sum() / total), comb_white=float(comb.sum() / (n * n - 1)),
        mask_lattice_frac=float((pm := power(mask).mean(0))[lattice].sum() / pm.sum()))
    out['radial'], out['aniso'], out['n'] = rad, ani_db.tolist(), n
    out['p2d'] = np.fft.fftshift(p)
    out['swatch'] = c[0, :128, :128]

    # E. filtered error
    def filt(stack):
        stack = stack.astype(np.float32)
        res = [gaussian_filter(stack, (0, s_, s_), mode='wrap', truncate=4) for s_ in SIGMAS]
        res += [uniform_filter(stack, (1, b, b), mode='wrap') for b in BOXES]
        return [x[:, PAD:PAD + N, PAD:PAD + N].astype(np.float64) for x in res]

    out['value_err'] = [float(np.sqrt(((x - 0.5) ** 2).mean())) for x in filt(f)]
    mse = np.array([[((x - t) ** 2).mean() for x in filt(f[:4] < t)] for t in THRESHOLDS])
    out['thresh_err'] = np.sqrt(mse.mean(0)).tolist()
    out['thresh_err_by_t'] = np.sqrt(mse).tolist()  # [threshold][filter]
    out['mask_raw_bias'] = float(np.abs([(c < t).mean() - t for t in THRESHOLDS]).max())

    # F. window means, aligned to the pixel grid origin vs every offset
    ii = np.zeros((R, N + 2 * PAD + 1, N + 2 * PAD + 1))
    ii[:, 1:, 1:] = f.cumsum(1).cumsum(2)
    win = {}
    for w in WINDOWS:
        a = slice(PAD, PAD + N)
        b = slice(PAD + w, PAD + N + w)
        err = (ii[:, b, b] - ii[:, a, b] - ii[:, b, a] + ii[:, a, a]) / (w * w) - 0.5
        e2 = (err ** 2).mean(0)  # indexed by window start (y, x) in the crop
        by_offset = np.sqrt(e2.reshape(N // 8, 8, N // 8, 8).mean(axis=(0, 2)))
        win[str(w)] = dict(aligned=float(np.sqrt(e2[::w, ::w].mean())), any=float(np.sqrt(e2.mean())),
                           worst_offset=float(by_offset.max()), by_offset=by_offset.tolist(),
                           max_abs_aligned=float(np.abs(err[:, ::w, ::w]).max()))
    out['win'] = win

    # G. autocorrelation
    m, var = c.mean(), c.var()
    shift = lambda dx, dy: f[:, PAD + dy:PAD + dy + N, PAD + dx:PAD + dx + N]
    corr = lambda dx, dy: float(((c - m) * (shift(dx, dy) - m)).mean() / var)
    out['acorr'] = {f'{dx},{dy}': corr(dx, dy) for dx, dy in LAGS}
    out['acorr_map'] = [[corr(dx, dy) for dx in range(-6, 7)] for dy in range(-6, 7)]
    if key == 'hsn':
        prod = ((c - m) * (shift(1, 0) - m)).mean(0) / var  # pair (x, x+1), indexed by x
        col = prod.mean(0).reshape(-1, 8).mean(0)
        out['hsn_pairs'] = {'same 2x2 block (x%2=0)': float(col[[0, 2, 4, 6]].mean()), 'across 2x2, same 4x4 (x%4=1)': float(col[[1, 5]].mean()),
                            'across 4x4, same tile (x%8=3)': float(col[3]), 'across tile boundary (x%8=7)': float(col[7])}
        many = power(fields('hsn', 64)[:, PAD:PAD + N, PAD:PAD + N])
        pm = many.mean(0)
        out['hsn_lines64'] = dict(lattice_frac=float(pm[lattice].sum() / pm.sum()), lattice_max=float(pm[lattice].max()),
                                  lattice_mean=float(pm[lattice].mean()), comb_frac=float(pm[comb].sum() / pm.sum()),
                                  other_max=float(pm[~lattice & (r > 0)].max()),
                                  plateau_db=float(10 * np.log10(pm[(r > 0) & (r <= 4)].mean())))
    return key, out


# ---------------------------------------------------------------- figures

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker
from PIL import Image

BG, INK, MUTED, GRID = '#fcfbf7', '#111111', '#555555', '#e4e2dc'
plt.rcParams.update({'font.family': ['Helvetica Neue', 'Helvetica', 'Arial', 'DejaVu Sans'], 'font.size': 13, 'axes.facecolor': BG,
                     'figure.facecolor': BG, 'savefig.facecolor': BG, 'axes.edgecolor': GRID, 'axes.labelcolor': MUTED,
                     'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.spines.left': False, 'axes.grid': True, 'axes.grid.axis': 'y', 'grid.color': GRID, 'axes.axisbelow': True,
                     'xtick.major.size': 0, 'ytick.major.size': 0, 'legend.frameon': False})
FIG = OUT / 'figures'


def figure(title, subtitle, height, rows=1, cols=1, header=1.25, **kw):
    fig, axes = plt.subplots(rows, cols, figsize=(16, height), dpi=100, squeeze=False,
                             gridspec_kw=dict(left=0.06, right=0.975, top=1 - header / height, bottom=0.75 / height, **kw))
    fig.text(0.03, 1 - 0.42 / height, title, fontsize=22, fontweight='bold', color=INK, va='center')
    fig.text(0.03, 1 - 0.82 / height, subtitle, fontsize=13, color=MUTED, va='center')
    return fig, axes


def legend(fig, height, keys=METHODS, y=1.12):
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], color=ALL[k][1], ls=ALL[k][2], lw=max(ALL[k][3], 2)) for k in keys]
    fig.legend(handles, [ALL[k][0] for k in keys], loc='upper left', bbox_to_anchor=(0.025, 1 - y / height), ncol=6, fontsize=12.5,
               handlelength=2.2, columnspacing=1.6)


def line(ax, key, x, y, **kw):
    label, colour, ls, lw, _ = ALL[key]
    ax.plot(x, y, color=colour, ls=ls, lw=kw.pop('lw', lw), zorder=10 if key == 'hsn' else 3, **kw)


def save(fig, name):
    png = io.BytesIO()
    fig.savefig(png, format='png')
    plt.close(fig)
    Image.open(png).convert('RGB').save(FIG / f'{name}.webp', quality=88, method=6)


def panels(res, name, title, subtitle, draw, cbar=False):
    """2x6 grid of square panels placed on exact pixels (256 px = 2x a 128 px swatch)."""
    size, gap, left, top, label = (240, 8, 12, 100, 34) if cbar else (256, 8, 12, 100, 34)
    width, height = 1600, top + 2 * (label + size) + 14
    fig = plt.figure(figsize=(width / 100, height / 100), dpi=100)
    fig.text(0.03, 1 - 42 / height, title, fontsize=22, fontweight='bold', color=INK, va='center')
    fig.text(0.03, 1 - 82 / height, subtitle, fontsize=13, color=MUTED, va='center')
    for i, key in enumerate(PANELS):
        x, y = left + (i % 6) * (size + gap), top + label + (i // 6) * (label + size)
        ax = fig.add_axes([x / width, 1 - (y + size) / height, size / width, size / height])
        im = draw(ax, key, res[key])
        ax.set_title(ALL[key][0], fontsize=13, fontweight='bold' if key == 'hsn' else 'normal', color=ALL[key][1] if key == 'hsn' else INK, pad=5)
        ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(key == 'hsn'); s.set_color(ALL['hsn'][1]); s.set_linewidth(3)
    cax = fig.add_axes([1508 / width, 0.06, 14 / width, 0.72]) if cbar else None
    return fig, cax, im


def make_figures(res):
    FIG.mkdir(parents=True, exist_ok=True)
    gray = dict(cmap='gray', vmin=0, vmax=1, interpolation='nearest')
    fig, _, _ = panels(res, 'swatches', 'One frame of each noise', 'The same 128×128 pixel crop of every method, nearest-neighbour upscaled. Black = 0, white = 1.',
                       lambda ax, k, r: ax.imshow(r['swatch'], **gray))
    save(fig, 'swatches')
    fig, _, _ = panels(res, 'swatches-threshold', 'The same crops thresholded at 50%', 'Pixels with value below 0.5 are black. A good dither mask spreads them evenly with no clumps and no visible pattern.',
                       lambda ax, k, r: ax.imshow(r['swatch'] >= 0.5, **gray))
    save(fig, 'swatches-threshold')

    def spec(ax, k, r):
        return ax.imshow(np.log10(np.maximum(r['p2d'], 1e-9)), cmap='inferno', vmin=-3, vmax=1.5, extent=(-.5, .5, -.5, .5), interpolation='nearest')
    fig, axes, im = panels(res, 'spectra-2d', 'Power spectra', f'2D DFT power of one frame (DC removed, mean of {R} realizations, native period). Centre = low frequency, edges = Nyquist. Shared log scale; white noise = 1.', spec, cbar=True)
    cb = fig.colorbar(im, cax=axes)
    cb.set_ticks([-3, -2, -1, 0, 1]); cb.set_ticklabels(['0.001×', '0.01×', '0.1×', 'white', '10×']); cb.outline.set_visible(False)
    save(fig, 'spectra-2d')

    def hist(ax, k, r):
        ax.bar(np.arange(64), np.array(r['hist64']) - 1, bottom=1, width=1, color=ALL[k][1] if k != 'vnc64' else '#111111')
        ax.axhline(1, color=MUTED, lw=0.8); ax.set_ylim(0.75, 1.25); ax.set_xlim(-0.5, 63.5); ax.set_facecolor('#ffffff')
    fig, _, _ = panels(res, 'histograms', 'Value histograms', f'64 bins over [0,1), pooled over {R} realizations of 256×256, as deviation from the ideal uniform count (grey line; panel spans −25% to +25%).', hist)
    save(fig, 'histograms')

    def acm(ax, k, r):
        a = np.array(r['acorr_map']); a[6, 6] = np.nan
        return ax.imshow(a, cmap='RdBu_r', vmin=-0.6, vmax=0.6, extent=(-6.5, 6.5, 6.5, -6.5), interpolation='nearest')
    fig, axes, im = panels(res, 'autocorrelation', 'Autocorrelation at small lags', 'Correlation between a pixel and its neighbour at offsets up to ±6 pixels (centre = zero lag, blanked). Blue = neighbours differ, red = neighbours agree.', acm, cbar=True)
    cb = fig.colorbar(im, cax=axes); cb.outline.set_visible(False)
    save(fig, 'autocorrelation')

    # radial power and anisotropy
    for name, field, title, sub, ylabel, ylim in (
            ('radial-power', 'radial', 'Radially averaged power spectrum', 'Mean power in rings of constant spatial frequency, in dB relative to white noise. Blue noise is low on the left, flat on the right. Clipped at −45 dB.', 'power relative to white (dB)', (-46, 32)),
            ('anisotropy', 'aniso', 'Radial anisotropy', f'Variance of power within each frequency ring over its squared mean, mean periodogram of {R} realizations. Isotropic noise sits at −9 dB (dotted).', 'anisotropy (dB)', (-14, 42))):
        fig, axes = figure(title, sub, 7.4, header=2.0)
        ax = axes[0, 0]
        for k in METHODS:
            n = res[k]['n']
            y = np.array(res[k][field], float)
            if field == 'radial':
                y = 10 * np.log10(np.maximum(y, 10 ** -4.5))
            line(ax, k, np.arange(1, n // 2 + 1) / n, y, **(dict(lw=1.1) if k in ('ign', 'r2', 'tjs', 'bayer') else {}))
        ax.axhline(0 if field == 'radial' else -10 * np.log10(R), color=MUTED, lw=1, ls=':')
        ax.set_xlim(0, 0.5); ax.set_ylim(*ylim); ax.set_xlabel('spatial frequency (cycles per pixel; 0.5 = Nyquist)'); ax.set_ylabel(ylabel)
        if field == 'radial':
            for m_ in (1, 2, 3, 4):
                ax.axvline(m_ / 8, color=GRID, lw=1, zorder=0)
            ax.text(0.127, 28.5, f'multiples of 1/8 cycle/pixel ({SHORT} tile size)', color=MUTED, fontsize=11)
        legend(fig, 7.4)
        save(fig, name)

    # filtered error
    fig, axes = figure('Error left after a Gaussian blur', 'RMS error of a blurred frame against the ideal flat result. Left: the noise value (target 0.5). Right: noise thresholded at 16 levels t (target t), pooled. Lower is better.', 8.4, 1, 2, header=2.35, wspace=0.16)
    for ax, field, name in zip(axes[0], ('value_err', 'thresh_err'), ('Value test', 'Threshold test')):
        for k in METHODS:
            line(ax, k, SIGMAS, res[k][field][:len(SIGMAS)], marker='o', ms=4 if k != 'hsn' else 6)
        ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xticks(SIGMAS); ax.set_xticklabels([str(s) for s in SIGMAS]); ax.minorticks_off()
        ax.set_xlabel('Gaussian blur sigma (pixels)'); ax.set_ylabel('RMS error'); ax.set_title(name, loc='left', fontsize=14, fontweight='bold', color=INK)
    legend(fig, 8.4)
    save(fig, 'filtered-error')

    fig, axes = figure('Filtered threshold error by threshold level', 'RMS error of (noise < t) after a sigma = 2 pixel Gaussian blur, for each of the 16 threshold levels t. Log scale; lower is better.', 7.0, header=2.0)
    j = SIGMAS.index(2)
    for k in METHODS:
        line(axes[0, 0], k, THRESHOLDS, [row[j] for row in res[k]['thresh_err_by_t']], marker='o', ms=4 if k != 'hsn' else 6)
    axes[0, 0].set_yscale('log'); axes[0, 0].set_ylim(4e-3, 1e-1); axes[0, 0].yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter()); axes[0, 0].set_xlabel('threshold level t'); axes[0, 0].set_ylabel('RMS error after blur'); axes[0, 0].set_xlim(0, 1)
    legend(fig, 7.0)
    save(fig, 'threshold-error-by-level')

    # local stratification
    fig, axes = figure('Local stratification: error of window means', 'RMS error of the mean of a w×w pixel window, relative to white noise (= 1). Left: windows on the w-pixel grid. Right: every pixel offset. Exact zeros drawn at 0.001.', 8.2, 1, 2, header=2.35, wspace=0.16)
    for ax, field, name in zip(axes[0], ('aligned', 'any'), ('Aligned windows', 'Windows at every offset')):
        for k in METHODS:
            y = [max(res[k]['win'][str(w)][field] / (12 ** -0.5 / w), 1e-3) for w in WINDOWS]
            line(ax, k, WINDOWS, y, marker='o', ms=5 if k != 'hsn' else 8)
        ax.set_xscale('log', base=2); ax.set_yscale('log'); ax.set_xticks(WINDOWS); ax.set_xticklabels([f'{w}×{w}' for w in WINDOWS]); ax.set_ylim(8e-4, 3)
        ax.set_xlabel('window size (pixels)'); ax.set_ylabel('RMS error of window mean ÷ white noise'); ax.set_title(name, loc='left', fontsize=14, fontweight='bold', color=INK)
    legend(fig, 8.2)
    save(fig, 'window-stratification')

    fig, axes = figure(f'{SHORT}: what happens off the 8×8 grid', f'RMS error of w×w window means for {SHORT} as a function of where the window starts inside the 8×8 tile, relative to white noise (= 1). (0,0) is the aligned case.', 5.6, 1, 4, header=1.5, wspace=0.25)
    axes[0, 0].get_gridspec().update(left=0.05, right=0.90, bottom=0.13)
    for ax, w in zip(axes[0], WINDOWS):
        a = np.array(res['hsn']['win'][str(w)]['by_offset']) / (12 ** -0.5 / w)
        im = ax.imshow(a, cmap='viridis', vmin=0, vmax=1, interpolation='nearest')
        for (yy, xx), v in np.ndenumerate(a):
            ax.text(xx, yy, f'{v:.2f}'.lstrip('0') if v < 1 else f'{v:.1f}', ha='center', va='center', fontsize=8.5, color='white' if v < 0.6 else 'black')
        ax.set_title(f'{w}×{w} windows', fontsize=13, color=INK); ax.grid(False); ax.set_xticks(range(8)); ax.set_yticks(range(8))
        ax.set_xlabel('window start x mod 8')
    axes[0, 0].set_ylabel('window start y mod 8')
    cb = fig.colorbar(im, cax=fig.add_axes([0.925, 0.13, 0.012, 0.6])); cb.outline.set_visible(False); cb.set_label('÷ white noise')
    save(fig, 'window-offsets')


# ---------------------------------------------------------------- tables

def make_tables(res):
    L = lambda k: (f'**{SHORT}**' if k == 'hsn' else ALL[k][0])
    w = res['white']
    out = []
    data = []  # the same tables as JSON, for the website

    def table(title, head, rows):
        out.append(f'### {title}\n\n| Method | ' + ' | '.join(head) + ' |\n| --- |' + ' ---: |' * len(head))
        out.extend(f'| {L(k)} | ' + ' | '.join(cells) + ' |' for k, cells in rows)
        out.append('')
        data.append(dict(id=title.split('.')[0], title=title, head=list(head), rows=[[ALL[k][0], *cells] for k, cells in rows], keys=[k for k, _ in rows]))

    table('A. Histogram and uniformity (256×256, mean of 8 realizations)',
          ['mean', 'variance ×12', 'χ² 64 bins (dof 63)', 'χ² 256 bins (dof 255)', 'max bin deviation, 64 bins', 'max bin deviation, 256 bins', 'distinct values'],
          [(k, [f"{h['mean']:.4f}", f"{h['var12']:.4f}", f"{h['chi2_64']:.1f}", f"{h['chi2_256']:.1f}", f"{h['maxdev_64']:.1%}", f"{h['maxdev_256']:.1%}", str(h['distinct'])])
           for k in ALL for h in [res[k]['hist']]])
    table('D1. Fraction of spectral power below a cutoff frequency, as a multiple of white noise',
          [f'f < {c:g} c/px (white = {w["spec"]["low_white"][str(c)]:.2%})' for c in CUTS],
          [(k, [f"{s['low'][str(c)] / s['low_white'][str(c)]:.4f}×" for c in CUTS]) for k in ALL for s in [res[k]['spec']]])
    table('D2. Spectral peakiness (power in the single largest bin) and anisotropy',
          ['FFT size', 'largest bin, values', 'largest bin, 50% mask', 'largest bin, 50% mask, 128² crop', 'same, Hann window', 'anisotropy mean (dB)', 'anisotropy median (dB)', 'anisotropy max (dB)'],
          [(k, [str(res[k]['n']), f"{s['peak_value']:.3%}", f"{s['peak_mask']:.3%}", f"{s['peak_mask128']:.3%}", f"{s['peak_mask128_hann']:.3%}", f"{s['ani_mean']:+.1f}", f"{s['ani_median']:+.1f}", f"{s['ani_max']:+.1f}"])
           for k in ALL for s in [res[k]['spec']]])
    cols = [SIGMAS.index(1), SIGMAS.index(2), SIGMAS.index(4), len(SIGMAS), len(SIGMAS) + 1]
    head = ['Gaussian σ=1', 'Gaussian σ=2', 'Gaussian σ=4', 'box 3×3', 'box 5×5']
    for field, title in (('value_err', 'E1. Filtered error, value test: RMS(blur(noise) − 0.5) ×10³ (multiple of white)'),
                         ('thresh_err', 'E2. Filtered error, threshold test: RMS(blur(noise < t) − t) ×10³ pooled over 16 thresholds (multiple of white)')):
        table(title, head, [(k, [f"{res[k][field][j] * 1e3:.2f} ({res[k][field][j] / w[field][j]:.2f}×)" for j in cols]) for k in ALL])
    for field, name in (('value_err', 'value'), ('thresh_err', 'threshold')):
        table(f'E{3 if name == "value" else 4}. All Gaussian widths, {name} test, RMS ×10³', [f'σ={s}' for s in SIGMAS],
              [(k, [f"{v * 1e3:.2f}" for v in res[k][field][:len(SIGMAS)]]) for k in ALL])
    rel = lambda v, ww: f'{v / (12 ** -0.5 / ww):.3f}'
    table('F1. Window-mean RMS error relative to white noise (white = 1; theory 0.2887/w): aligned / every offset / worst offset class (mod 8)',
          [f'{ww}×{ww}' for ww in WINDOWS],
          [(k, [f"{rel(d['aligned'], ww)} / {rel(d['any'], ww)} / {rel(d['worst_offset'], ww)}" for ww in WINDOWS for d in [res[k]['win'][str(ww)]]]) for k in ALL])
    table('F2. 8-pixel periodicity: share of power on the 1/8-cycle lattice (63 bins at multiples of 1/8 c/px in both axes) and on the comb (either axis)',
          ['lattice share (values)', 'white expectation', 'largest lattice bin (white = 1)', 'lattice share (50% mask)', 'comb share', 'white expectation'],
          [(k, [f"{s['lattice_frac']:.3%}", f"{s['lattice_white']:.3%}", f"{s['lattice_max']:.2f}", f"{s['mask_lattice_frac']:.3%}", f"{s['comb_frac']:.2%}", f"{s['comb_white']:.2%}"])
           for k in ALL for s in [res[k]['spec']]])
    table('G. Autocorrelation at small lags (dx,dy)', [f'({l})' for l in res['hsn']['acorr']],
          [(k, [f'{v:+.3f}' for v in res[k]['acorr'].values()]) for k in ALL])
    h = res['hsn']['hsn_lines64']
    details = [
        'Horizontal nearest-neighbour correlation by position of the pair inside the tile: ' + '; '.join(f'{k}: {v:+.3f}' for k, v in res['hsn']['hsn_pairs'].items()) + '.',
        f"With 64 seeds averaged: lattice share {h['lattice_frac']:.4%} (white 0.0961%), mean lattice bin {h['lattice_mean']:.3f}× white, largest lattice bin {h['lattice_max']:.3f}× white, "
        f"largest non-lattice bin {h['other_max']:.3f}× white, comb share {h['comb_frac']:.2%}, lowest-frequency level (f ≤ 1/64 c/px; theory 1/64 = −18.1 dB) {h['plateau_db']:.1f} dB.",
        f"Largest aligned-window |mean − 0.5| for {SHORT}: " + ', '.join(f"{ww}×{ww}: {res['hsn']['win'][str(ww)]['max_abs_aligned']:.5f}" for ww in WINDOWS) + '.']
    out.append(f'### {SHORT} details\n\n' + '\n\n'.join(details))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'tables.md').write_text('\n'.join(out) + '\n')
    (OUT / 'tables.json').write_text(json.dumps(dict(short=SHORT, tables=data, details=details), indent=1, ensure_ascii=False) + '\n')


def main():
    nz.selfcheck()
    with Pool(8) as pool:
        res = dict(pool.map(compute, list(ALL)))
    make_tables(res)
    make_figures(res)
    slim = {k: {a: b for a, b in v.items() if a not in ('p2d', 'swatch')} for k, v in res.items()}
    (OUT / 'results.json').write_text(json.dumps(slim, indent=1) + '\n')
    print('done')


if __name__ == '__main__':
    main()
