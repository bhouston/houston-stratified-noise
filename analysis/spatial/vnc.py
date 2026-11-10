"""Void-and-cluster dither array (Ulichney 1993): toroidal Gaussian sigma 1.5, 10% initial minority pixels."""
from pathlib import Path

import numpy as np

CACHE = Path(__file__).parent / 'cache'  # gitignored; delete to regenerate


def void_and_cluster(n, seed, sigma=1.5):
    rng = np.random.default_rng(seed)
    d = np.minimum(np.arange(n), n - np.arange(n))
    g = np.exp(-d ** 2 / (2 * sigma ** 2))
    k2 = np.tile(np.outer(g, g), (2, 2))  # k2[n-y:2n-y, n-x:2n-x] is the kernel centred on (y, x)
    bp = np.zeros((n, n), bool)
    bp.flat[rng.choice(n * n, n * n // 10, replace=False)] = True
    energy = np.zeros((n, n))
    for y, x in zip(*np.nonzero(bp)):
        energy += k2[n - y:2 * n - y, n - x:2 * n - x]

    def flip(i, on):
        y, x = divmod(i, n)
        bp[y, x] = on
        k = k2[n - y:2 * n - y, n - x:2 * n - x]
        np.add(energy, k, out=energy) if on else np.subtract(energy, k, out=energy)

    cluster = lambda: int(np.argmax(np.where(bp, energy, -np.inf)))
    void = lambda: int(np.argmin(np.where(bp, np.inf, energy)))

    while True:  # phase 0: relax the initial pattern
        c = cluster(); flip(c, False)
        v = void(); flip(v, True)
        if v == c:
            break
    rank = np.zeros(n * n, int)
    ones = int(bp.sum())
    proto, proto_energy = bp.copy(), energy.copy()
    for r in range(ones - 1, -1, -1):  # phase 1: rank the initial pixels by removing tightest clusters
        c = cluster(); rank[c] = r; flip(c, False)
    bp[:], energy[:] = proto, proto_energy
    # phases 2+3: fill largest voids. Past 50% Ulichney removes the tightest cluster of zeros, which is
    # the same pixel: zeros-energy = const - ones-energy.
    for r in range(ones, n * n):
        v = void(); rank[v] = r; flip(v, True)
    return ((rank + 0.5) / (n * n)).reshape(n, n)


def cached(n, seed):
    CACHE.mkdir(exist_ok=True)
    f = CACHE / f'vnc_{n}_{seed}.npy'
    if not f.exists():
        np.save(f, void_and_cluster(n, seed))
    return np.load(f)


if __name__ == '__main__':
    t = void_and_cluster(32, 1)
    assert sorted((t * 1024 - 0.5).round().astype(int).ravel()) == list(range(1024))
    p = np.abs(np.fft.fft2(t - t.mean())) ** 2
    r = np.hypot(*np.meshgrid(np.fft.fftfreq(32), np.fft.fftfreq(32)))
    assert p[(r > 0) & (r < 0.1)].mean() < 0.1 * p[r > 0.3].mean(), 'not blue'
    print('void-and-cluster self-check passed')
