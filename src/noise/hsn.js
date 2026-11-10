// Plain-JavaScript reference for Houston Stratified Noise (HSN). Transliterated operation-for-operation
// from the TSL in three.js PR #35429, examples/jsm/tsl/utils/HierarchicalHashedWeyl.js (commit 34137c3756fa).
// All arithmetic is 32-bit unsigned and wrapping, exactly as WGSL u32.

import { GOLDEN_STEP, R4_STEPS } from './steps.js';

// 2-round xorshift-multiply integer hash, constants [16 21f0aaad 15 735a2d97 15] (hash-prospector family).
export function hashUint( v ) {

	v >>>= 0;
	v = Math.imul( v ^ ( v >>> 16 ), 0x21f0aaad ) >>> 0;
	v = Math.imul( v ^ ( v >>> 15 ), 0x735a2d97 ) >>> 0;
	return ( v ^ ( v >>> 15 ) ) >>> 0;

}

// 2D pre-mix with the xxHash32 primes, then XOR the seed, then hash.
export function pixelHash( x, y, seed ) {

	return hashUint( ( Math.imul( x, 0x9e3779b1 ) ^ Math.imul( y, 0x85ebca77 ) ^ seed ) >>> 0 );

}

export const LEVEL_SALTS = [ 0, 1, 2 ].map( ( level ) => Math.imul( level + 1, 0x632be5ab ) >>> 0 ); // 0x632be5ab, 0xc657cb56, 0x2983b101
export const PHASE_SALT = 0x02e5be93;

// The 6-bit hierarchical rank in bits 31..26 of a u32 (bits 25..0 are zero).
// Level 0 (which pixel inside its 2x2 block) is the most significant digit, as in a Bayer matrix.
export function hsnRank( x, y, seed ) {

	let rank = 0;

	for ( let level = 0; level < 3; level ++ ) {

		// one hash per parent block: all children of a 2x2 / 4x4 / 8x8 parent share it
		const scramble = pixelHash( x >>> ( level + 1 ), y >>> ( level + 1 ), ( seed ^ LEVEL_SALTS[ level ] ) >>> 0 );
		const a = ( x >>> level ) & 1;
		const b = ( y >>> level ) & 1;
		const low = ( scramble & 4 ) !== 0 ? a : b; // orientation swap
		const child = ( ( a ^ b ) << 1 ) | low; // 2x2 Bayer cell (or its transpose)
		rank = ( rank | ( ( child ^ ( scramble & 3 ) ) << ( 30 - 2 * level ) ) ) >>> 0;

	}

	return rank;

}

// Per-tile phase: a full 32-bit hash of the 8x8 tile coordinate (a Cranley-Patterson rotation of the tile).
export function hsnPhase( x, y, seed ) {

	return pixelHash( x >>> 3, y >>> 3, ( seed ^ PHASE_SALT ) >>> 0 );

}

// The 32-bit fixed-point value before float conversion.
export function hsnBits( x, y, index, seed, step = GOLDEN_STEP ) {

	return ( hsnRank( x, y, seed ) + hsnPhase( x, y, seed ) + Math.imul( index >>> 0, step ) ) >>> 0;

}

// The scalar noise: a float in [0, 1), a multiple of 2^-24.
export function hsn( x, y, index, seed, step = GOLDEN_STEP ) {

	return ( hsnBits( x, y, index, seed, step ) >>> 8 ) / 16777216;

}

// Four values per pixel as the three.js helper binds them: independently seeded, each with its own R4 step.
export function hsn4( x, y, index, seed = 0 ) {

	return [ 0, 1, 2, 3 ].map( ( k ) => hsn( x, y, index, seed * 4 + k + 1, R4_STEPS[ k ] ) );

}
