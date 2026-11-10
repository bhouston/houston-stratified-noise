# Free blue noise textures (Christoph Peters)

Eight 256×256 single-channel 16-bit void-and-cluster blue-noise textures.

- **Files:** `HDR_L_0.png` … `HDR_L_7.png`, unmodified copies of `Data/256_256/HDR_L_0.png` … `HDR_L_7.png` from the archive below, plus the archive's `LICENSE.txt` and `COPYING.txt`.
- **Author:** Christoph Peters, "Free blue noise textures", 2016-12-22, https://momentsingraphics.de/BlueNoise.html
- **Origin:** https://momentsingraphics.de/Media/BlueNoise/FreeBlueNoiseTextures.zip (42,288,737 bytes; server Last-Modified 2025-05-12; SHA-256 `4279ad66ec851a8cbf37025816ef5187bf1c1c001d46afb8edfa6d3c8e44c644`). Only the eight files used by the analysis are included here; the full archive has 1,743 files.
- **Retrieved:** 2026-11-10.

## Licence

CC0 1.0 Universal (Creative Commons public domain dedication). `LICENSE.txt` from the archive, in full:

> To the extent possible under law, Christoph Peters has waived all copyright and related or neighboring rights to the files in this directory and its subdirectories. This work is published from: Germany.
>
> The work is made available under the terms of the Creative Commons CC0 Public Domain Dedication.
>
> For more information please visit: https://creativecommons.org/publicdomain/zero/1.0/

`COPYING.txt` is the CC0 1.0 Universal legal code shipped in the same archive. The blog post says: "I have placed them in the public domain through CC0-licensing."

## Use in this repository

`analysis/spatial/noises.py` reads each file as a 16-bit image and maps value `v` to `(v + 0.5) / 65536`. The files are only ever parsed as images.
