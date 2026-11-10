// Hash-free "analytic" lattice samplers, as compared in analysis/r4-ablation and measured in-engine
// (analysis/gpu, variants E, F and G). Every pixel's phase is a linear function of its coordinates, so
// each has visible lattice structure: 6-18% of a threshold mask's spectral power sits in one bin.

import { RD_ALPHAS } from './steps.js';

const f = Math.fround;
const fract = ( v ) => v - Math.floor( v );
const P2 = 1.32471795724474602596; // plastic number (R2)
const P4 = 1.1673039782614187; // root of x^5 = x + 1 (R4)
const fixed = ( v ) => Math.round( fract( v ) * 4294967296 ) >>> 0; // fraction -> u32 0.32 fixed point
const unit24 = ( v ) => ( v >>> 8 ) / 16777216;

// G. The RNoise.js of bhouston/three.js PR #42 ("analytic R4"), float32: a 32x32 tile shifted by an R2
// sequence of integer offsets; inside it t = cx + 32 cy + seed and value_k = fract( t / P^(k+1) + 0.5 ).
export function analyticR4Tile( x, y, index = 0, dimension = 0, seed = 47 ) {

	const i = f( index + seed );
	const ox = Math.floor( f( fract( f( i * f( 0.7548776662 ) ) ) * 32 ) );
	const oy = Math.floor( f( fract( f( i * f( 0.5698402910 ) ) ) * 32 ) );
	const t = f( f( ( x + ox ) % 32 + f( ( ( y + oy ) % 32 ) * 32 ) ) + seed );
	return fract( f( f( f( 1 / P4 ** ( dimension + 1 ) ) * t ) + 0.5 ) );

}

// (i) Single lattice, float32: t = x / P + y / P^2 (plastic P), value_k = fract( ( t + index ) * alpha_k ).
// All values of a pixel are functions of one scalar. Float time breaks between 10^6 and 10^7 frames.
export function analyticSingleLattice( x, y, index = 0, alpha = RD_ALPHAS[ 4 ][ 0 ] ) {

	const t = f( f( x * f( 1 / P2 ) ) + f( y * f( 1 / P2 ** 2 ) ) );
	return fract( f( f( t + f( index ) ) * f( alpha ) ) );

}

// (ii) Per-dimension lattices: phase_k = fract( x a_k + y b_k ) in float32, plus index * step_k in uint32.
// Direction pairs: the R2 lattice, its 90 degree rotation, and its two 45 degree images.
const A1 = 1 / P2, A2 = 1 / P2 ** 2;
export const LATTICE_DIRECTIONS = [ [ A1, A2 ], [ - A2, A1 ], [ A1 + A2, A2 - A1 ], [ A1 - A2, A1 + A2 ] ];

export function analyticPerDimensionLattices( x, y, index = 0, dimension = 0, step ) {

	const [ a, b ] = LATTICE_DIRECTIONS[ dimension ];
	const phase = ( Math.floor( fract( f( f( x * f( a ) ) + f( y * f( b ) ) ) ) * 16777216 ) << 8 ) >>> 0;
	return unit24( ( phase + Math.imul( index >>> 0, step ) ) >>> 0 );

}

// E. Single lattice exactly as measured in-engine, all in uint32: value_k = fract( ( t + index ) * alpha_k )
// with t = x / P + y / P^2 + seed.
export function engineSingleLattice( x, y, index = 0, alpha = RD_ALPHAS[ 4 ][ 0 ], seed = 47 ) {

	return unit24( ( Math.imul( x, fixed( alpha / P2 ) ) + Math.imul( y, fixed( alpha / P2 ** 2 ) ) + fixed( alpha * seed ) + Math.imul( index >>> 0, fixed( alpha ) ) ) >>> 0 );

}

// F. Per-dimension lattices exactly as measured in-engine, all in uint32, with different direction pairs
// from (ii): the R2 lattice (a, b), then (b, 1 - a), (b, a), (a, 1 - b).
export const ENGINE_LATTICE_DIRECTIONS = [ [ A1, A2 ], [ A2, 1 - A1 ], [ A2, A1 ], [ A1, 1 - A2 ] ];

export function engineLattices( x, y, index = 0, dimension = 0, alpha = RD_ALPHAS[ 4 ][ dimension ] ) {

	const [ a, b ] = ENGINE_LATTICE_DIRECTIONS[ dimension ];
	return unit24( ( Math.imul( x, fixed( a ) ) + Math.imul( y, fixed( b ) ) + Math.imul( index >>> 0, fixed( alpha ) ) ) >>> 0 );

}
