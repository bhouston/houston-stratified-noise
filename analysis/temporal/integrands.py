"""Test integrands on [0,1)^D with known means.  Each entry: (name, group, fn(u) -> float array, truth); u has shape (D, ...)."""
import math
import numpy as np

TAU = 2 * math.pi

# ---------------------------------------------------------------- 1D
THRESHOLDS = [0.1, 0.25, 1 / math.pi, 0.5, 1 / math.sqrt(2), 0.75, 0.9]

INT1 = [
    ('u', 'smooth', lambda u: u[0].astype(np.float64), 0.5),
    ('u^2', 'smooth', lambda u: u[0].astype(np.float64) ** 2, 1 / 3),
    ('0.5+0.5cos(2 pi u)', 'smooth', lambda u: 0.5 + 0.5 * np.cos(TAU * u[0].astype(np.float64)), 0.5),
] + [(f'u<{t:.4f}', 'step', (lambda t: lambda u: (u[0] < t).astype(np.float64))(t), t) for t in THRESHOLDS]


# ---------------------------------------------------------------- 2D
def _ggx_h(u, v, alpha=0.3):
    """GGX half-vector for roughness alpha, phi = 2 pi u, cos^2(theta) = (1 - v) / (1 + (alpha^2 - 1) v)."""
    u = u.astype(np.float64); v = v.astype(np.float64)
    c2 = (1 - v) / (1 + (alpha * alpha - 1) * v)
    s = np.sqrt(np.maximum(0, 1 - c2))
    return s * np.cos(TAU * u), s * np.sin(TAU * u), np.sqrt(c2)


_L = np.array([0.3, 0.2, 1.0]) / np.linalg.norm([0.3, 0.2, 1.0])


def _ggx_dot(u, v):
    hx, hy, hz = _ggx_h(u, v)
    return hx * _L[0] + hy * _L[1] + hz * _L[2]


def f_ggx_smooth(u, v):
    return np.maximum(0, _ggx_dot(u, v)) ** 8


def f_ggx_light(u, v):
    return (_ggx_dot(u, v) > 0.97).astype(np.float64)


def f_ao(u, v):
    """Cosine-weighted hemisphere direction (phi = 2 pi u, cos(theta) = sqrt(1 - v)), visible above a sinusoidal horizon."""
    u = u.astype(np.float64); v = v.astype(np.float64)
    return (np.sqrt(1 - v) > 0.3 + 0.25 * np.sin(TAU * u)).astype(np.float64)


def _quad(f, n=4096):
    g = (np.arange(n) + 0.5) / n
    return float(np.mean([f(np.full(n, a), g).mean() for a in g]))


def _gauss_truth(s=0.2):
    return (math.sqrt(TAU) * s * math.erf(0.5 / (s * math.sqrt(2)))) ** 2


def _d(a):
    return a.astype(np.float64)


INT2 = [
    ('u*v', 'smooth', lambda u: _d(u[0]) * _d(u[1]), 0.25),
    ('0.5+0.5cos(2pi(u-v))', 'smooth', lambda u: 0.5 + 0.5 * np.cos(TAU * (_d(u[0]) - _d(u[1]))), 0.5),
    ('0.5+0.5cos(2pi(u+v))', 'smooth', lambda u: 0.5 + 0.5 * np.cos(TAU * (_d(u[0]) + _d(u[1]))), 0.5),
    ('gaussian bump s=0.2', 'smooth', lambda u: np.exp(-((_d(u[0]) - .5) ** 2 + (_d(u[1]) - .5) ** 2) / (2 * 0.2 ** 2)), _gauss_truth()),
    ('disc r=0.4', 'edge', lambda u: ((_d(u[0]) - .5) ** 2 + (_d(u[1]) - .5) ** 2 < 0.16).astype(np.float64), math.pi * 0.16),
    ('quarter disc', 'edge', lambda u: (_d(u[0]) ** 2 + _d(u[1]) ** 2 < 1).astype(np.float64), math.pi / 4),
    ('u+v<1 (anti-diagonal)', 'edge', lambda u: (_d(u[0]) + _d(u[1]) < 1).astype(np.float64), 0.5),
    ('u<v (diagonal)', 'edge', lambda u: (u[0] < u[1]).astype(np.float64), 0.5),
    ('u+v<0.7', 'edge', lambda u: (_d(u[0]) + _d(u[1]) < 0.7).astype(np.float64), 0.245),
    ('box u<0.3,v<0.6', 'edge', lambda u: ((u[0] < 0.3) & (u[1] < 0.6)).astype(np.float64), 0.18),
    ('oblique 0.37u+0.81v<0.5', 'edge', lambda u: (0.37 * _d(u[0]) + 0.81 * _d(u[1]) < 0.5).astype(np.float64), (0.5 - 0.185) / 0.81),
    ('AO cosine hemisphere', 'render', lambda u: f_ao(u[0], u[1]), 1 - (0.09 + 0.0625 / 2)),
    ('GGX lobe, (h.l)^8', 'render', lambda u: f_ggx_smooth(u[0], u[1]), None),
    ('GGX lobe, light hit h.l>0.97', 'render', lambda u: f_ggx_light(u[0], u[1]), None),
]
_T_GGX_S = _quad(f_ggx_smooth)
_T_GGX_L = _quad(f_ggx_light)
INT2[12] = INT2[12][:3] + (_T_GGX_S,)
INT2[13] = INT2[13][:3] + (_T_GGX_L,)
_T_AO = INT2[11][3]

# ---------------------------------------------------------------- 4D
PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
INT4 = [
    ('mean(u_i)', 'joint', lambda u: sum(_d(u[i]) for i in range(4)) / 4, 0.5),
    ('u1 u2 u3 u4', 'joint', lambda u: _d(u[0]) * _d(u[1]) * _d(u[2]) * _d(u[3]), 1 / 16),
    ('sum(u_i)<2', 'joint', lambda u: (sum(_d(u[i]) for i in range(4)) < 2).astype(np.float64), 0.5),
    ('4-ball r=0.5', 'joint', lambda u: (sum((_d(u[i]) - .5) ** 2 for i in range(4)) < 0.25).astype(np.float64), math.pi ** 2 / 32),
    ('[u1<u3][u2<u4]', 'joint', lambda u: ((u[0] < u[2]) & (u[1] < u[3])).astype(np.float64), 0.25),
    ('SSR-like: GGX(u1,u2)[u3<0.4](0.5+u4)', 'joint', lambda u: f_ggx_smooth(u[0], u[1]) * (u[2] < 0.4) * (0.5 + _d(u[3])), _T_GGX_S * 0.4),
    ('AO(u1,u2)*AO(u3,u4)', 'joint', lambda u: f_ao(u[0], u[1]) * f_ao(u[2], u[3]), _T_AO ** 2),
] + [(f'u{i + 1}<u{j + 1}', 'pair', (lambda i, j: lambda u: (u[i] < u[j]).astype(np.float64))(i, j), 0.5) for i, j in PAIRS] \
  + [(f'u{i + 1}+u{j + 1}<1', 'pair', (lambda i, j: lambda u: (_d(u[i]) + _d(u[j]) < 1).astype(np.float64))(i, j), 0.5) for i, j in PAIRS]

INTS = {1: INT1, 2: INT2, 4: INT4}

if __name__ == '__main__':
    rng = np.random.default_rng(0)
    for D, lst in INTS.items():
        u = rng.random((D, 2_000_000)).astype(np.float32)
        for name, group, f, truth in lst:
            m = f(u).mean()
            assert abs(m - truth) < 2e-3, (name, m, truth)  # Monte Carlo check of every stated truth
            print(D, group, name, round(truth, 6))
    print('integrands ok')
