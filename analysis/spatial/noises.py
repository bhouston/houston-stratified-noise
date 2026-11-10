"""Scalar screen-space noises as functions of integer pixel arrays (x, y) -> float64 in [0, 1).

Integer methods use numpy uint32 (wraps mod 2^32 like WGSL u32). Float methods use numpy float32
so every intermediate rounds like a 32-bit shader float (sin() itself is libm's, not any GPU's).
Run this file directly for the self-checks; `python noises.py vectors` rewrites src/noise/python-vectors.json,
which the JavaScript self-check compares the src/noise modules against.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SHORT = json.loads((ROOT / 'names.json').read_text())['short']  # display name of the noise, set in names.json
U = np.uint32
F = np.float32
np.seterr(over='ignore')


def u32(v):
    return U(v & 0xFFFFFFFF)


def fract(v):
    return v - np.floor(v)


def unit24(v):
    """Top 24 bits of a uint32 as an exactly representable float in [0,1)."""
    return (v >> U(8)).astype(np.float64) / 16777216.0


# --- HSN / HHW (port of examples/jsm/tsl/utils/HierarchicalHashedWeyl.js, three.js PR #35429) ---

def hash_uint(v):
    v = (v ^ (v >> U(16))) * U(0x21F0AAAD)
    v = (v ^ (v >> U(15))) * U(0x735A2D97)
    return v ^ (v >> U(15))


def pixel_hash(x, y, seed):
    return hash_uint((x * U(0x9E3779B1)) ^ (y * U(0x85EBCA77)) ^ u32(seed))


def hsn_bits(x, y, seed=1, index=0, step=2654435769, scramble=True, phase=True):
    x, y = x.astype(U), y.astype(U)
    rank = np.zeros_like(x)
    for level in range(3):
        s = pixel_hash(x >> U(level + 1), y >> U(level + 1), seed ^ ((level + 1) * 0x632BE5AB)) if scramble else np.zeros_like(x)
        a = (x >> U(level)) & U(1)
        b = (y >> U(level)) & U(1)
        low = np.where((s & U(4)) != 0, a, b)
        child = ((a ^ b) << U(1)) | low
        rank |= (child ^ (s & U(3))) << U(30 - 2 * level)
    ph = pixel_hash(x >> U(3), y >> U(3), seed ^ 0x02E5BE93) if phase else U(0)
    return rank + ph + u32(index * step)


def hsn(x, y, seed=1, index=0, step=2654435769):
    return unit24(hsn_bits(x, y, seed, index, step))


# --- white-noise hashes ---

def white_hsn_hash(x, y, seed=1):
    """White noise from the same integer hash HSN uses."""
    return unit24(pixel_hash(x.astype(U), y.astype(U), seed))


def pcg3d(x, y, z):
    """Jarzynski & Olano 2020, pcg3d; returns the x output."""
    x, y, z = (v * U(1664525) + U(1013904223) for v in (x.astype(U), y.astype(U), z.astype(U)))
    x = x + y * z; y = y + z * x; z = z + x * y
    x ^= x >> U(16); y ^= y >> U(16); z ^= z >> U(16)
    x = x + y * z
    return x


def white_pcg(x, y, seed=1):
    return unit24(pcg3d(x, y, np.full(x.shape, seed, U)))


def sin_hash(x, y):
    """fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453), float32."""
    d = x.astype(F) * F(12.9898) + y.astype(F) * F(78.233)
    return fract(np.sin(d) * F(43758.5453)).astype(np.float64)


def hash12(x, y):
    """Dave Hoskins 'hash without sine' hash12, float32."""
    px, py = x.astype(F), y.astype(F)
    p3 = [fract(px * F(.1031)), fract(py * F(.1031)), fract(px * F(.1031))]
    d = p3[0] * (p3[1] + F(33.33)) + p3[1] * (p3[2] + F(33.33)) + p3[2] * (p3[0] + F(33.33))
    p3 = [p + d for p in p3]
    return fract((p3[0] + p3[1]) * p3[2]).astype(np.float64)


# --- structured arithmetic noises ---

def ign(x, y):
    """Jimenez interleaved gradient noise, float32."""
    return fract(F(52.9829189) * fract(F(0.06711056) * x.astype(F) + F(0.00583715) * y.astype(F))).astype(np.float64)


PLASTIC = 1.32471795724474602596


def r2_roberts(x, y):
    """Martin Roberts' R2 dither mask fract(x/g + y/g^2), float64 (exact to ~1e-12 at screen coordinates)."""
    return fract(x.astype(np.float64) / PLASTIC + y.astype(np.float64) / PLASTIC ** 2)


def threejs_analytic(x, y, seed=47, index=0, channel=0):
    """bindAnalyticNoise from three.js examples/jsm/tsl/utils/RNoise.js (dev), float32.

    The SSR 'Analytic R2' that PR #35429 replaces. Coordinates are wrapped to a 32x32 tile that is
    shifted per sample index; all four channels are fract(c_k * t) of the same t.
    """
    P = PLASTIC
    i = F(index + seed)
    ox = np.floor(fract(i * F(0.7548776662)) * F(32))
    oy = np.floor(fract(i * F(0.5698402910)) * F(32))
    cx = np.mod(x.astype(F) + ox, F(32))
    cy = np.mod(y.astype(F) + oy, F(32))
    t = cx * F(1 / P) + cy * F(1 / P ** 2) + F(seed)
    a, b = [(P, 1 / P), (P * 2, 1 / P ** 2), (P * 3, 0.4198754210), (P * 4, 1 / P ** 3)][channel]
    return fract(t * F(a) * F(b)).astype(np.float64)


def bayer_index(x, y):
    """Standard recursive 8x8 Bayer index 0..63: M2 = [[0,2],[3,1]], M2n = 4*M_n(x%n,y%n) + M2(x//n,y//n)."""
    m = np.array([[0, 2], [3, 1]])
    n = 2
    while n < 8:
        m = np.block([[4 * m + 0, 4 * m + 2], [4 * m + 3, 4 * m + 1]])
        n *= 2
    return m[y % 8, x % 8]


def bayer(x, y):
    return (bayer_index(x, y) + 0.5) / 64


# --- textures (tiled toroidally) ---

def tile(tex):
    return lambda x, y: tex[y % tex.shape[0], x % tex.shape[1]]


def load_fast(name='gauss1-ema01-spatial', slices=range(0, 32, 4)):
    """EA FAST scalar texture: B channel of the left 128 columns of the three.js PR #35244 atlas, 128x128 per slice."""
    a = np.asarray(Image.open(ROOT / 'textures/fast' / f'{name}.png').convert('RGB'))
    assert a.shape == (4096, 256, 3)
    return [(a[t * 128:(t + 1) * 128, :128, 2] + 0.5) / 256 for t in slices]


def load_peters(n=8):
    """Christoph Peters' free blue noise (CC0), 256x256 16-bit scalar HDR_L_k."""
    out = []
    for k in range(n):
        a = np.asarray(Image.open(ROOT / f'textures/peters/HDR_L_{k}.png'))
        if a.ndim == 3:
            a = a[..., 0]
        assert a.shape == (256, 256) and a.dtype == np.uint16, (a.shape, a.dtype)
        out.append((a + 0.5) / 65536)
    return out


def selfcheck():
    y, x = np.mgrid[:256, :256]
    # 1. HSN: every aligned 8x8 tile's top-6-bit ranks are a permutation of 0..63 (also 2x2 / 4x4 strata)
    for seed in (1, 2, 189, 0xDEADBEEF):
        for index in (0, 1, 12345):
            v = hsn(x, y, seed, index)
            r = np.floor(v * 64).astype(int).reshape(32, 8, 32, 8).transpose(0, 2, 1, 3).reshape(-1, 64)
            assert (np.sort(r, 1) == np.arange(64)).all(), f'{SHORT} 8x8 tile is not a permutation'
    bits = hsn_bits(x, y, 1, phase=False)
    for w, shift in ((2, 30), (4, 28)):
        r = (bits >> U(shift)).astype(int).reshape(256 // w, w, 256 // w, w).transpose(0, 2, 1, 3).reshape(-1, w * w)
        assert (np.sort(r, 1) == np.arange(w * w)).all(), f'{SHORT} {w}x{w} strata broken'
    # 2. unscrambled, unphased HSN is exactly the standard Bayer matrix
    assert ((hsn_bits(x, y, 1, scramble=False, phase=False) >> U(26)) == bayer_index(x, y)).all()
    # 3. bit-exact against the test vectors of the JavaScript reference (src/noise/hsn-vectors.json), which were
    #    generated from the reference that matches the three.js PR and the CPU model that matched GPU output
    cases = json.loads((ROOT / 'src/noise/hsn-vectors.json').read_text())['cases']
    for cx, cy, index, seed, step, bits in cases:
        assert int(hsn_bits(np.array([cx]), np.array([cy]), seed, index, step)[0]) == bits, (cx, cy, index, seed, step)
    print(f'{SHORT} matches the JavaScript reference bit-for-bit on {len(cases)} test vectors')
    # 4. pcg3d test vector computed independently with Python ints
    def pcg_int(x, y, z):
        M = 0xFFFFFFFF
        x, y, z = ((v * 1664525 + 1013904223) & M for v in (x, y, z))
        x = (x + y * z) & M; y = (y + z * x) & M; z = (z + x * y) & M
        x ^= x >> 16; y ^= y >> 16; z ^= z >> 16
        return (x + y * z) & M
    for p in ((0, 0, 0), (1, 2, 3), (255, 1023, 7)):
        assert int(pcg3d(*(np.array([v]) for v in p))[0]) == pcg_int(*p)
    for f in (white_pcg, white_hsn_hash, sin_hash, hash12, ign, r2_roberts, threejs_analytic, bayer):
        v = f(x + 1024, y + 1024)
        assert v.min() >= 0 and v.max() < 1, f.__name__
    print('self-checks passed')


def write_vectors():
    """Values of the non-HSN noises at 64 screen coordinates, for the JavaScript self-check."""
    k = np.arange(64)
    x, y = 1024 + (k * 37) % 1300, 1024 + (k * 91) % 1300
    out = {'x': x.tolist(), 'y': y.tolist(),
           'whitePcg': white_pcg(x, y, 3).tolist(), 'whiteHsnHash': white_hsn_hash(x, y, 3).tolist(),
           'hash12': hash12(x, y).tolist(), 'ign': ign(x, y).tolist(), 'r2': r2_roberts(x, y).tolist(), 'bayer': bayer(x, y).tolist(),
           'sinHash': sin_hash(x, y).tolist(),
           'threejsAnalytic': [[threejs_analytic(x, y, 47, index, ch).tolist() for ch in range(4)] for index in (0, 1, 7)]}
    (ROOT / 'src/noise/python-vectors.json').write_text(json.dumps(out, indent='\t') + '\n')


if __name__ == '__main__':
    selfcheck()
    if sys.argv[1:] == ['vectors']:
        write_vectors()
