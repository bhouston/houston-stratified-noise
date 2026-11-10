"""Held-out integrands for validating step constants.  Written BEFORE any candidate was scored.
Same tuple format as integrands.py: (name, group, fn(u) -> float64 array, truth).  Fixed RNG seed.
Different from the selection set: random half-planes / half-spaces, random boxes, off-centre discs,
different lobes (GGX alpha 0.5 and 0.15, another light, a Phong lobe, another AO horizon), other smooth functions."""
import itertools, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../temporal'))
from integrands import _ggx_h, _quad, _d, TAU, PAIRS

HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(20261110)


def halfspace_volume(w, c):
    """Vol{u in [0,1]^d : w.u < c}, exact (inclusion-exclusion)."""
    w = np.asarray(w, float); c = c - w[w < 0].sum(); w = np.abs(w); d = len(w)
    tot = sum((-1) ** len(S) * max(0.0, c - sum(w[i] for i in S)) ** d for r in range(d + 1) for S in itertools.combinations(range(d), r))
    return tot / (math.factorial(d) * np.prod(w))


def halfspace(dims, D):
    """Random half-space over the listed dims, through a random point of [0.25, 0.75]^k."""
    w = rng.normal(size=len(dims)); w /= np.linalg.norm(w)
    c = float(w @ rng.uniform(0.25, 0.75, len(dims)))
    name = ' + '.join(f'{a:.3f} u{i + 1}' for a, i in zip(w, dims)) + f' < {c:.3f}'
    return (name, 'halfspace', lambda u: (sum(a * _d(u[i]) for a, i in zip(w, dims)) < c).astype(np.float64), halfspace_volume(w, c))


def box(dims):
    lo = rng.uniform(0, 0.5, len(dims)); hi = lo + rng.uniform(0.3, 0.5, len(dims))
    name = 'box ' + ' x '.join(f'u{i + 1} in [{a:.2f},{b:.2f})' for i, a, b in zip(dims, lo, hi))
    def f(u):
        m = np.ones(np.shape(u[0]), bool)
        for i, a, b in zip(dims, lo, hi):
            m &= (u[i] >= a) & (u[i] < b)
        return m.astype(np.float64)
    return (name, 'box', f, float(np.prod(hi - lo)))


# ---- lobes (2D functions of (u, v))
_L2 = np.array([-0.4, 0.5, 0.8]) / np.linalg.norm([-0.4, 0.5, 0.8])
_M = np.array([0.5, -0.2, 0.84]) / np.linalg.norm([0.5, -0.2, 0.84])


def ggx05(u, v):
    hx, hy, hz = _ggx_h(u, v, 0.5)
    return np.maximum(0, hx * _L2[0] + hy * _L2[1] + hz * _L2[2]) ** 4


def ggx015_hit(u, v):
    hx, hy, hz = _ggx_h(u, v, 0.15)
    return (hx * _L2[0] + hy * _L2[1] + hz * _L2[2] > 0.85).astype(np.float64)


def phong(u, v):
    u = _d(u); v = _d(v)
    c = v ** (1 / 21); s = np.sqrt(np.maximum(0, 1 - c * c))
    return np.maximum(0, s * np.cos(TAU * u) * _M[0] + s * np.sin(TAU * u) * _M[1] + c * _M[2]) ** 6


def ao2(u, v):
    return (np.sqrt(1 - _d(v)) > 0.5 + 0.2 * np.cos(2 * TAU * _d(u))).astype(np.float64)


_cache = os.path.join(HERE, '../../results/steps', 'heldout_truth.json')
if os.path.exists(_cache):
    _T = json.load(open(_cache))
else:
    _T = dict(ggx05=_quad(ggx05), ggx015_hit=_quad(ggx015_hit), phong=_quad(phong))
    os.makedirs(os.path.dirname(_cache), exist_ok=True); json.dump(_T, open(_cache, 'w'))
_T['ao2'] = 1 - (0.25 + 0.04 / 2)


def _gauss1(mu, s):
    return s * math.sqrt(TAU / 4) * (math.erf((1 - mu) / (s * 2 ** 0.5)) + math.erf(mu / (s * 2 ** 0.5)))


H1 = [
    ('u^3', 'smooth', lambda u: _d(u[0]) ** 3, 0.25),
    ('exp(-2u)', 'smooth', lambda u: np.exp(-2 * _d(u[0])), (1 - math.exp(-2)) / 2),
    ('|2u-1|', 'smooth', lambda u: np.abs(2 * _d(u[0]) - 1), 0.5),
    ('0.5+0.5sin(4 pi u + 1)', 'smooth', lambda u: 0.5 + 0.5 * np.sin(2 * TAU * _d(u[0]) + 1), 0.5),
] + [(f'u<{t:.4f}', 'step', (lambda t: lambda u: (u[0] < t).astype(np.float64))(t), float(t)) for t in np.sort(rng.uniform(0.03, 0.97, 7))] \
  + [box([0]) for _ in range(4)]

H2 = [
    ('(u^2+v)/2', 'smooth', lambda u: (_d(u[0]) ** 2 + _d(u[1])) / 2, (1 / 3 + 0.5) / 2),
    ('0.5+0.5cos(2pi(2u+v))', 'smooth', lambda u: 0.5 + 0.5 * np.cos(TAU * (2 * _d(u[0]) + _d(u[1]))), 0.5),
    ('0.5+0.5cos(2pi(u-3v))', 'smooth', lambda u: 0.5 + 0.5 * np.cos(TAU * (_d(u[0]) - 3 * _d(u[1]))), 0.5),
    ('gaussian (0.3,0.7) s=0.15', 'smooth', lambda u: np.exp(-((_d(u[0]) - .3) ** 2 + (_d(u[1]) - .7) ** 2) / (2 * 0.15 ** 2)), _gauss1(0.3, 0.15) * _gauss1(0.7, 0.15)),
    ('disc (0.35,0.6) r=0.25', 'edge', lambda u: ((_d(u[0]) - .35) ** 2 + (_d(u[1]) - .6) ** 2 < 0.0625).astype(np.float64), math.pi * 0.0625),
    ('GGX a=0.5 lobe (h.l)^4', 'lobe', lambda u: ggx05(u[0], u[1]), _T['ggx05']),
    ('GGX a=0.15 light hit', 'lobe', lambda u: ggx015_hit(u[0], u[1]), _T['ggx015_hit']),
    ('Phong n=20 lobe', 'lobe', lambda u: phong(u[0], u[1]), _T['phong']),
    ('AO horizon 0.5+0.2cos(4 pi u)', 'lobe', lambda u: ao2(u[0], u[1]), _T['ao2']),
] + [halfspace([0, 1], 2) for _ in range(6)] + [box([0, 1]) for _ in range(4)]

H4 = [
    ('prod(0.5+u_i)', 'smooth', lambda u: np.prod([0.5 + _d(u[i]) for i in range(4)], 0), 1.0),
    ('0.5+0.5cos(2pi(u1-u2+u3-u4))', 'smooth', lambda u: 0.5 + 0.5 * np.cos(TAU * (_d(u[0]) - _d(u[1]) + _d(u[2]) - _d(u[3]))), 0.5),
    ('exp(-sum u_i)', 'smooth', lambda u: np.exp(-sum(_d(u[i]) for i in range(4))), (1 - math.exp(-1)) ** 4),
    ('GGX05(u1,u2)*Phong(u3,u4)', 'lobe', lambda u: ggx05(u[0], u[1]) * phong(u[2], u[3]), _T['ggx05'] * _T['phong']),
    ('AO2(u1,u3)*GGX015hit(u2,u4)', 'lobe', lambda u: ao2(u[0], u[2]) * ggx015_hit(u[1], u[3]), _T['ao2'] * _T['ggx015_hit']),
    ('Phong(u1,u4)*[u2<0.6]*(0.5+u3)', 'lobe', lambda u: phong(u[0], u[3]) * (u[1] < 0.6) * (0.5 + _d(u[2])), _T['phong'] * 0.6),
] + [halfspace([0, 1, 2, 3], 4) for _ in range(6)] + [box([0, 1, 2, 3]) for _ in range(4)] + [halfspace(list(p), 4) for p in PAIRS] + [box(list(p)) for p in PAIRS]

HELD = {1: H1, 2: H2, 4: H4}

if __name__ == '__main__':
    r = np.random.default_rng(0)
    for D, lst in HELD.items():
        u = r.random((D, 4_000_000)).astype(np.float32)
        for name, group, f, truth in lst:
            m = f(u).mean()
            assert abs(m - truth) < 1.5e-3, (name, m, truth)
            print(D, group, name, round(truth, 6))
    print('held-out integrands ok:', {D: len(l) for D, l in HELD.items()})
