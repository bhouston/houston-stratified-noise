// White-noise hashes. Integer hashes wrap like WGSL u32; float hashes round every intermediate to
// float32 like a shader (Math.sin is the platform's, not any GPU's).

import { pixelHash } from './hsn.js';

const f = Math.fround;
const fract = ( v ) => v - Math.floor( v );
const unit24 = ( v ) => ( v >>> 8 ) / 16777216;

// Jarzynski & Olano 2020, pcg3d; returns the x output.
export function pcg3d( x, y, z ) {

	x = ( Math.imul( x, 1664525 ) + 1013904223 ) >>> 0;
	y = ( Math.imul( y, 1664525 ) + 1013904223 ) >>> 0;
	z = ( Math.imul( z, 1664525 ) + 1013904223 ) >>> 0;
	x = ( x + Math.imul( y, z ) ) >>> 0;
	y = ( y + Math.imul( z, x ) ) >>> 0;
	z = ( z + Math.imul( x, y ) ) >>> 0;
	x ^= x >>> 16; y ^= y >>> 16; z ^= z >>> 16;
	return ( x + Math.imul( y, z ) ) >>> 0;

}

// A new independent frame per index; index 0 is pcg3d( x, y, seed ).
const frameSeed = ( index, seed ) => ( seed ^ Math.imul( index, 0x632be5ab ) ) >>> 0;

export function whitePcg( x, y, index = 0, seed = 1 ) {

	return unit24( pcg3d( x, y, frameSeed( index, seed ) ) );

}

// White noise from the same integer hash HSN uses.
export function whiteHsnHash( x, y, index = 0, seed = 1 ) {

	return unit24( pixelHash( x, y, frameSeed( index, seed ) ) );

}

// fract( sin( dot( p, vec2( 12.9898, 78.233 ) ) ) * 43758.5453 )
export function sinHash( x, y ) {

	const d = f( f( x * f( 12.9898 ) ) + f( y * f( 78.233 ) ) );
	return fract( f( f( Math.sin( d ) ) * f( 43758.5453 ) ) );

}

// Dave Hoskins' "hash without sine" hash12.
export function hash12( x, y ) {

	const k = f( 0.1031 ), o = f( 33.33 );
	let p0 = fract( f( x * k ) ), p1 = fract( f( y * k ) ), p2 = p0;
	const d = f( f( f( p0 * f( p1 + o ) ) + f( p1 * f( p2 + o ) ) ) + f( p2 * f( p0 + o ) ) );
	p0 = f( p0 + d ); p1 = f( p1 + d ); p2 = f( p2 + d );
	return fract( f( f( p0 + p1 ) * p2 ) );

}
