"""One bounded search for better temporal step constants.  `pnpm analysis:steps` runs the stages in order, then report.py:

    search.py cands      analytic candidate generation -> results/steps/cands.json
    search.py select     harness metrics on the SELECTION integrands (../temporal/integrands.py) -> select.json, picks one set per D
    search.py validate   picked sets vs current constants on the HELD-OUT integrands (heldout.py), 5 seeds/regions -> validate.json

Uses the temporal analysis harness (analysis/temporal).

Selection rule, fixed before any harness number was seen (HSN phase, selection integrands, seeds 1..D, region at 0):
    metrics  = per-pixel N in PP_N (7) + {4, 8, 16-frame box, EMA 0.1} x {3x3 box, Gauss 1, Gauss 2} (12)
    ratio    = candidate / current constants, per metric;  J = geometric mean of the 19 ratios
    eligible = max ratio <= 1.03 and (D >= 2) every pairwise temporal chi2/dof <= 1.0
    pick     = eligible candidate with the lowest J; if none is eligible, the lowest J among chi2-ok candidates (flagged)
"""
import itertools, json, math, os, sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../temporal'))
OUT = os.path.join(HERE, '../../results/steps')
U = np.uint32
GOLDEN = 2654435769
R2 = [3242174889, 2447445413]
R4 = [3679390609, 3152041523, 2700274805, 2313257605]
BASE = {1: [GOLDEN], 2: R2, 4: R4}
PP_N = [4, 8, 16, 32, 64, 256, 1024]
NS_A = sorted(set(int(round(v)) for v in np.geomspace(4, 1024, 40)))  # log-spaced, not only powers of two
FILTERS = ('box3', 'gauss1', 'gauss2')
OBJ = [f'pp/{n}' for n in PP_N] + [f'{w}/{fl}' for w in ('box4', 'box8', 'box16', 'ema') for fl in FILTERS]
HELD_CONFIGS = [(17, 5003, 911), (101, 20011, 40009), (5, 777, 1234), (40, 123457, 3331), (9, 31, 65000)]  # (seed base, x0, y0)


def to_step(a):
    return (int((a % 1.0) * 2 ** 32) | 1) & 0xffffffff


# ================================================================ analytic criteria

def dist(v):
    """|v/2^32 - nearest integer| for uint64 residues v mod 2^32."""
    v = v & np.uint64(0xffffffff)
    return np.minimum(v, np.uint64(2 ** 32) - v).astype(np.float64) / 2 ** 32


def crit_a(step, qmax=1000):
    """min over q <= qmax of q * ||q a||  (golden: 0.38; 1/sqrt(5) = 0.447 is the asymptotic optimum) and the q."""
    q = np.arange(1, qmax + 1, dtype=np.uint64)
    v = q * dist(q * np.uint64(step))
    return float(v.min()), int(q[v.argmin()])


def crit_c(step):
    """Base-4 hierarchy resonance: min over q = 4m (m <= 16) of q * ||q a||, and raw ||q a|| for q = 4, 8, 16, 64."""
    q = np.arange(4, 65, 4, dtype=np.uint64)
    return float((q * dist(q * np.uint64(step))).min()), [float(dist(np.uint64(k) * np.uint64(step))) for k in (4, 8, 16, 64)]


def crit_b(steps, kmax=8):
    """Integer relations: min ||k.a|| over 0 != k in [-kmax, kmax]^D (raw, with k) and min ||k.a|| * prod max(1, |k_i|)."""
    D = len(steps)
    k = np.stack(np.meshgrid(*[np.arange(-kmax, kmax + 1)] * D, indexing='ij'), -1).reshape(-1, D)
    k = k[np.any(k != 0, 1)]
    d = dist((k.astype(np.int64) * np.array(steps, np.int64)).sum(1).astype(np.uint64))
    w = d * np.prod(np.maximum(1, np.abs(k)), 1)
    return [float(d.min()), k[d.argmin()].tolist(), float(w.min()), k[w.argmin()].tolist()]


def wd_factors(steps_arr, T=1024):
    """steps_arr (C, D) uint -> per-dimension kernel factor (C, D, T-1) = 3/2 - t(1-t), t = frac(m a_d), m = 1..T-1."""
    m = np.arange(1, T, dtype=np.uint64)
    t = ((np.asarray(steps_arr, np.uint64)[..., None] * m) & np.uint64(0xffffffff)).astype(np.float64) / 2 ** 32
    return 1.5 - t * (1 - t)


def wd(K, d, NS=NS_A):
    """Wrap-around L2 discrepancy of the first N Kronecker points (= shift-averaged, so it is what a pixel with a
    random phase sees).  K (..., T-1) is the product kernel over the d chosen dimensions.  Returns (..., len(NS))."""
    m = np.arange(1, K.shape[-1] + 1)
    S1 = np.concatenate([np.zeros(K.shape[:-1] + (1,)), np.cumsum(K, -1)], -1)       # sum_{m<N} K
    S2 = np.concatenate([np.zeros(K.shape[:-1] + (1,)), np.cumsum(K * m, -1)], -1)   # sum_{m<N} m K
    out = []
    for n in NS:
        v = -(4 / 3) ** d + 1.5 ** d / n + 2 / n ** 2 * (n * S1[..., n - 1] - S2[..., n - 1])
        out.append(np.sqrt(np.maximum(v, 0)))
    return np.stack(out, -1)


def gm(a, axis=-1):
    return np.exp(np.mean(np.log(a), axis))


_REF = {}


def refs():
    if not _REF:
        _REF[1] = wd(wd_factors([[GOLDEN]])[0, 0], 1)
        _REF[2] = wd(np.prod(wd_factors([R2])[0], 0), 2)
        _REF[4] = wd(np.prod(wd_factors([R4])[0], 0), 4)
    return _REF


def analytic_score(steps_arr):
    """(C, D) -> dict of arrays: g_full (vs current D-dim constants), g1 (worst component vs golden), g2 (worst pair vs R2), score."""
    steps_arr = np.asarray(steps_arr, np.uint64)
    C, D = steps_arr.shape
    R = refs()
    out = {k: [] for k in ('g_full', 'g1', 'g2', 'score')}
    for c0 in range(0, C, 2000):
        F = wd_factors(steps_arr[c0:c0 + 2000])
        g1 = np.max([gm(wd(F[:, d], 1) / R[1]) for d in range(D)], 0)
        g_full = gm(wd(np.prod(F, 1), D) / R[D])
        g2 = np.max([gm(wd(F[:, i] * F[:, j], 2) / R[2]) for i, j in itertools.combinations(range(D), 2)], 0) if D > 1 else np.ones(len(F))
        score = g1 if D == 1 else g_full * np.sqrt(g1) * (np.sqrt(g2) if D == 4 else 1)
        for k, v in zip(out, (g_full, g1, g2, score)):
            out[k].append(v)
    return {k: np.concatenate(v) for k, v in out.items()}


# ================================================================ candidate constructions

PHI = (1 + 5 ** 0.5) / 2


def proot(coeffs):
    """Largest real root of a polynomial (highest power first)."""
    r = np.roots(coeffs)
    return float(max(x.real for x in r if abs(x.imag) < 1e-9))


def number_pool():
    """Badly approximable 1D numbers: noble numbers [0; a1, a2, 1, 1, ...], metallic means, sqrt of primes, cubic Pisot inverses."""
    P = {}
    seen = []
    for cf in [(1, 1), (1, 2), (1, 3), (2, 2), (2, 3), (3, 2), (3, 3), (4, 2), (4, 3), (1, 1, 2), (2, 1, 2), (1, 2, 2), (1, 1, 3)]:
        v = 1 / PHI
        for a in reversed(cf):
            v = 1 / (a + v)
        if not any(abs(v - w) < 1e-9 or abs(v + w - 1) < 1e-9 for w in seen):
            seen.append(v)
            P[f'noble[0;{",".join(map(str, cf))},1...]'] = v
    P['silver sqrt2-1'] = 2 ** 0.5 - 1
    P['bronze (sqrt13-3)/2'] = (13 ** 0.5 - 3) / 2
    for p in (3, 7, 11, 13, 17, 19, 23):
        P[f'frac sqrt{p}'] = p ** 0.5 % 1
    rho, psi, tri = proot([1, 0, -1, -1]), proot([1, -1, 0, -1]), proot([1, -1, -1, -1])
    P['1/plastic'] = 1 / rho; P['1/plastic^2'] = 1 / rho ** 2
    P['1/supergolden'] = 1 / psi; P['1/supergolden^2'] = 1 / psi ** 2
    P['1/tribonacci'] = 1 / tri; P['1/tribonacci^2'] = 1 / tri ** 2
    return P


def field(name):
    """Two numbers of one quadratic field are rationally dependent with 1 (the pair is not equidistributed), so a set
    may hold one number per quadratic field and two per cubic field."""
    if name.startswith('noble'):
        return 'q5', 1
    if name.startswith('silver'):
        return 'q2', 1
    if 'sqrt13' in name:
        return 'q13', 1
    if name.startswith('frac sqrt'):
        return 'q' + name[9:], 1
    return name.split('/')[1].split('^')[0], 2


def independent(names):
    cnt = {}
    for n in names:
        f, lim = field(n)
        cnt[f] = cnt.get(f, 0) + 1
        if cnt[f] > lim:
            return False
    return True


FIELDS = {  # name: (polynomial, degree)
    'plastic x^3=x+1': [1, 0, -1, -1], 'supergolden x^3=x^2+1': [1, -1, 0, -1], 'tribonacci': [1, -1, -1, -1],
    '2cos(2pi/7) x^3+x^2-2x-1': [1, 1, -2, -1], '2cos(2pi/9) x^3-3x+1': [1, 0, -3, 1],
    'R3 x^4=x+1': [1, 0, 0, -1, -1], 'x^4=x^3+1': [1, -1, 0, 0, -1], 'tetranacci': [1, -1, -1, -1, -1],
    'R4 x^5=x+1': [1, 0, 0, 0, -1, -1], 'pentanacci': [1, -1, -1, -1, -1, -1], 'x^5=x^3+x^2+x+1': [1, 0, -1, -1, -1, -1],
    'x^5=x^4+x^2+1': [1, -1, 0, -1, 0, -1], 'x^5=x^4+x^3+1': [1, -1, -1, 0, 0, -1], '2cos(2pi/11) quintic': [1, 1, -4, -3, 3, 1],
    'R5 x^6=x+1': [1, 0, 0, 0, 0, -1, -1], 'R6 x^7=x+1': [1, 0, 0, 0, 0, 0, -1, -1], 'R7 x^8=x+1': [1, 0, 0, 0, 0, 0, 0, -1, -1],
}
KOROBOV = [2891336453, 29943829, 32310901, 1664525, 747796405, 22695477]  # LCG multipliers mod 2^32 with good spectral tests


def constructions(D):
    """{name: [uint32 steps]} for D dimensions."""
    C = {}
    pool = number_pool()
    if D == 1:
        return {k: [to_step(v)] for k, v in pool.items()} | {f'R4_STEPS[{i}]': [s] for i, s in enumerate(R4)}
    for name, poly in FIELDS.items():
        deg = len(poly) - 1
        if deg - 1 < D:
            continue
        a = proot(poly)
        inv = [to_step(a ** -k) for k in range(1, deg)]
        pw = [to_step(a ** k) for k in range(1, deg)]
        for sub in itertools.combinations(range(deg - 1), D):
            if deg - 1 > 4 and sub not in (tuple(range(D)), tuple(range(1, D + 1)), tuple(range(deg - 1 - D, deg - 1))):
                continue
            C[f'{name}: a^-k k={[i + 1 for i in sub]}'] = [inv[i] for i in sub]
            C[f'{name}: frac a^k k={[i + 1 for i in sub]}'] = [pw[i] for i in sub]
    for g in KOROBOV:  # Korobov lattice (1, g, g^2, ..) mod 2^32 put in Kronecker order by multiplying with the golden step
        C[f'Korobov g={g} x golden'] = [(GOLDEN * pow(g, k, 2 ** 32)) % 2 ** 32 for k in range(D)]
    primes = (2, 3, 5, 7, 11, 13)
    for sub in itertools.combinations(primes, D):
        if D == 2 or sub in ((2, 3, 5, 7), (3, 5, 7, 11), (2, 3, 7, 11), (5, 7, 11, 13)):
            C[f'frac sqrt{list(sub)}'] = [to_step(p ** 0.5) for p in sub]
    names = list(pool)
    for sub in itertools.combinations(range(len(names)), D):  # every rationally independent D-subset of the 1D pool (mixed fields)
        if not independent([names[i] for i in sub]):
            continue
        C['pool: ' + ' | '.join(names[i] for i in sub)] = [to_step(pool[names[i]]) for i in sub]
    return C


def stage_cands():
    rng = np.random.default_rng(35429)
    res = {}
    for D in (1, 2, 4):
        C = constructions(D)
        C = {k: v for k, v in C.items() if len(set(v)) == D}
        names = list(C)
        sc = analytic_score([C[k] for k in names])
        order = np.argsort(sc['score'])
        keep, used = [], {}
        n_con = {1: 30, 2: 18, 4: 18}[D]
        for i in order:  # diversity: a pool number may appear in at most 3 kept sets
            st = C[names[i]]
            if names[i].startswith('pool') and D > 1 and any(used.get(s, 0) >= 3 for s in st):
                continue
            for s in st:
                used[s] = used.get(s, 0) + 1
            keep.append((names[i], st, 'construction'))
            if len(keep) >= n_con:
                break
        # named references that are always evaluated
        always = {1: ['R4_STEPS[0]', 'R4_STEPS[3]', '1/plastic', '1/plastic^2'],
                  2: ['R4 x^5=x+1: a^-k k=[1, 2]', 'R4 x^5=x+1: a^-k k=[1, 4]', 'R3 x^4=x+1: a^-k k=[1, 2]', 'frac sqrt[2, 3]', f'Korobov g={KOROBOV[0]} x golden',
                      '2cos(2pi/7) x^3+x^2-2x-1: frac a^k k=[1, 2]', 'pool: noble[0;1,1,1...] | silver sqrt2-1', 'pool: 1/plastic | 1/plastic^2'],
                  4: ['frac sqrt[2, 3, 5, 7]', 'R5 x^6=x+1: a^-k k=[1, 2, 3, 4]', 'R6 x^7=x+1: a^-k k=[1, 2, 3, 4]', '2cos(2pi/11) quintic: frac a^k k=[1, 2, 3, 4]',
                      f'Korobov g={KOROBOV[0]} x golden', 'pentanacci: a^-k k=[1, 2, 3, 4]']}[D]
        for nm in always:
            if nm in C and nm not in [k[0] for k in keep]:
                keep.append((nm, C[nm], 'reference'))
        if D > 1:  # modest random search: odd uint32 vectors, ranked by the same analytic score, hard filter on criterion (a)
            one = (rng.integers(0, 2 ** 31, 200000, dtype=np.uint64) << np.uint64(1)) | np.uint64(1)
            q = np.arange(1, 1001, dtype=np.uint64)
            good = np.concatenate([o[(q * dist(o[:, None] * q)).min(1) >= 0.2] for o in np.array_split(one, 100)])
            print(f'random search: {len(good)} of {len(one)} odd uint32 pass criterion (a) >= 0.2')
            R = good[rng.integers(0, len(good), (40000, D))]
            rs = analytic_score(R)
            n = 0
            for i in np.argsort(rs['score'])[:3000]:
                st = [int(v) for v in R[i]]
                if len(set(st)) < D:
                    continue
                keep.append((f'random #{i}', st, 'random'))
                n += 1
                if n >= 10:
                    break
        keep.insert(0, ('CURRENT ' + {1: 'golden', 2: 'R2_STEPS', 4: 'R4_STEPS'}[D], BASE[D], 'current'))
        out = []
        sc2 = analytic_score([k[1] for k in keep])
        for j, (nm, st, src) in enumerate(keep):
            a = [crit_a(s) for s in st]
            c = [crit_c(s) for s in st]
            b = crit_b(st) if D > 1 else (None, None, None, None)
            pr = min((crit_b([st[i], st[j]], 64)[2:] + [f'{i + 1}-{j + 1}'] for i, j in itertools.combinations(range(D), 2)), key=lambda t: t[0]) if D > 1 else None
            out.append(dict(name=nm, steps=[int(s) for s in st], source=src, floats=[s / 2 ** 32 for s in st],
                            a_min=min(v[0] for v in a), a=[list(v) for v in a], c_min=min(v[0] for v in c), c_raw=[v[1] for v in c],
                            b_raw=b[0], b_k=b[1], b_norm=b[2], b_norm_k=b[3], pair64=pr,
                            **{k: float(v[j]) for k, v in sc2.items()}))
        res[D] = dict(n_constructions=len(C), cands=out)
        print(f'\n== D={D}: {len(C)} constructions scored analytically, {len(out)} kept')
        for o in out:
            print(f"{o['score']:.3f} g_full={o['g_full']:.3f} g1={o['g1']:.3f} g2={o['g2']:.3f} a={o['a_min']:.3f} c={o['c_min']:.3f} b_norm={o['b_norm'] if o['b_norm'] is None else round(o['b_norm'], 4)} pair64={o['pair64'] and (round(o['pair64'][0], 4), o['pair64'][1])} [{o['source']}] {o['name']} {o['steps']}")
    json.dump(res, open(os.path.join(OUT, 'cands.json'), 'w'), indent=1)


# ================================================================ harness metrics (same protocol as analysis-temporal run_all.py / extras.py)

def sampler(steps, phase, seed_base):
    import noises as N
    def fn(x, y, n):
        if phase == 'hsn':
            return np.stack([N.hsn1(x, y, n, seed_base * 4 + k + 1, s) for k, s in enumerate(steps)])
        xu, yu, nu = N._u(x), N._u(y), N._u(n)
        out = [N.pcg(xu ^ N.pcg(yu ^ N.pcg(np.array(d + 7001 + 97 * seed_base, np.uint32)))) + nu * U(s) for d, s in enumerate(steps)]
        return np.stack([(v >> U(8)).astype(np.float32) / np.float32(16777216) for v in np.broadcast_arrays(*out)])
    return fn


def evaluate(task):
    key, steps, phase, setname, seed_base, x0, y0 = task
    from scipy import signal
    from run_all import spatial, rms, chi2_pair, BOX_STARTS, W, PAD, T_EMA, T0
    from integrands import INTS
    from heldout import HELD
    D = len(steps)
    ints = (INTS if setname == 'sel' else HELD)[D]
    fn = sampler(steps, phase, seed_base)
    out = {}
    # per pixel, no spatial filter: 64x64 pixels, 1024 frames
    y, x = np.mgrid[0:64, 0:64]
    s = fn(x[None] + x0, y[None] + y0, np.arange(1024, dtype=np.int64)[:, None, None]).reshape(D, 1024, -1)
    sq = 0
    for name, grp, f, truth in ints:
        v = f(s)
        sq = sq + np.mean((np.cumsum(v, 0) / np.arange(1, 1025)[:, None] - truth) ** 2, 1)
    curve = np.sqrt(sq / len(ints))
    for n in PP_N:
        out[f'pp/{n}'] = float(curve[n - 1])
    out['pp_all'] = [float(curve[n - 1]) for n in NS_A]
    if D > 1:
        out['chi'] = {f'{i + 1}-{j + 1}': chi2_pair(s[i], s[j], 8) for i, j in itertools.combinations(range(D), 2)}
    # short histories with a spatial filter: 128x128 inside 144x144, EMA measured over frames 128..255
    y, x = np.mgrid[0:W + 2 * PAD, 0:W + 2 * PAD]
    s = fn(x[None] + x0, y[None] + y0, np.arange(T_EMA, dtype=np.int64)[:, None, None])
    acc = {}
    for name, grp, f, truth in ints:
        v = (f(s) - truth).astype(np.float32)
        e = signal.lfilter([0.1], [1, -0.9], v, axis=0, zi=(0.9 * v[:1]))[0][T0:].astype(np.float32)
        for fl in FILTERS:
            acc.setdefault(f'ema/{fl}', []).append(float(rms(spatial(e, fl))))
            for c in (1, 4, 8, 16):
                acc.setdefault(f'box{c}/{fl}', []).append(float(rms(spatial(np.stack([v[st:st + c].mean(0) for st in BOX_STARTS]), fl))))
    for k, v in acc.items():
        out[k] = float(np.sqrt(np.mean(np.square(v))))
    return key, out


def run(tasks):
    with Pool(6) as pool:
        res = {}
        for i, (key, out) in enumerate(pool.imap_unordered(evaluate, tasks)):
            res[key] = out
            print(f'  {i + 1}/{len(tasks)} {key}', flush=True)
    return res


def stage_select():
    cands = json.load(open(os.path.join(OUT, 'cands.json')))
    tasks = [(f'{D}|{c["name"]}|{ph}', c['steps'], ph, 'sel', 0, 0, 0) for D in ('4', '2', '1') for c in cands[D]['cands'] for ph in ('hsn', 'hash')]
    res = run(tasks)
    picks = {}
    for D in ('1', '2', '4'):
        base = res[f'{D}|{cands[D]["cands"][0]["name"]}|hsn']
        rows = []
        for c in cands[D]['cands'][1:]:
            r = res[f'{D}|{c["name"]}|hsn']
            ratios = {m: r[m] / base[m] for m in OBJ}
            chi = max(r['chi'].values()) if 'chi' in r else 0.0
            rows.append(dict(name=c['name'], steps=c['steps'], J=float(gm(np.array(list(ratios.values())))), max_ratio=max(ratios.values()),
                             worst=max(ratios, key=ratios.get), chi_max=chi, eligible=bool(max(ratios.values()) <= 1.03 and chi <= 1.0)))
        rows.sort(key=lambda r: r['J'])
        elig = [r for r in rows if r['eligible']]
        pick = elig[0] if elig else [r for r in rows if r['chi_max'] <= 1.0][0]
        picks[D] = dict(pick=pick, any_eligible=bool(elig), ranking=rows)
        print(f'\n== D={D}  eligible: {len(elig)}/{len(rows)}   pick: {pick["name"]} {pick["steps"]} J={pick["J"]:.3f} max={pick["max_ratio"]:.3f}')
        for r in rows:
            print(f"  J={r['J']:.3f} max={r['max_ratio']:.3f} ({r['worst']}) chi={r['chi_max']:.2f} {'ELIG' if r['eligible'] else '    '} {r['name']}")
    json.dump(dict(metrics=res, picks=picks), open(os.path.join(OUT, 'select.json'), 'w'), indent=1)


def stage_validate():
    sel = json.load(open(os.path.join(OUT, 'select.json')))
    tasks = []
    for D in ('1', '2', '4'):
        new = sel['picks'][D]['pick']['steps']
        for label, st in (('old', BASE[int(D)]), ('new', new)):
            for ph in ('hsn', 'hash'):
                for ci, (sb, x0, y0) in enumerate(HELD_CONFIGS):
                    tasks.append((f'{D}|{label}|{ph}|{ci}', st, ph, 'held', sb, x0, y0))
    # supplementary, fixed in advance: the first two steps of the 4D sets used as a 2D pair (the PR's VXGI does this)
    new4 = sel['picks']['4']['pick']['steps']
    for label, st in (('old4xy', R4[:2]), ('new4xy', new4[:2])):
        for ci, (sb, x0, y0) in enumerate(HELD_CONFIGS):
            tasks.append((f'2|{label}|hsn|{ci}', st, 'hsn', 'held', sb, x0, y0))
    json.dump(run(tasks), open(os.path.join(OUT, 'validate.json'), 'w'), indent=1)


def demo():
    assert to_step(1 / PHI) == GOLDEN
    assert abs(crit_a(GOLDEN)[0] - 0.382) < 0.01 and crit_a(R4[0])[1] == 7 and crit_a(R2[0])[1] == 4
    b = crit_b([R4[0], R4[2]])
    assert b[0] < 3e-4 and sorted(map(abs, b[1])) == [1, 5]        # the five-lines relation a1 + 5 a2
    # wrap-around discrepancy closed form against brute force
    pts = (np.arange(37)[:, None] * np.array(R2) % 2 ** 32) / 2 ** 32
    d = np.abs(pts[:, None] - pts[None]); brute = math.sqrt(-(4 / 3) ** 2 + np.prod(1.5 - d * (1 - d), -1).mean())
    assert abs(wd(np.prod(wd_factors([R2])[0], 0), 2, [37])[0] - brute) < 1e-12
    print('search self-check ok')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    demo()
    {'cands': stage_cands, 'select': stage_select, 'validate': stage_validate, 'demo': lambda: None}[sys.argv[1]]()
