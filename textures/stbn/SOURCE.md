# NVIDIA spatiotemporal blue noise (STBN): not included, downloaded on first use

The temporal analysis uses 128 slices of NVIDIA's STBN textures as a reference. They are **not committed to this repository** because of their licence (below). `analysis/temporal/noises.py` (`download_stbn`) fetches the archive the first time the analysis runs, checks its SHA-256, extracts only the 128 PNG files it reads into `analysis/temporal/cache/stbn/` (git-ignored), and only ever parses them as images.

- **Files used:** `stbn_scalar_2Dx1Dx1D_128x128x64x1_0..63.png` and `stbn_vec2_2Dx1D_128x128x64_0..63.png` from `Assets/STBN.zip`.
- **Authors:** Alan Wolfe, Nathan Morrical, Tomas Akenine-Möller and Ravi Ramamoorthi (NVIDIA), "Scalar Spatiotemporal Blue Noise Masks", EGSR 2022, https://arxiv.org/abs/2112.09629
- **Origin:** https://github.com/NVIDIA-RTX/STBN, file `Assets/STBN.zip` at commit `48b2839e4d8b7f0202ac72c6b0ae720d235a5b8b` (2025-02-05), 29,681,961 bytes, SHA-256 `f262aaa79704b913ad1ac22b11674931c5c16a788688f8ce49ec43d59eb5c747`.
- **Retrieved:** 2026-11-10.

## Licence

The repository's `License.txt` (GitHub reports it as "Other") offers two licences. The first is headed "Non-Commercial Use License" and titled "NVIDIA Source Code License for Spatiotemporal Blue Noise Texture Generation". Its relevant terms:

> 3.1 Redistribution. You may reproduce or distribute the Work only if (a) you do so under this License, (b) you include a complete copy of this License with your distribution, and (c) you retain without modification any copyright, patent, trademark, or attribution notices that are present in the Work.

> 3.3 Use Limitation. The Work and any derivative works thereof only may be used or intended for use non-commercially. Notwithstanding the foregoing, NVIDIA and its affiliates may use the Work and any derivative works commercially. As used herein, "non-commercially" means for research or evaluation purposes only.

The second is headed "Commercial Use License" and is the "NVIDIA RTX SDKs LICENSE", which does not allow distributing the SDK as a stand-alone product.

Redistribution is therefore allowed only under NVIDIA's non-commercial licence, which is incompatible with shipping the files inside an MIT-licensed repository that anyone may use commercially. Downloading them for this analysis is research and evaluation use.
