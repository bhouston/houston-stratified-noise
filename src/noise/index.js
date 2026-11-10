// Registry of noises with one call shape: fn( x, y, index, seed, dimension, steps ) -> [0, 1).
//   seed       0, 1, 2, ... selects an independent realization where the noise has one
//   dimension  which of the values per pixel (0-based)
//   steps      the temporal step per dimension, u32 fixed point (see steps.js); only Weyl-stepped noises use it
// `animated: false` means the index is ignored; `multi: false` means the noise only defines one value per pixel.

import { hsn } from './hsn.js';
import { white, whiteHsnHash, sinHash, hash12 } from './hashes.js';
import { ign, animatedIgn } from './ign.js';
import { r2, threejsAnalytic } from './r2.js';
import { bayer } from './bayer.js';
import { hashRd, ignRd, vcRd } from './rd.js';
import { analyticR4Tile, analyticSingleLattice, analyticPerDimensionLattices, engineLattices } from './analytic-r4.js';

export const NOISES = [
	{ id: 'hsn', label: 'HSN', animated: true, multi: true, fn: ( x, y, i, s, d, steps ) => hsn( x, y, i, s * 4 + d + 1, steps[ d ] ) },
	{ id: 'hash-rd', label: 'Hash + R_d steps', animated: true, multi: true, fn: ( x, y, i, s, d, steps ) => hashRd( x, y, i, d, steps[ d ], s ) },
	{ id: 'ign-rd', label: 'IGN + R_d steps', animated: true, multi: true, fn: ( x, y, i, s, d, steps ) => ignRd( x, y, i, d, steps[ d ] ) },
	{ id: 'vc-rd', label: 'Void-and-cluster 64² + R_d steps', animated: true, multi: true, fn: ( x, y, i, s, d, steps ) => vcRd( x, y, i, d, steps[ d ] / 4294967296 ) },
	{ id: 'ign-animated', label: 'Animated IGN (scrolled)', animated: true, multi: true, fn: ( x, y, i, s, d ) => animatedIgn( x, y, i, d ) },
	{ id: 'threejs-analytic', label: 'Three.js Analytic R²', animated: true, multi: true, fn: ( x, y, i, s, d ) => threejsAnalytic( x, y, i, 47, d ) },
	{ id: 'r4-tile', label: 'Analytic R4, 32×32 tile (three.js fork PR #42)', animated: true, multi: true, fn: ( x, y, i, s, d ) => analyticR4Tile( x, y, i, d ) },
	{ id: 'r4-single', label: 'Analytic R_d, single lattice', animated: true, multi: true, fn: ( x, y, i, s, d, steps ) => analyticSingleLattice( x, y, i, steps[ d ] / 4294967296 ) },
	{ id: 'r4-lattices', label: 'Analytic R_d, per-value lattices', animated: true, multi: true, fn: ( x, y, i, s, d, steps ) => analyticPerDimensionLattices( x, y, i, d, steps[ d ] ) },
	{ id: 'r4-lattices-engine', label: 'Analytic R_d, per-value lattices (in-engine variant F)', animated: true, multi: true, fn: ( x, y, i, s, d, steps ) => engineLattices( x, y, i, d, steps[ d ] / 4294967296 ) },
	{ id: 'white', label: 'White (PCG hash)', animated: true, multi: true, fn: ( x, y, i, s, d ) => white( x, y, i, d, s ) },
	{ id: 'white-hsn-hash', label: 'White (HSN\'s own hash)', animated: true, multi: false, fn: ( x, y, i, s ) => whiteHsnHash( x, y, i, s + 1 ) },
	{ id: 'sin', label: 'fract(sin) hash', animated: false, multi: false, fn: ( x, y ) => sinHash( x, y ) },
	{ id: 'hash12', label: 'Hoskins hash12', animated: false, multi: false, fn: ( x, y ) => hash12( x, y ) },
	{ id: 'ign', label: 'IGN', animated: false, multi: false, fn: ( x, y ) => ign( x, y ) },
	{ id: 'r2', label: 'R2 (Roberts)', animated: false, multi: false, fn: ( x, y ) => r2( x, y ) },
	{ id: 'bayer', label: 'Bayer 8×8', animated: false, multi: false, fn: ( x, y ) => bayer( x, y ) }
];

export * from './steps.js';
export * from './hsn.js';
export * from './hashes.js';
export * from './ign.js';
export * from './r2.js';
export * from './bayer.js';
export * from './rd.js';
export * from './analytic-r4.js';
export { VC64 } from './vc64.js';
