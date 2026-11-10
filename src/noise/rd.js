// Baselines without the hierarchy: a per-pixel spatial phase plus a per-dimension R_d (Weyl) step in time.
// Definitions match analysis/temporal (extras.py: hash_rd, ign_rd; noises.py: vc_rd).

import { pcg } from './hashes.js';
import { ign } from './ign.js';
import { VC64 } from './vc64.js';
import { GOLDEN_STEP, RD_ALPHAS } from './steps.js';

const f = Math.fround;

// "Hash + R_d": one PCG hash per pixel and dimension as a Cranley-Patterson offset, plus index * step in
// uint32. White in space, low-discrepancy in time: HSN with the rank removed.
export function hashRd( x, y, index = 0, dimension = 0, step = GOLDEN_STEP, seed = 0 ) {

	const phase = pcg( x ^ pcg( y ^ pcg( dimension + 7001 + 97 * seed ) ) );
	return ( ( phase + Math.imul( index >>> 0, step ) ) >>> 8 ) / 16777216;

}

// "IGN + R_d": IGN( pixel centre + a large fixed offset per dimension ) as the phase, plus index * step in uint32.
export const IGN_RD_OFFSETS = [ [ 0, 0 ], [ 47, 17 ], [ 101, 59 ], [ 173, 113 ] ];

export function ignRd( x, y, index = 0, dimension = 0, step = GOLDEN_STEP ) {

	const [ ox, oy ] = IGN_RD_OFFSETS[ dimension ];
	const phase = ( Math.floor( ign( f( f( x + 0.5 ) + ox ), f( f( y + 0.5 ) + oy ) ) * 16777216 ) << 8 ) >>> 0;
	return ( ( phase + Math.imul( index >>> 0, step ) ) >>> 8 ) / 16777216;

}

// "Void-and-cluster + R_d": a 64x64 blue-noise texture read at a per-dimension texel offset as the phase,
// plus float( index ) * alpha_d in float32, as a shader sampling a texture would do it. Float time loses
// precision at large indices (about 10^6 frames); pass alpha = step / 2^32 to use other steps.
export const VC_OFFSETS = [ [ 0, 0 ], [ 23, 41 ], [ 47, 13 ], [ 11, 53 ] ];

export function vcRd( x, y, index = 0, dimension = 0, alpha = RD_ALPHAS[ 1 ][ 0 ] ) {

	const [ ox, oy ] = VC_OFFSETS[ dimension ];
	const texel = f( ( VC64[ ( ( y + oy ) % 64 ) * 64 + ( x + ox ) % 64 ] + 0.5 ) / 4096 );
	const v = f( texel + f( f( index ) * f( alpha ) ) );
	return v - Math.floor( v );

}
