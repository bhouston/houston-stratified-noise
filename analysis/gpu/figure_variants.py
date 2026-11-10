# Builds results/gpu/figures/in-engine-variants.webp: for every sampler variant, one frame after TRAA (crop) and the
# 256-frame mean minus the reference (amplified crop), from the image crops in crops/. Variants without crops yet are skipped.
# Run from the repository root: pnpm analysis:gpu
import os
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from paths import CROPS, savefig

SURFACE, INK, GRID = '#fcfcfb', '#0b0b0b', '#e4e3df'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'text.color': INK, 'figure.facecolor': SURFACE, 'savefig.facecolor': SURFACE})
crop = lambda name: np.asarray(Image.open(CROPS + name + '.webp').convert('RGB')) / 255
NAMES = {'base': 'before', 'hsn': 'HSN (PR)', 'hash': 'A: hash + R_d', 'ign': 'B: IGN + R_d', 'hsnr2': 'C: HSN, R2 steps', 'vc': 'D: void-cluster + R_d',
         'e': 'E: analytic R4, single lattice', 'er2': 'E: single lattice, R2 constants', 'f': 'F: per-dim lattices, R4 steps', 'fr2': 'F: per-dim lattices, R2 steps', 'g': 'G: analytic R4 (fork PR #42)', 'h': 'H: FAST texture (PR #35244)'}
ROWS = [('vxgi', 'VXGI', ['base', 'hsn', 'hash', 'ign', 'vc', 'hsnr2', 'e', 'er2', 'f', 'fr2', 'g', 'h'], (240, 140, 300, 200), 1.6, 40),
        ('ssr', 'SSR', ['base', 'hsn', 'hash', 'ign', 'vc', 'e', 'f', 'g', 'h'], (470, 400, 300, 200), 2.5, 300)]
COLS = 5

fig, axes = plt.subplots(10, COLS, figsize=(16, 29.4), dpi=100, gridspec_kw=dict(left=0.01, right=0.99, top=0.972, bottom=0.005, hspace=0.14, wspace=0.04))
fig.suptitle('Sampler variants: one frame after TRAA (crop) and 256-frame mean minus reference (amplified crop)', fontsize=15, fontweight='bold', x=0.01, ha='left')
for ax in axes.flat: ax.axis('off')
for r, (fx, name, variants, (x, y, w, h), exposure, gain) in enumerate(ROWS):
    for i, v in enumerate([v for v in variants if os.path.exists(CROPS + f'{fx}_{v}_frame.webp')]):
        frame, error = crop(f'{fx}_{v}_frame'), crop(f'{fx}_{v}_error_crop')
        for k, (img, label) in enumerate(((frame, 'one frame'), (error, f'mean − ref, ×{gain}'))):
            ax = axes[r * 6 + (i // COLS) * 2 + k, i % COLS]; ax.axis('on'); ax.set_xticks([]); ax.set_yticks([])
            [sp.set_edgecolor(GRID) for sp in ax.spines.values()]
            ax.imshow(np.clip(img, 0, 1), interpolation='nearest', aspect='auto')
            ax.set_title(f'{name} {NAMES[v]}: {label}', fontsize=8.5, loc='left', pad=4)
savefig(fig, 'in-engine-variants')
