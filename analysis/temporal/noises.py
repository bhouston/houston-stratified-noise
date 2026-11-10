"""Noise methods as functions of integer pixel (x, y), frame n and dimension count D.

Every sampler has the signature  f(x, y, n, D) -> float32 array of shape (D,) + broadcast(x, y, n)
with x, y, n int64 arrays.  Integer paths emulate uint32 wrap; float paths are float32 like a shader.
Run this file directly for the self-checks.
"""
import hashlib
import io
import json
import os
import urllib.request
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CACHE = os.path.join(HERE, 'cache')  # gitignored: generated void-and-cluster texture and the downloaded STBN slices
SHORT = json.load(open(os.path.join(ROOT, 'names.json')))['short']  # display name of the noise, set in names.json
U = np.uint32
F = np.float32
np.seterr(over='ignore')


def _u(a):
    return (np.asarray(a, dtype=np.int64) & 0xffffffff).astype(np.uint32)


def fract(a):
    return a - np.floor(a)


# ---------------------------------------------------------------- HSN (PR #35429, HierarchicalHashedWeyl.js)

GOLDEN_STEP = 2654435769
R2_STEPS = [3242174889, 2447445413]
R4_STEPS = [3679390609, 3152041523, 2700274805, 2313257605]


def hash_uint(v):
    v = (v ^ (v >> U(16))) * U(0x21f0aaad)
    v = (v ^ (v >> U(15))) * U(0x735a2d97)
    return v ^ (v >> U(15))


def pixel_hash(x, y, seed):
    return hash_uint((x * U(0x9e3779b1)) ^ (y * U(0x85ebca77)) ^ U(seed))


def hsn_u32(x, y, n, seed, step=GOLDEN_STEP):
    """The uint32 value before the final >>8 / 2^24."""
    x, y, n = _u(x), _u(y), _u(n)
    rank = np.zeros(np.broadcast(x, y).shape, np.uint32)
    for level in range(3):
        salt = ((level + 1) * 0x632be5ab) & 0xffffffff
        scramble = pixel_hash(x >> U(level + 1), y >> U(level + 1), seed ^ salt)
        a = (x >> U(level)) & U(1)
        b = (y >> U(level)) & U(1)
        low = np.where((scramble & U(4)) != 0, a, b)
        child = ((a ^ b) << U(1)) | low
        rank = rank | ((child ^ (scramble & U(3))) << U(30 - 2 * level))
    phase = pixel_hash(x >> U(3), y >> U(3), seed ^ 0x02e5be93)
    return rank + phase + n * U(step)


def hsn1(x, y, n, seed, step=GOLDEN_STEP):
    return (hsn_u32(x, y, n, seed, step) >> U(8)).astype(F) / F(16777216)


def _steps(D):
    return {1: [GOLDEN_STEP], 2: R2_STEPS, 4: R4_STEPS}[D]


def hsn(x, y, n, D, seed=0):
    """Per-dimension seeds seed*4+k+1 (as bindHierarchicalHashedWeyl) and golden / R2 / R4 steps for D = 1 / 2 / 4."""
    return np.stack([hsn1(x, y, n, seed * 4 + k + 1, s) for k, s in enumerate(_steps(D))])


def hsn_shared(x, y, n, D):
    """Deliberately broken: the golden step in every dimension."""
    return np.stack([hsn1(x, y, n, k + 1, GOLDEN_STEP) for k in range(D)])


def hsn_pr_vxgi(x, y, n, D):
    """What the PR's VXGINode actually calls: bindHierarchicalHashedWeyl(res, 29).xy = first D of the R4 steps."""
    return np.stack([hsn1(x, y, n, 29 * 4 + k + 1, R4_STEPS[k]) for k in range(D)])


# ---------------------------------------------------------------- white noise (PCG, three.js Hash.js)

def pcg(v):
    state = v * U(747796405) + U(2891336453)
    word = ((state >> ((state >> U(28)) + U(4))) ^ state) * U(277803737)
    return (word >> U(22)) ^ word


def white(x, y, n, D, salt=0):
    x, y, n = _u(x), _u(y), _u(n)
    out = []
    for d in range(D):
        h = pcg(x ^ pcg(y ^ pcg(n ^ pcg(np.array(d + 1 + 1000 * salt, np.uint32)))))
        out.append((h >> U(8)).astype(F) / F(16777216))  # top 24 bits so the float stays < 1
    return np.stack(np.broadcast_arrays(*out))


# ---------------------------------------------------------------- interleaved gradient noise

def ign(px, py):
    return fract(F(52.9829189) * fract(px * F(0.06711056) + py * F(0.00583715)))


# dim 1 offset is exactly the removed VXGINode.js code; dims 2, 3 are arbitrary fixed offsets of our own
IGN_OFFSETS = [(0.0, 0.0), (5.588238, 3.14159), (47.0, 17.0), (101.0, 59.0)]


def ign_anim(x, y, n, D, cycle=None):
    """IGN(screenCoordinate + frame * 5.588238 [+ offset_d]); screenCoordinate is the pixel centre (x + 0.5)."""
    n = np.asarray(n, np.int64)
    shift = (n % cycle if cycle else n).astype(F) * F(5.588238)
    px = (np.asarray(x).astype(F) + F(0.5)) + shift
    py = (np.asarray(y).astype(F) + F(0.5)) + shift
    out = [ign(px, py) if d == 0 else ign(px + F(IGN_OFFSETS[d][0]), py + F(IGN_OFFSETS[d][1])) for d in range(D)]
    return np.stack(np.broadcast_arrays(*out))


def ign_vxgi(x, y, n, D):
    """Removed VXGINode.js code: frame = frameId % 64."""
    return ign_anim(x, y, n, D, cycle=64)


# ---------------------------------------------------------------- analytic R2 as SSRNode.js used it (RNoise.js)

P = 1.32471795724474602596


def analytic_r2_ssr(x, y, n, D, seed=47):
    index = np.asarray(n, np.int64) + seed
    fi = index.astype(F)
    ox = np.floor(fract(fi * F(0.7548776662)) * F(32))
    oy = np.floor(fract(fi * F(0.5698402910)) * F(32))
    cx = np.mod(np.asarray(x).astype(F) + ox, F(32))
    cy = np.mod(np.asarray(y).astype(F) + oy, F(32))
    t = cx * F(1 / P) + cy * F(1 / P ** 2) + F(seed)
    out = [
        fract(t * F(P) * F(1 / P)),
        fract(t * F(P * 2) * F(1 / P ** 2)),
        fract(t * F(P * 3) * F(0.4198754210)),
        fract(t * F(P * 4) * F(1 / P ** 3)),
    ][:D]
    return np.stack(np.broadcast_arrays(*out)).astype(F)


# ---------------------------------------------------------------- generic "analytic R_d": per-pixel offset + n * alpha_d (float32)

G1 = (1 + 5 ** 0.5) / 2
G4 = 1.1673039782614187  # real root of x^5 = x + 1
ALPHAS = {1: [1 / G1], 2: [1 / P, 1 / P ** 2], 4: [1 / G4 ** k for k in (1, 2, 3, 4)]}


def rd_white(x, y, n, D):
    """fract(whiteHash_d(x, y) + float(n) * alpha_d), float32."""
    off = white(x, y, np.zeros_like(np.asarray(n)), D, salt=7)
    nf = np.asarray(n).astype(F)
    return np.stack([fract(off[d] + nf * F(ALPHAS[D][d])) for d in range(D)])


def rd_ign(x, y, n, D):
    """fract(IGN(pixel + offset_d) + float(n) * alpha_d), float32 (the common 'IGN + frame * golden ratio')."""
    off = ign_anim(x, y, np.zeros_like(np.asarray(n)), D)
    nf = np.asarray(n).astype(F)
    return np.stack([fract(off[d] + nf * F(ALPHAS[D][d])) for d in range(D)])


# ---------------------------------------------------------------- void-and-cluster 64x64 (Ulichney 1993, toroidal)

def void_and_cluster(size=64, sigma=1.5, seed=1):
    rng = np.random.default_rng(seed)
    d = np.minimum(np.arange(size), size - np.arange(size)).astype(np.float64)
    k = np.exp(-(d[:, None] ** 2 + d[None, :] ** 2) / (2 * sigma ** 2))
    roll = lambda p: np.roll(np.roll(k, p[0], 0), p[1], 1)
    pat = np.zeros((size, size), bool)
    pat.flat[rng.choice(size * size, size * size // 10, replace=False)] = True
    E = np.real(np.fft.ifft2(np.fft.fft2(pat) * np.fft.fft2(k)))
    tightest = lambda: np.unravel_index(np.argmax(np.where(pat, E, -np.inf)), E.shape)
    void = lambda: np.unravel_index(np.argmin(np.where(pat, np.inf, E)), E.shape)
    while True:  # relax the initial pattern
        c = tightest(); pat[c] = False; E -= roll(c)
        v = void(); pat[v] = True; E += roll(v)
        if v == c:
            break
    rank = np.zeros((size, size), np.int64)
    ones = int(pat.sum())
    p0, E0 = pat.copy(), E.copy()
    for r in range(ones - 1, -1, -1):
        c = tightest(); pat[c] = False; E -= roll(c); rank[c] = r
    pat[...] = p0; E[...] = E0
    for r in range(ones, size * size):
        v = void(); pat[v] = True; E += roll(v); rank[v] = r
    return rank


_VC = None


def vc_texture():
    global _VC
    if _VC is None:
        path = os.path.join(CACHE, 'vc64.npy')
        if not os.path.exists(path):
            os.makedirs(CACHE, exist_ok=True)
            np.save(path, void_and_cluster())
        _VC = ((np.load(path) + 0.5) / 4096).astype(F)
    return _VC


VC_OFFSETS = [(0, 0), (23, 41), (47, 13), (11, 53)]  # texel offsets (x, y) per dimension


def _vc(x, y, n, D, alphas):
    tex = vc_texture()
    nf = np.asarray(n).astype(F)
    out = []
    for d in range(D):
        v = tex[(np.asarray(y) + VC_OFFSETS[d][1]) % 64, (np.asarray(x) + VC_OFFSETS[d][0]) % 64]
        out.append(fract(v + nf * F(alphas[d])))
    return np.stack(np.broadcast_arrays(*out))


def vc_golden(x, y, n, D):
    """fract(tex(pixel + offset_d) + float(n) * golden) -- the same step in every dimension (common practice)."""
    return _vc(x, y, n, D, [1 / G1] * D)


def vc_rd(x, y, n, D):
    """As vc_golden but with R_d steps per dimension."""
    return _vc(x, y, n, D, ALPHAS[D])


# ---------------------------------------------------------------- real spatiotemporal textures (downloaded; parsed as images only)

_TEX = {}


# NVIDIA STBN is under a non-commercial licence (see textures/stbn/SOURCE.md), so it is downloaded on first
# use instead of being committed. The archive is pinned by commit and SHA-256; only the 128 PNG slices this
# analysis reads are extracted, under fixed names, and they are only ever parsed as images.
STBN_URL = 'https://raw.githubusercontent.com/NVIDIA-RTX/STBN/48b2839e4d8b7f0202ac72c6b0ae720d235a5b8b/Assets/STBN.zip'
STBN_SHA256 = 'f262aaa79704b913ad1ac22b11674931c5c16a788688f8ce49ec43d59eb5c747'
STBN_FILES = [f'stbn_scalar_2Dx1Dx1D_128x128x64x1_{i}.png' for i in range(64)] + [f'stbn_vec2_2Dx1D_128x128x64_{i}.png' for i in range(64)]


def download_stbn():
    d = os.path.join(CACHE, 'stbn')
    if all(os.path.exists(os.path.join(d, f)) for f in STBN_FILES):
        return d
    print('downloading NVIDIA STBN (30 MB) from', STBN_URL)
    blob = urllib.request.urlopen(STBN_URL, timeout=300).read()
    assert hashlib.sha256(blob).hexdigest() == STBN_SHA256, 'STBN.zip does not match the pinned SHA-256'
    os.makedirs(d, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        members = {os.path.basename(m): m for m in z.namelist()}
        for f in STBN_FILES:
            open(os.path.join(d, f), 'wb').write(z.read(members[f]))
    return d


def _load_stbn():
    if 'stbn' not in _TEX:
        from PIL import Image
        d = download_stbn()
        s = np.stack([np.asarray(Image.open(os.path.join(d, f'stbn_scalar_2Dx1Dx1D_128x128x64x1_{i}.png')).convert('L')) for i in range(64)])
        v = np.stack([np.asarray(Image.open(os.path.join(d, f'stbn_vec2_2Dx1D_128x128x64_{i}.png')).convert('RGB'))[..., :2] for i in range(64)])
        _TEX['stbn'] = (s, v)
    return _TEX['stbn']


def _load_fast():
    if 'fast' not in _TEX:
        from PIL import Image
        a = np.asarray(Image.open(os.path.join(ROOT, 'textures/fast', 'gauss1-ema01-spatio-temporal.png')).convert('RGB'))
        _TEX['fast'] = a.reshape(32, 128, 256, 3)
    return _TEX['fast']


def _cyc(x, y, n, period):
    """Slice index plus the per-cycle tile shift of three.js FASTNoise.js: pixel + (37, 71) * (cycle mod 128)."""
    n = np.asarray(n, np.int64) & 0xffffffff
    c = (n // period) % 128
    return n % period, (np.asarray(x) + 37 * c) % 128, (np.asarray(y) + 71 * c) % 128


def stbn(x, y, n, D):
    """NVIDIA STBN 128x128x64. D=1: scalar; D=2: vec2; D=4: vec2 and the same vec2 at texel offset (49, 83)."""
    s, v = _load_stbn()
    t, px, py = _cyc(x, y, n, 64)
    if D == 1:
        raw = s[t, py, px][None]
    else:
        a = v[t, py, px]
        raw = np.stack([a[..., 0], a[..., 1]])
        if D == 4:
            b = v[t, (py + 83) % 128, (px + 49) % 128]
            raw = np.stack([a[..., 0], a[..., 1], b[..., 0], b[..., 1]])
    return ((raw.astype(F) + F(0.5)) / F(256))


def fast(x, y, n, D):
    """EA FAST 128x128x32 (gauss sigma 1 x EMA 0.1) read as three.js FASTNoise.js does.
    D=1: the scalar ('real') texture; D=2: the vec2 texture; D=4: (vec2.x, vec2.y, real, real shifted)."""
    a = _load_fast()
    t, px, py = _cyc(x, y, n, 32)
    left = a[t, py, px]
    if D == 1:
        raw = left[..., 2][None]
    elif D == 2:
        raw = np.stack([left[..., 0], left[..., 1]])
    else:
        raw = np.stack([left[..., 0], left[..., 1], left[..., 2], a[t, py, px + 128][..., 0]])
    return ((raw.astype(F) + F(0.5)) / F(256))


# ---------------------------------------------------------------- reference bound: independent scrambled Sobol per pixel

def sobol_bound(D, T, npix, seed=1234):
    """(D, T, npix) -- scipy scrambled Sobol (LMS + digital shift), an independent sequence per pixel."""
    from scipy.stats import qmc
    out = np.empty((D, T, npix), F)
    for i in range(npix):
        out[:, :, i] = qmc.Sobol(D, scramble=True, seed=seed + i).random(T).T
    return np.minimum(out, np.nextafter(F(1), F(0)))


# ---------------------------------------------------------------- self-checks

def _selfcheck():
    # step constants are round(2^32 * alpha)
    assert GOLDEN_STEP == round(2 ** 32 / G1)
    assert all(abs(a - round(2 ** 32 * b)) <= 2 for a, b in zip(R2_STEPS, ALPHAS[2]))
    r4 = [round(2 ** 32 * a) for a in ALPHAS[4]]
    assert all(abs(a - b) <= 2 for a, b in zip(R4_STEPS, r4)), (R4_STEPS, r4)
    # every aligned 8x8 tile holds all 64 six-bit ranks once the tile phase is removed
    y, x = np.mgrid[0:64, 0:64]
    for seed in (1, 2, 117):
        v = hsn_u32(x, y, 0, seed)
        ph = pixel_hash(_u(x) >> U(3), _u(y) >> U(3), seed ^ 0x02e5be93)
        r = ((v - ph) >> U(26)).reshape(8, 8, 8, 8).transpose(0, 2, 1, 3).reshape(64, 64)
        assert all(len(set(t)) == 64 for t in r)
    # Weyl step is exact integer arithmetic
    a = hsn_u32(x, y, 10 ** 7, 3, R2_STEPS[1]); b = hsn_u32(x, y, 0, 3, R2_STEPS[1])
    assert np.all((a - b) == U((10 ** 7 * R2_STEPS[1]) & 0xffffffff))
    # bit-exact against the test vectors of the JavaScript reference (src/noise/hsn-vectors.json)
    for cx, cy, index, seed, step, bits in json.load(open(os.path.join(ROOT, 'src/noise/hsn-vectors.json')))['cases']:
        assert int(hsn_u32(np.array([cx]), np.array([cy]), np.array([index]), seed, step)[0]) == bits, (cx, cy, index, seed, step)
    # V&C texture is a permutation
    assert len(np.unique(vc_texture())) == 4096
    for f in (hsn, hsn_shared, white, ign_anim, ign_vxgi, analytic_r2_ssr, rd_white, rd_ign, vc_golden, vc_rd, stbn, fast):
        for D in (1, 2, 4):
            s = f(x[None], y[None], np.arange(5)[:, None, None], D)
            assert s.shape == (D, 5, 64, 64) and s.dtype == np.float32 and s.min() >= 0 and s.max() < 1, (f.__name__, D, s.shape, s.dtype, s.min(), s.max())
    print('noises self-check ok')


if __name__ == '__main__':
    _selfcheck()
