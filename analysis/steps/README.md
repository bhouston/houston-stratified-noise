# Step-constant search

One bounded search for better temporal step constants, with one validation on held-out integrands.

Entry point, from the repository root: `pnpm analysis:steps` (about 5 minutes). It runs, in order:

1. `search.py cands`: analytic candidate generation (algebraic constructions plus seeded random vectors) → `results/steps/cands.json`
2. `search.py select`: harness metrics on the selection integrands; applies the selection rule written in the file header → `select.json`
3. `search.py validate`: the picked sets against the current constants on the held-out integrands (`heldout.py`), five seed and region configurations → `validate.json`
4. `report.py`: `tables_steps.md`, `tables_steps.json` and `figures/pairs_4d_current_vs_candidate.webp`

It imports the harness from `analysis/temporal/` (samplers, integrands, filters).

Verdict: keep the golden step for one value per pixel and `R2_STEPS` for two. For four, `R4_STEPS` stays by the stated bar; the candidate `[3280154747, 2481977421, 1303403687, 2746543331]` is a real trade-off and is exported from `src/noise/steps.js` as `TRADEOFF_R4_STEPS`, optional and not the default. The findings are on the website's Results page (source: `site/src/steps-readings.json`).
