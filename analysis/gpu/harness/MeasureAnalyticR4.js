// Measurement-only variants E and F: hash-free analytic R4 / R2 lattices (not part of any PR).
// All arithmetic is 0.32 fixed point in uint32 (wraps mod 2^32), so neither large pixel coordinates nor large
// frame indices lose precision.
import { Fn, uint, vec4 } from 'three/tsl';

const P = 1.32471795724474602596; // plastic number
const G = 1.1673039782614187; // R4 generalized golden ratio
const fixed = ( value ) => Math.round( ( value - Math.floor( value ) ) * 4294967296 ) >>> 0; // fract( value ) in 0.32 fixed point

export const R4_ALPHAS = [ 1 / G, 1 / G ** 2, 1 / G ** 3, 1 / G ** 4 ];
export const R2_ALPHAS = [ 1 / P, 1 / P ** 2 ];

// E. "Analytic R4, single lattice": one spatial scalar t( x, y ) = x / P + y / P^2 ( + seed ) used as a real-valued
// index into the sequence: value_k = fract( ( t * K + n ) * alpha_k ), K = 1.
// Since x, y and n are integers this is exactly x * fract( K alpha_k / P ) + y * fract( K alpha_k / P^2 ) + n * alpha_k (mod 1).

export function bindAnalyticSingleLattice( resolution, seed = 0, alphas = R4_ALPHAS, K = 1 ) {

	return Fn( ( [ uvCoord, sampleIndex ] ) => {

		const pixel = uvCoord.mul( resolution ).floor();
		const x = uint( pixel.x ).toConst(), y = uint( pixel.y ).toConst(), n = uint( sampleIndex ).toConst();
		const result = vec4( 0 ).toVar();

		for ( let k = 0; k < alphas.length; k ++ ) {

			const a = alphas[ k ];
			const phase = x.mul( uint( fixed( K * a / P ) ) ).add( y.mul( uint( fixed( K * a / P ** 2 ) ) ) ).add( uint( fixed( K * a * seed ) ) );
			result.element( k ).assign( phase.add( n.mul( uint( fixed( a ) ) ) ).shiftRight( 8 ).toFloat().div( 16777216 ) );

		}

		return result;

	} );

}

// F. "Analytic R4, per-dimension lattices": value_k = fract( x * a_k + y * b_k + n * alpha_k ). Each dimension gets the
// R2 lattice ( a, b ) = ( 1 / P, 1 / P^2 ) in a different orientation (identity, rotated 90 degrees, transposed,
// transposed and rotated), so every dimension has the same spatial quality but a different direction pair. No seed.

const A = 1 / P, B = 1 / P ** 2;
export const LATTICE_DIRECTIONS = [ [ A, B ], [ B, 1 - A ], [ B, A ], [ A, 1 - B ] ];

export function bindAnalyticPerDimensionLattices( resolution, seed = 0, alphas = R4_ALPHAS ) {

	return Fn( ( [ uvCoord, sampleIndex ] ) => {

		const pixel = uvCoord.mul( resolution ).floor();
		const x = uint( pixel.x ).toConst(), y = uint( pixel.y ).toConst(), n = uint( sampleIndex ).toConst();
		const result = vec4( 0 ).toVar();

		for ( let k = 0; k < alphas.length; k ++ ) {

			const [ a, b ] = LATTICE_DIRECTIONS[ k ];
			const phase = x.mul( uint( fixed( a ) ) ).add( y.mul( uint( fixed( b ) ) ) );
			result.element( k ).assign( phase.add( n.mul( uint( fixed( alphas[ k ] ) ) ) ).shiftRight( 8 ).toFloat().div( 16777216 ) );

		}

		return result;

	} );

}
