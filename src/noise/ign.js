// Jorge Jimenez' interleaved gradient noise, float32 like a shader.

const f = Math.fround;
const fract = ( v ) => v - Math.floor( v );

export function ign( x, y ) {

	return fract( f( f( 52.9829189 ) * fract( f( f( f( 0.06711056 ) * f( x ) ) + f( f( 0.00583715 ) * f( y ) ) ) ) ) );

}

// Animated IGN as in the three.js noise-smoothing example: scroll the coordinate diagonally by
// 5.588238 px per frame, wrapping the index at 256 to keep float32 precision.
export function animatedIgn( x, y, index = 0 ) {

	const shift = f( f( index % 256 ) * f( 5.588238 ) );
	return ign( f( x + shift ), f( y + shift ) );

}
