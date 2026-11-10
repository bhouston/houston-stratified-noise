# Builds results/gpu/figures/in-engine-results.webp (1600 px wide) from the committed metrics JSON and the image crops in crops/.
# Run from the repository root: pnpm analysis:gpu
import json, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from paths import OUT, CROPS, savefig

rt = json.load(open(OUT + 'realtime_metrics.json'))
bake = json.load(open(OUT + 'bake_metrics.json'))
crop = lambda name: np.asarray(Image.open(CROPS + name + '.webp').convert('RGB')) / 255

SURFACE, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
COLORS = {'hsn': '#2a78d6', 'hash': '#eb6834', 'ign': '#1baf7a', 'vc': '#6250d6', 'hsnr2': '#eda100', 'shared': '#e87ba4'}
LABELS = {'hsn': 'HSN (upstream PR)', 'hash': 'Hash + R$_d$ steps', 'ign': 'IGN + R$_d$ steps', 'vc': 'Void-and-cluster + R$_d$', 'hsnr2': 'HSN, R2 steps', 'shared': 'HSN, shared golden step'}
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'text.color': INK, 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
                     'axes.edgecolor': GRID, 'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE})

fig = plt.figure(figsize=(16, 16.4), dpi=100)
gs = fig.add_gridspec(4, 12, height_ratios=[4.0, 2.75, 2.75, 3.5], hspace=0.2, wspace=0.6, left=0.045, right=0.985, top=0.895, bottom=0.012)
fig.suptitle('Houston Stratified Noise (HSN) in Three.js: measured change against the previous code', fontsize=17, fontweight='bold', x=0.045, ha='left', y=0.988)
fig.text(0.045, 0.957, 'Apple GPU (Metal, hardware WebGPU), 960×720, stationary camera, linear float readback. Bars are % change against the previous sampler; lower is better. Error bars: ±1 SD over repeats.', color=INK2, fontsize=11)

def bars(ax, title, metrics, series, values, sds, ylim):
    n = len(series); width = 0.8 / n
    for i, s in enumerate(series):
        x = np.arange(len(metrics)) + (i - (n - 1) / 2) * width
        ax.bar(x, values[s], width * 0.9, color=COLORS[s], label=LABELS[s], yerr=sds[s], ecolor=INK2, error_kw=dict(lw=1), zorder=3)
        for xi, v in zip(x, values[s]):
            shown = min(max(v, ylim[0]), ylim[1])
            ax.text(xi, shown + (3 if v >= 0 else -3) * (ylim[1] - ylim[0]) / 200, f'{v:+.0f}%' if abs(v) >= 10 else f'{v:+.1f}%', ha='center', va='bottom' if v >= 0 else 'top', fontsize=7.5, color=INK)
    ax.axhline(0, color=INK2, lw=1, zorder=4)
    ax.set_xticks(np.arange(len(metrics))); ax.set_xticklabels(metrics, fontsize=11, color=INK)
    ax.set_ylim(*ylim); ax.set_title(title, loc='left', fontsize=13, fontweight='bold', pad=44)
    ax.yaxis.grid(True, color=GRID, zorder=0); ax.set_axisbelow(True)
    ax.tick_params(length=0); [sp.set_visible(False) for sp in ax.spines.values()]
    ax.yaxis.set_major_formatter(lambda v, _: f'{v:+.0f}%')
    ax.legend(loc='lower left', bbox_to_anchor=(0, 1.0), ncol=3, frameon=False, fontsize=9, handlelength=1, columnspacing=0.9, borderaxespad=0.1)

def realtime(ax, fx, title, series, ylim):
    v = rt[fx]['variants']; base = v['base']['mean']
    keys = ('rmse', 'bias', 'flicker')
    vals = {s: [(v[s]['mean'][k] / base[k] - 1) * 100 for k in keys] for s in series}
    sds = {s: [v[s]['sd'][k] / base[k] * 100 for k in keys] for s in series}
    bars(ax, title, ['RMSE', 'Bias', 'Flicker'], series, vals, sds, ylim)

realtime(fig.add_subplot(gs[0, 0:4]), 'vxgi', 'VXGI, real time (before: IGN pair)', ['hsn', 'hash', 'ign', 'vc', 'hsnr2'], (-90, 60))
realtime(fig.add_subplot(gs[0, 4:8]), 'ssr', 'SSR, denoised (before: analytic R2)', ['hsn', 'hash', 'ign', 'vc'], (-90, 60))
b = bake['samplers']; keys = ('rmse', 'bias', 'grain')
bars(fig.add_subplot(gs[0, 8:12]), 'Light map bake, 64 samples (before: IGN pair)', ['RMSE', 'Bias (low-pass)', 'Grain (high-pass)'], ['shared', 'hsnr2'],
     {s: [(b[m]['mean'][k] / b['prev']['mean'][k] - 1) * 100 for k in keys] for s, m in (('shared', 'shared'), ('hsnr2', 'r2'))},
     {s: [b[m]['sd'][k] / b['prev']['mean'][k] * 100 for k in keys] for s, m in (('shared', 'shared'), ('hsnr2', 'r2'))}, (-110, 310))

def show(ax, img, title, nearest=True):
    ax.imshow(np.clip(img, 0, 1), interpolation='nearest' if nearest else 'lanczos'); ax.set_xticks([]); ax.set_yticks([])
    [sp.set_edgecolor(GRID) for sp in ax.spines.values()]
    ax.set_title(title, loc='left', fontsize=10.5, color=INK, pad=5, linespacing=1.3)

def realtime_images(row, fx, name, before_label, box, exposure, gain):
    for i, (v, label) in enumerate((('base', before_label), ('hsn', 'after (HSN)'))):
        show(fig.add_subplot(gs[row, i * 3:i * 3 + 3]), crop(f'{fx}_{v}_frame'), f'{name} {label}\none frame after TRAA, crop')
        show(fig.add_subplot(gs[row, 6 + i * 3:9 + i * 3]), crop(f'{fx}_{v}_error_full'), f'{name} {label}\n256-frame mean − reference, ×{gain}', nearest=False)

realtime_images(1, 'vxgi', 'VXGI', 'before (IGN pair)', (240, 140, 300, 200), 1.6, 40)
realtime_images(2, 'ssr', 'SSR', 'before (analytic R2)', (470, 400, 300, 200), 2.5, 300)

for i, (m, label) in enumerate((('prev', 'before (IGN pair)'), ('shared', 'HSN, shared golden step'), ('r2', 'HSN, R2 steps'), (None, 'reference'))):
    show(fig.add_subplot(gs[3, i * 3:i * 3 + 3]), crop(f"bake_{m or 'reference'}"), f'Light map bake, {label}\n64 samples, crop' if m else 'Light map bake, reference\nwhite noise, 8,192 samples, crop')

savefig(fig, 'in-engine-results')
