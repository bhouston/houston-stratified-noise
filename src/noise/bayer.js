// Standard recursive 8x8 Bayer ordered-dither matrix (M2 = [[0,2],[3,1]]).
// HSN with its scramble and phase switched off is exactly this.

export function bayerIndex( x, y ) {

	let rank = 0;

	for ( let level = 0; level < 3; level ++ ) {

		const a = ( x >>> level ) & 1, b = ( y >>> level ) & 1;
		rank |= ( ( ( a ^ b ) << 1 ) | b ) << ( 4 - 2 * level );

	}

	return rank; // 0..63

}

export function bayer( x, y ) {

	return ( bayerIndex( x, y ) + 0.5 ) / 64;

}
