// Measurement-only variant D: 64x64 void-and-cluster blue noise (Ulichney 1993, toroidal, sigma 1.5) + per-dimension
// Roberts Weyl steps. Generator ported from scratchpad/analysis-temporal/noises.py (void_and_cluster); the initial
// random pattern uses a JS PRNG, so the texture is a different instance of the same algorithm.
import { DataTexture, FloatType, NearestFilter, RedFormat, RepeatWrapping } from 'three/webgpu';
import { Fn, ivec2, textureLoad, uint, vec4 } from 'three/tsl';
import { R4_STEPS } from './HierarchicalHashedWeyl.js';

export function voidAndCluster( size = 64, sigma = 1.5, seed = 1 ) {

	const n = size * size;
	const kernel = new Float64Array( n );

	for ( let i = 0; i < size; i ++ ) for ( let j = 0; j < size; j ++ ) {

		const di = Math.min( i, size - i ), dj = Math.min( j, size - j );
		kernel[ i * size + j ] = Math.exp( - ( di * di + dj * dj ) / ( 2 * sigma * sigma ) );

	}

	const pattern = new Uint8Array( n ), energy = new Float64Array( n );

	const splat = ( p, sign ) => {

		const pi = Math.floor( p / size ), pj = p % size;
		for ( let i = 0; i < size; i ++ ) for ( let j = 0; j < size; j ++ ) energy[ i * size + j ] += sign * kernel[ ( ( i - pi + size ) % size ) * size + ( j - pj + size ) % size ];

	};

	const set = ( p, value ) => { pattern[ p ] = value; splat( p, value ? 1 : - 1 ); };

	const tightest = () => { let best = - 1, e = - Infinity; for ( let p = 0; p < n; p ++ ) if ( pattern[ p ] === 1 && energy[ p ] > e ) { e = energy[ p ]; best = p; } return best; };
	const largestVoid = () => { let best = - 1, e = Infinity; for ( let p = 0; p < n; p ++ ) if ( pattern[ p ] === 0 && energy[ p ] < e ) { e = energy[ p ]; best = p; } return best; };

	// initial pattern: a random 10% of the texels (mulberry32 partial shuffle)

	let state = seed >>> 0;
	const random = () => { state = state + 0x6D2B79F5 | 0; let t = Math.imul( state ^ state >>> 15, 1 | state ); t = t + Math.imul( t ^ t >>> 7, 61 | t ) ^ t; return ( ( t ^ t >>> 14 ) >>> 0 ) / 4294967296; };
	const order = Uint32Array.from( { length: n }, ( _, i ) => i );
	const ones = Math.floor( n / 10 );

	for ( let i = 0; i < ones; i ++ ) {

		const j = i + Math.floor( random() * ( n - i ) );
		[ order[ i ], order[ j ] ] = [ order[ j ], order[ i ] ];
		set( order[ i ], 1 );

	}

	while ( true ) { // relax the initial pattern

		const c = tightest(); set( c, 0 );
		const v = largestVoid(); set( v, 1 );
		if ( v === c ) break;

	}

	const rank = new Float32Array( n ).fill( - 1 );
	const pattern0 = pattern.slice(), energy0 = energy.slice();

	for ( let r = ones - 1; r >= 0; r -- ) { const c = tightest(); set( c, 0 ); rank[ c ] = r; }

	pattern.set( pattern0 ); energy.set( energy0 );

	for ( let r = ones; r < n; r ++ ) { const v = largestVoid(); set( v, 1 ); rank[ v ] = r; }

	// self-check: the ranks are a permutation of 0..n-1
	const seen = new Uint8Array( n );
	for ( const r of rank ) { if ( r < 0 || seen[ r ] ) throw new Error( 'voidAndCluster: ranks are not a permutation' ); seen[ r ] = 1; }

	return rank;

}

let _texture = null;

function getTexture() {

	if ( _texture === null ) {

		const t0 = performance.now();
		const rank = voidAndCluster();
		globalThis.__VC_MS = performance.now() - t0;
		globalThis.__VC_BYTES = rank.byteLength;

		// r32float, one channel, 64 x 64 x 4 bytes = 16,384 bytes; integer ranks 0..4095 are exact in float32
		_texture = new DataTexture( rank, 64, 64, RedFormat, FloatType );
		_texture.minFilter = _texture.magFilter = NearestFilter;
		_texture.wrapS = _texture.wrapT = RepeatWrapping;
		_texture.needsUpdate = true;

	}

	return _texture;

}

const OFFSETS = [ [ 0, 0 ], [ 23, 41 ], [ 47, 13 ], [ 11, 53 ] ];

export function bindVoidClusterRd( resolution, seed = 0, steps = R4_STEPS ) { // the seed is unused: one texture, fixed offsets

	const map = getTexture();

	return Fn( ( [ uvCoord, sampleIndex ] ) => {

		const pixel = ivec2( uvCoord.mul( resolution ).floor() );
		const index = uint( sampleIndex ).toConst();
		const result = vec4( 0 ).toVar();

		for ( let k = 0; k < steps.length; k ++ ) {

			// exact texel fetch with repeat wrap, then all arithmetic in 0.32 fixed point:
			// phase = ( rank + 0.5 ) / 4096, time = index * step (wraps mod 2^32, no precision loss at large indices)
			const rank = uint( textureLoad( map, pixel.add( ivec2( OFFSETS[ k ][ 0 ], OFFSETS[ k ][ 1 ] ) ).bitAnd( 63 ) ).r );
			const phase = rank.shiftLeft( 20 ).add( uint( 1 << 19 ) );
			result.element( k ).assign( phase.add( index.mul( uint( steps[ k ] ) ) ).shiftRight( 8 ).toFloat().div( 16777216 ) );

		}

		return result;

	} );

}
