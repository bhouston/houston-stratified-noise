// Registry of scalar noises with one call shape: fn( x, y, index, seed ) -> [0, 1).
// `animated: false` means the index is ignored (the pattern is the same every frame).

import { hsn } from './hsn.js';
import { whitePcg, whiteHsnHash, sinHash, hash12 } from './hashes.js';
import { ign, animatedIgn } from './ign.js';
import { r2, threejsAnalytic } from './r2.js';
import { bayer } from './bayer.js';
import { hashRd, ignRd } from './rd.js';

export const NOISES = [
	{ id: 'hsn', label: 'HSN', animated: true, fn: ( x, y, i, s ) => hsn( x, y, i, s ) },
	{ id: 'white', label: 'White (PCG3D)', animated: true, fn: whitePcg },
	{ id: 'white-hsn-hash', label: 'White (HSN\'s own hash)', animated: true, fn: whiteHsnHash },
	{ id: 'sin', label: 'fract(sin) hash', animated: false, fn: ( x, y ) => sinHash( x, y ) },
	{ id: 'hash12', label: 'Hoskins hash12', animated: false, fn: ( x, y ) => hash12( x, y ) },
	{ id: 'ign', label: 'IGN', animated: false, fn: ( x, y ) => ign( x, y ) },
	{ id: 'ign-animated', label: 'Animated IGN (scrolled)', animated: true, fn: ( x, y, i ) => animatedIgn( x, y, i ) },
	{ id: 'ign-rd', label: 'IGN + R1 (golden) step', animated: true, fn: ( x, y, i ) => ignRd( x, y, i ) },
	{ id: 'hash-rd', label: 'Hash + R1 (golden) step', animated: true, fn: ( x, y, i, s ) => hashRd( x, y, i, s ) },
	{ id: 'r2', label: 'R2 (Roberts)', animated: false, fn: ( x, y ) => r2( x, y ) },
	{ id: 'threejs-analytic', label: 'Three.js Analytic R²', animated: true, fn: ( x, y, i ) => threejsAnalytic( x, y, i ) },
	{ id: 'bayer', label: 'Bayer 8×8', animated: false, fn: ( x, y ) => bayer( x, y ) }
];

export * from './steps.js';
export * from './hsn.js';
export * from './hashes.js';
export * from './ign.js';
export * from './r2.js';
export * from './bayer.js';
export * from './rd.js';
