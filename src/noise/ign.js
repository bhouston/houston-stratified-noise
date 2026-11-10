// Jorge Jimenez' interleaved gradient noise, float32 like a shader.

const f = Math.fround;
const fract = ( v ) => v - Math.floor( v );

export function ign( x, y ) {

	return fract( f( f( 52.9829189 ) * fract( f( f( f( 0.06711056 ) * f( x ) ) + f( f( 0.00583715 ) * f( y ) ) ) ) ) );

}

// Per-dimension pixel offsets of animated IGN in the temporal analysis. Dimension 2's is the removed
// three.js VXGI code; dimensions 3 and 4 are arbitrary choices.
export const IGN_OFFSETS = [ [ 0, 0 ], [ 5.588238, 3.14159 ], [ 47, 17 ], [ 101, 59 ] ];

// Animated IGN: IGN( pixel centre + index * 5.588238 [+ offset_d] ), float32 time. `cycle` wraps the index
// (the removed VXGI code used 64); without it float precision degrades by about 10^5 frames.
export function animatedIgn( x, y, index = 0, dimension = 0, cycle = 0 ) {

	const shift = f( f( cycle ? index % cycle : index ) * f( 5.588238 ) );
	const px = f( f( x + 0.5 ) + shift ), py = f( f( y + 0.5 ) + shift );
	if ( dimension === 0 ) return ign( px, py );
	return ign( f( px + f( IGN_OFFSETS[ dimension ][ 0 ] ) ), f( py + f( IGN_OFFSETS[ dimension ][ 1 ] ) ) );

}
