"""Tables (results/steps/tables_steps.md and .json) and the 4D pair scatter figure from results/steps/{cands,select,validate}.json."""
import itertools, json, os
import numpy as np
import search as S
from run_all import md_table, e3, newfig, savefig, save

OUT = S.OUT
cands = json.load(open(os.path.join(OUT, 'cands.json')))
sel = json.load(open(os.path.join(OUT, 'select.json')))
val = json.load(open(os.path.join(OUT, 'validate.json')))
ROWS = [f'pp/{n}' for n in S.PP_N] + [f'{w}/{fl}' for w in ('box1', 'box4', 'box8', 'box16', 'ema') for fl in S.FILTERS]
LABEL = lambda m: m.replace('pp/', 'per pixel N=').replace('box3', '3x3 box').replace('gauss', 'Gauss s=').replace('ema/', 'EMA 0.1 + ').replace('box1/', '1 frame + ').replace('box4/', '4 frames + ').replace('box8/', '8 frames + ').replace('box16/', '16 frames + ')
NC = len(S.HELD_CONFIGS)
t = ''


def held(D, label, ph, m):
    return np.array([val[f'{D}|{label}|{ph}|{c}'][m] for c in range(NC)])


for D in ('1', '2', '4'):
    p = sel['picks'][D]
    c0 = cands[D]['cands'][0]
    cn = next(c for c in cands[D]['cands'] if c['name'] == p['pick']['name'])
    t += f"\n## {D} value(s) per pixel\n\nPick: `{cn['steps']}` = {[round(f, 9) for f in cn['floats']]} ({cn['name']}; source: {cn['source']}). Eligible candidates on the selection set: {sum(r['eligible'] for r in p['ranking'])} of {len(p['ranking'])}. Pick J = {p['pick']['J']:.3f}, worst metric ratio {p['pick']['max_ratio']:.3f} ({p['pick']['worst']}).\n\n"
    t += '**Criteria**\n\n' + md_table(['Set', '(a) min q||qa||, q<=1000', '(c) min q||qa||, q=4m<=64', 'raw ||4a||,||8a||,||16a||,||64a|| (worst component)', '(b) min ||k.a||, |k|<=8 (k)', '(b) normalised', 'pair relation |k|<=64, normalised', 'wrap-around L2 disc. vs current (geo-mean N=4..1024)'],
                                   [[nm, f"{c['a_min']:.3f}", f"{c['c_min']:.3f}", ', '.join(f'{v:.3f}' for v in np.min(c['c_raw'], 0)),
                                     '-' if c['b_raw'] is None else f"{c['b_raw']:.5f} {c['b_k']}", '-' if c['b_norm'] is None else f"{c['b_norm']:.4f}", '-' if not c['pair64'] else f"{c['pair64'][0]:.4f} {c['pair64'][1]} (pair {c['pair64'][2]})", f"{c['g_full']:.3f}"]
                                    for nm, c in (('current', c0), ('new', cn))])
    # selection set
    R = sel['metrics']
    o, oh, n, nh = R[f'{D}|{c0["name"]}|hsn'], R[f'{D}|{c0["name"]}|hash'], R[f'{D}|{cn["name"]}|hsn'], R[f'{D}|{cn["name"]}|hash']
    t += '\n**Selection integrands (RMSE x 1000; seeds 1..D, region at 0)**\n\n'
    t += md_table(['Metric', 'HSN old', 'HSN new', 'new/old', 'hash old', 'hash new', 'new/old', 'HSN/hash old', 'HSN/hash new'],
                  [[LABEL(m), e3(o[m]), e3(n[m]), f'{n[m] / o[m]:.3f}', e3(oh[m]), e3(nh[m]), f'{nh[m] / oh[m]:.3f}', f'{o[m] / oh[m]:.2f}', f'{n[m] / nh[m]:.2f}'] for m in ROWS])
    # held-out
    t += f'\n**Held-out integrands (RMSE x 1000, mean of {NC} seed/region configurations; ratio = mean +- std of the per-configuration ratio; "seed CV" = std/mean of the current constants across configurations)**\n\n'
    rows, rat = [], {}
    for m in ROWS:
        a, b, ah, bh = held(D, 'old', 'hsn', m), held(D, 'new', 'hsn', m), held(D, 'old', 'hash', m), held(D, 'new', 'hash', m)
        rat[m] = ((b / a).mean(), (b / a).std(ddof=1), (bh / ah).mean(), (bh / ah).std(ddof=1))
        rows.append([LABEL(m), e3(a.mean()), e3(b.mean()), f'{rat[m][0]:.3f} +- {rat[m][1]:.3f}', f'{a.std(ddof=1) / a.mean() * 100:.1f}%', e3(ah.mean()), e3(bh.mean()), f'{rat[m][2]:.3f} +- {rat[m][3]:.3f}',
                     f'{(a / ah).mean():.2f}', f'{(b / bh).mean():.2f} +- {(b / bh).std(ddof=1):.2f}'])
    t += md_table(['Metric', 'HSN old', 'HSN new', 'new/old', 'seed CV', 'hash old', 'hash new', 'new/old', 'HSN/hash old', 'HSN/hash new'], rows)
    obj = [m for m in ROWS if not m.startswith('box1/')]
    for nm, idx in (('HSN phase', 0), ('hash phase', 2)):
        g = float(np.exp(np.mean([np.log(rat[m][idx]) for m in obj])))
        w = max(obj, key=lambda m: rat[m][idx]); bst = min(obj, key=lambda m: rat[m][idx])
        t += f'\nHeld-out summary, {nm}: geometric mean new/old over the 19 step-dependent metrics = **{g:.3f}**; worst {rat[w][idx]:.3f} ({LABEL(w)}); best {rat[bst][idx]:.3f} ({LABEL(bst)}); metrics regressing > 3%: {[LABEL(m) for m in obj if rat[m][idx] > 1.03]}; largest ratio std across configurations {max(rat[m][idx + 1] for m in obj):.3f}.\n'
    for grp, ms in (('per pixel', [m for m in obj if m.startswith('pp')]), ('filtered', [m for m in obj if not m.startswith('pp')])):
        t += f"\n- {grp}: HSN phase {np.exp(np.mean([np.log(rat[m][0]) for m in ms])):.3f}, hash phase {np.exp(np.mean([np.log(rat[m][2]) for m in ms])):.3f}"
    # all N, log-spaced (not only powers of two)
    a = np.array([val[f'{D}|old|hsn|{c}']['pp_all'] for c in range(NC)]).mean(0); b = np.array([val[f'{D}|new|hsn|{c}']['pp_all'] for c in range(NC)]).mean(0)
    r = b / a
    t += f"\n- per pixel at {len(S.NS_A)} log-spaced N in 4..1024 (held-out, HSN phase): geometric mean new/old {np.exp(np.log(r).mean()):.3f}, worst {r.max():.3f} at N={S.NS_A[int(r.argmax())]}, best {r.min():.3f} at N={S.NS_A[int(r.argmin())]}, N with ratio > 1.03: {[S.NS_A[i] for i in np.where(r > 1.03)[0]]}\n"
    if D != '1':
        prs = list(o['chi'])
        t += '\n**Pairwise temporal chi-square/dof (8x8 histogram of 1024 frames, mean over 4096 pixels; white = 1.0, lower is more even)**\n\n'
        t += md_table(['Set'] + prs, [['current, selection region'] + [f"{o['chi'][k]:.2f}" for k in prs], ['new, selection region'] + [f"{n['chi'][k]:.2f}" for k in prs],
                                      ['current, held-out mean'] + [f"{np.mean([val[f'{D}|old|hsn|{c}']['chi'][k] for c in range(NC)]):.2f}" for k in prs],
                                      ['new, held-out mean'] + [f"{np.mean([val[f'{D}|new|hsn|{c}']['chi'][k] for c in range(NC)]):.2f}" for k in prs]])
    t += '\n**Selection ranking (HSN phase; J = geo-mean of 19 metric ratios vs current)**\n\n'
    t += md_table(['Candidate', 'steps', 'J', 'worst ratio', 'worst metric', 'max pair chi2', 'eligible', 'J with hash phase', 'HSN/hash EMA+3x3'],
                  [[r['name'], str(r['steps']), f"{r['J']:.3f}", f"{r['max_ratio']:.3f}", LABEL(r['worst']), f"{r['chi_max']:.2f}", 'yes' if r['eligible'] else '',
                    f"{np.exp(np.mean([np.log(R[f'{D}|{r['name']}|hash'][m] / oh[m]) for m in S.OBJ])):.3f}", f"{R[f'{D}|{r['name']}|hsn']['ema/box3'] / R[f'{D}|{r['name']}|hash']['ema/box3']:.2f}"] for r in p['ranking']])

# supplementary: first two steps of the 4D sets as a 2D pair (PR VXGI usage), held-out 2D integrands, HSN phase
t += '\n## Supplementary: first two steps of the 4D set used as a 2D pair (held-out 2D integrands, HSN phase)\n\n'
rows = []
for m in ROWS:
    a, b, r2, n2 = held('2', 'old4xy', 'hsn', m), held('2', 'new4xy', 'hsn', m), held('2', 'old', 'hsn', m), held('2', 'new', 'hsn', m)
    rows.append([LABEL(m), e3(a.mean()), e3(b.mean()), f'{(b / a).mean():.3f} +- {(b / a).std(ddof=1):.3f}', e3(r2.mean()), e3(n2.mean())])
t += md_table(['Metric', 'R4_STEPS[0],[1]', 'new 4D set [0],[1]', 'ratio', 'R2_STEPS', 'new 2D set'], rows)
save('steps', dict(picks={D: sel['picks'][D]['pick'] for D in ('1', '2', '4')}, any_eligible={D: sel['picks'][D]['any_eligible'] for D in ('1', '2', '4')}), t, OUT)

# figure: old vs new 4D pairwise projections, one pixel, 256 frames
import noises as N
PIX = (21, 13)
new4 = sel['picks']['4']['pick']['steps']
fig, axs = newfig('HSN: pairwise projections of one pixel\'s 256 four-dimensional samples, current and proposed steps',
                  f'Pixel {PIX}, frames 0-255. Top: current R4_STEPS (pair 1-3 sits on five lines; dimensions 1 and 4 revisit 7 and 13 clusters). Bottom: proposed steps {new4}.', 2, 6, 6.9, top_in=1.45)
fig.subplots_adjust(left=0.035, right=0.995, wspace=0.05, hspace=0.12, bottom=0.02)
for r, (nm, st) in enumerate((('current R4_STEPS', S.R4), ('proposed', new4))):
    s = np.stack([N.hsn1(np.array([PIX[0]]), np.array([PIX[1]]), np.arange(256), k + 1, v) for k, v in enumerate(st)])
    for c, (i, j) in enumerate(itertools.combinations(range(4), 2)):
        ax = axs[r][c]
        ax.scatter(s[i], s[j], s=7, color='#2f6fd0', linewidths=0)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        for sp in ax.spines.values():
            sp.set_visible(True)
        ax.set_title(f'dimensions {i + 1}-{j + 1}', fontsize=11, loc='center')
        if c == 0:
            ax.set_ylabel(f'HSN, {nm}')
savefig(fig, 'pairs_4d_current_vs_candidate', os.path.join(OUT, 'figures'))
