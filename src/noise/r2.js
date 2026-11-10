// Martin Roberts' R2 dither mask, and the "Analytic R2" variant three.js SSR used before PR #35429.

const f = Math.fround;
const fract = ( v ) => v - Math.floor( v );

export const PLASTIC = 1.32471795724474602596;

// fract( x / g + y / g^2 ), float64.
export function r2( x, y ) {

	return fract( x / PLASTIC + y / ( PLASTIC * PLASTIC ) );

}

// bindAnalyticNoise from three.js examples/jsm/tsl/utils/RNoise.js (dev), float32.
// Coordinates wrap to a 32x32 tile that is shifted per sample index; all four channels are
// fract( c_k * t ) of the same scalar t. Seed 47 is SSR's ray-march seed.
const CHANNELS = [ [ PLASTIC, 1 / PLASTIC ], [ PLASTIC * 2, 1 / PLASTIC ** 2 ], [ PLASTIC * 3, 0.4198754210 ], [ PLASTIC * 4, 1 / PLASTIC ** 3 ] ];

export function threejsAnalytic( x, y, index = 0, seed = 47, channel = 0 ) {

	const i = f( index + seed );
	const ox = Math.floor( f( fract( f( i * f( 0.7548776662 ) ) ) * 32 ) );
	const oy = Math.floor( f( fract( f( i * f( 0.5698402910 ) ) ) * 32 ) );
	const cx = ( x + ox ) % 32, cy = ( y + oy ) % 32;
	const t = f( f( f( cx * f( 1 / PLASTIC ) ) + f( cy * f( 1 / PLASTIC ** 2 ) ) ) + seed );
	const [ a, b ] = CHANNELS[ channel ];
	return fract( f( f( t * f( a ) ) * f( b ) ) );

}
