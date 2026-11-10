# FAST noise textures (Electronic Arts SEED)

Two packed atlases of FAST (Filter-Adapted Spatio-Temporal) noise, 128×128×32 each.

- **Files:** `gauss1-ema01-spatial.png`, `gauss1-ema01-spatio-temporal.png`, with a `.txt` beside each describing the source textures and the packing. Both are 256×4096 8-bit RGB PNGs.
- **Authors:** William Donnelly, Alan Wolfe, Judith Bütepage and Jon Valdés (SEED, Electronic Arts). Paper: "Filter-Adapted Spatio-Temporal Sampling for Real-Time Rendering", I3D 2024, https://arxiv.org/abs/2310.15364
- **Origin:** the textures come from `noise.zip` in https://github.com/electronicarts/fastnoise. The two atlases here are a repacking of those textures made for three.js pull request https://github.com/mrdoob/three.js/pull/35244 (`examples/textures/noises/fast/`), and were copied from that pull request's head commit `98781c8152e5edef408d9e42c4f2aa7667eab7b7`. Their git blob hashes (`bb838763c36b0bd77f2f82c384714bec0a3ff2c0`, `39e5cc3b38af88b3f7f824376377db41ac8f8aba`) match that commit.
- **Retrieved:** 2026-11-10. Upstream `electronicarts/fastnoise` `main` was at commit `2cf53e4bb510d07511fe63a312556d2a2e108c70` (2025-01-06) when the licence was checked.
- **SHA-256:** `43a02d620006aee446f0477a47695729fa0efccdf9f69bb4ca14d4a9f8a9ff3a` (spatial), `2f720e87953d2f013a17e5ed13649aeddbee93ba913da90c4c87b4f2d7bdad11` (spatio-temporal).

## Licence

BSD 3-Clause, "Copyright (c) 2023 Electronic Arts Inc. All rights reserved." The full text is in `LICENSE.txt` in this directory; it is byte-for-byte the upstream https://github.com/electronicarts/fastnoise/blob/main/LICENSE.txt (GitHub reports it as `BSD-3-Clause`). It permits "Redistribution and use in source and binary forms, with or without modification" provided the copyright notice, the list of conditions and the disclaimer are retained, and the name of Electronic Arts is not used to endorse derived products. The upstream repository has a single licence file covering the whole repository, including `noise.zip`; it has no separate statement for the textures.

## Use in this repository

`analysis/spatial/noises.py` reads the B channel of the left 128 columns (the scalar texture) of slices 0, 4, …, 28 as eight single-frame blue-noise references. The files are only ever parsed as images.
