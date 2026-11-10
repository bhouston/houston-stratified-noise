# Cuts the image crops the two figures show out of the harness's float32 images (RAW, about 1.1 GB, not committed)
# and stores them as 8-bit WebP in crops/. Only needed after rerunning the harness. Run: pnpm py analysis/gpu/make_crops.py
import os, numpy as np
from PIL import Image
from paths import RAW, CROPS

srgb = lambda a: np.where(np.clip(a, 0, 1) <= 0.0031308, np.clip(a, 0, 1) * 12.92, 1.055 * np.clip(a, 0, 1) ** (1 / 2.4) - 0.055)
os.makedirs(CROPS, exist_ok=True)


def save(name, img):
    Image.fromarray(np.rint(np.clip(img, 0, 1) * 255).astype(np.uint8)).save(CROPS + name + '.webp', quality=95, method=6)


# real-time effects: (crop box, exposure of the frame crop, gain of the error image), as in the figures
for fx, variants, (x, y, w, h), exposure, gain in (('vxgi', ['base', 'hhw', 'hash', 'ign', 'vc', 'hhwr2', 'e', 'er2', 'f', 'fr2', 'g'], (240, 140, 300, 200), 1.6, 40),
                                                     ('ssr', ['base', 'hhw', 'hash', 'ign', 'vc', 'e', 'f', 'g'], (470, 400, 300, 200), 2.5, 300)):
    L = lambda n: np.fromfile(f'{RAW}{fx}/{n}', dtype=np.float32).reshape(720, 960, 3).astype(np.float64)
    ref = sum(L(n + '_mean.f32') for n in ('white_base_s1', 'white_head_s2', 'white_base_s3', 'white_head_s4')) / 4
    for v in variants:
        if not os.path.exists(f'{RAW}{fx}/{v}_r0_mean.f32'):
            continue  # not measured (yet)
        err = (L(v + '_r0_mean.f32') - ref) * gain + 0.5
        save(f'{fx}_{v}_frame', srgb(L(v + '_r0_last.f32')[y:y + h, x:x + w] * exposure))  # one frame after TRAA
        save(f'{fx}_{v}_error_crop', err[y - 40:y + h + 40, x - 40:x + w + 60])  # 256-frame mean - reference, amplified
        if v in ('base', 'hhw'):  # the whole frame at half resolution (it is shown about 400 px wide)
            save(f'{fx}_{v}_error_full', err.reshape(360, 2, 480, 2, 3).mean((1, 3)))

# light map bake
LB = lambda n: np.fromfile(f'{RAW}bake/{n}', dtype=np.float32).reshape(1024, 1024, 3).astype(np.float64)
x, y, w, h = 20, 150, 200, 190
for m in ('prev', 'shared', 'r2', 'reference'):
    save(f'bake_{m}', srgb((LB('bake_white_mean.f32') if m == 'reference' else LB(f'bake_{m}_r0.f32'))[y:y + h, x:x + w] * 0.3))
