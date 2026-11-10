// Measurement-only white noise: an independent hash per pixel, frame and dimension. Not part of any PR.
import { Fn, uint, vec4 } from 'three/tsl';

const hashUint = Fn( ( [ input ] ) => {

	const value = uint( input ).toVar();
	value.assign( value.bitXor( value.shiftRight( 16 ) ).mul( uint( 0x21f0aaad ) ) );
	value.assign( value.bitXor( value.shiftRight( 15 ) ).mul( uint( 0x735a2d97 ) ) );
	return value.bitXor( value.shiftRight( 15 ) );

} );

// pixel: integer-valued vec2, sampleIndex: float or uint node, seed: JS number. Returns vec4 in [0,1).
export function whiteNoise4( pixel, sampleIndex, seed = 0 ) {

	const runSeed = ( globalThis.__WHITE_SEED ?? 0 ) >>> 0;
	const x = uint( pixel.x ), y = uint( pixel.y );
	const frameHash = hashUint( uint( sampleIndex ).add( uint( runSeed ) ) ).toConst();
	const dimension = ( k ) => hashUint( x.mul( uint( 0x9e3779b1 ) ).bitXor( y.mul( uint( 0x85ebca77 ) ) ).bitXor( frameHash.add( uint( Math.imul( seed * 4 + k + 1, 0x68bc21eb ) >>> 0 ) ) ) ).shiftRight( 8 ).toFloat().div( 16777216 );
	return vec4( dimension( 0 ), dimension( 1 ), dimension( 2 ), dimension( 3 ) );

}

export function bindWhiteNoise( resolution, seed = 0 ) {

	return Fn( ( [ uvCoord, sampleIndex ] ) => whiteNoise4( uvCoord.mul( resolution ).floor(), sampleIndex, seed ) );

}
