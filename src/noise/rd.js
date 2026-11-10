// Baselines without the hierarchy: a per-pixel spatial value plus an R_d (Weyl) step in time.
// For one scalar the R_1 step is the golden ratio; pass R2_STEPS[k] / R4_STEPS[k] for more dimensions.

import { pixelHash } from './hsn.js';
import { ign } from './ign.js';
import { GOLDEN_STEP } from './steps.js';

// "hash + R_d": white in space (a hashed Cranley-Patterson offset per pixel), low-discrepancy in time.
// This is HSN with the rank removed.
export function hashRd( x, y, index = 0, seed = 1, step = GOLDEN_STEP ) {

	return ( ( pixelHash( x, y, seed ) + Math.imul( index >>> 0, step ) ) >>> 8 ) / 16777216;

}

// "IGN + R_d": IGN in space, the same Weyl step in time.
export function ignRd( x, y, index = 0, step = GOLDEN_STEP ) {

	const v = ign( x, y ) + ( Math.imul( index >>> 0, step ) >>> 0 ) / 4294967296;
	return v - Math.floor( v );

}
