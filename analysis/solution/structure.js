// Numerical checks of the structural properties of the noise (permutation property, phase, uniformity,
// temporal behaviour, unaligned windows, dimension independence, step constants).
// Run from the repository root: node analysis/solution/structure.js
// Writes results/solution/structure.txt (everything printed) and structure.json (the tables the website shows).
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import * as H from '../../src/noise/index.js';
const { hsnRank, hsnPhase, hsnBits, hsn, GOLDEN_STEP, R2_STEPS, R4_STEPS } = H;
const SHORT = JSON.parse( readFileSync( new URL( '../../names.json', import.meta.url ) ) ).short;
const OUT = new URL( '../../results/solution/', import.meta.url );
const TWO32 = 4294967296;
const lines = [], json = { short: SHORT, windows: [], discrepancy: [] };
const log = ( ...a ) => { const s = a.map( ( v ) => typeof v === 'string' ? v : JSON.stringify( v ) ).join( ' ' ); lines.push( s ); console.log( s ); };
const hex = ( v ) => '0x' + ( v >>> 0 ).toString( 16 ).padStart( 8, '0' );

// deterministic white noise for baselines
let rs = 12345; const rnd = () => ( rs = H.hashUint( rs + 0x9e3779b9 ), rs / TWO32 );

log( '== constants' );
log( 'level salts', H.LEVEL_SALTS.map( hex ).join( ' ' ), 'phase salt', hex( H.PHASE_SALT ) );
{
	// generalized golden ratios: phi_d is the positive root of x^(d+1) = x + 1
	const root = ( d ) => { let x = 1.5; for ( let i = 0; i < 200; i ++ ) x = Math.pow( 1 + x, 1 / ( d + 1 ) ); return x; };
	for ( const [ name, d, steps ] of [ [ 'golden', 1, [ GOLDEN_STEP ] ], [ 'R2', 2, R2_STEPS ], [ 'R4', 4, R4_STEPS ] ] ) {
		const g = root( d );
		steps.forEach( ( s, k ) => {
			const exact = TWO32 / Math.pow( g, k + 1 );
			log( name, 'phi_d=' + g.toFixed( 16 ), 'k=' + k, 'step', s, hex( s ), '2^32/phi^(k+1)=' + exact.toFixed( 4 ), 'alpha=' + ( s / TWO32 ).toFixed( 10 ),
				'floor?', Math.floor( exact ) === s, 'round?', Math.round( exact ) === s, 'odd?', ( s & 1 ) === 1 );
		} );
	}
}

log( '\n== (a0) with scramble bits forced to 0 the rank is the classic 8x8 Bayer matrix' );
{
	const bayer = [ [ 0, 32, 8, 40, 2, 34, 10, 42 ], [ 48, 16, 56, 24, 50, 18, 58, 26 ], [ 12, 44, 4, 36, 14, 46, 6, 38 ], [ 60, 28, 52, 20, 62, 30, 54, 22 ],
		[ 3, 35, 11, 43, 1, 33, 9, 41 ], [ 51, 19, 59, 27, 49, 17, 57, 25 ], [ 15, 47, 7, 39, 13, 45, 5, 37 ], [ 63, 31, 55, 23, 61, 29, 53, 21 ] ];
	let ok = true;
	for ( let y = 0; y < 8; y ++ ) for ( let x = 0; x < 8; x ++ ) {
		let r = 0;
		for ( let l = 0; l < 3; l ++ ) { const a = ( x >> l ) & 1, b = ( y >> l ) & 1; r |= ( ( ( a ^ b ) << 1 ) | b ) << ( 4 - 2 * l ); }
		if ( r !== bayer[ y ][ x ] ) ok = false;
	}
	log( 'unscrambled rank == Bayer 8x8:', ok );
}

log( '\n== (a1) the per-parent scramble: which 2x2 arrangements occur (level 0, seed 1, 512x512)' );
{
	const counts = new Map();
	for ( let y = 0; y < 512; y += 2 ) for ( let x = 0; x < 512; x += 2 ) {
		const key = [ [ 0, 0 ], [ 1, 0 ], [ 0, 1 ], [ 1, 1 ] ].map( ( [ i, j ] ) => hsnRank( x + i, y + j, 1 ) >>> 30 ).join( '' );
		counts.set( key, ( counts.get( key ) || 0 ) + 1 );
	}
	log( 'distinct arrangements [r(0,0) r(1,0) r(0,1) r(1,1)]:', counts.size, 'of 24;', [ ...counts ].sort().map( ( [ k, n ] ) => k + ':' + n ).join( ' ' ) );
	// D4 orbit of the Bayer cell [[0,2],[3,1]]
	const cell = [ 0, 2, 3, 1 ]; // index = x + 2y
	const syms = [ ( x, y ) => [ x, y ], ( x, y ) => [ 1 - y, x ], ( x, y ) => [ 1 - x, 1 - y ], ( x, y ) => [ y, 1 - x ], ( x, y ) => [ 1 - x, y ], ( x, y ) => [ x, 1 - y ], ( x, y ) => [ y, x ], ( x, y ) => [ 1 - y, 1 - x ] ];
	const orbit = new Set( syms.map( ( f ) => [ [ 0, 0 ], [ 1, 0 ], [ 0, 1 ], [ 1, 1 ] ].map( ( [ x, y ] ) => { const [ u, v ] = f( x, y ); return cell[ u + 2 * v ]; } ).join( '' ) ) );
	log( 'equals the 8 rotations/reflections of the Bayer cell:', orbit.size === 8 && [ ...counts.keys() ].every( ( k ) => orbit.has( k ) ) );
	log( 'ranks {0,1} always on one diagonal:', [ ...counts.keys() ].every( ( k ) => ( +k[ 0 ] >> 1 ) === ( +k[ 3 ] >> 1 ) && ( +k[ 1 ] >> 1 ) === ( +k[ 2 ] >> 1 ) ) );
}

log( '\n== (a) aligned-block permutation property, 1024x1024, frames 0/1/999999, 6 seeds' );
{
	let blocks = 0, fail = 0;
	for ( const seed of [ 1, 2, 117, 118, 189, 240 ] ) for ( let k = 1; k <= 3; k ++ ) {
		const size = 1 << k;
		for ( let by = 0; by < 1024; by += size ) for ( let bx = 0; bx < 1024; bx += size ) {
			const seen = new Uint8Array( size * size );
			for ( let j = 0; j < size; j ++ ) for ( let i = 0; i < size; i ++ ) seen[ hsnRank( bx + i, by + j, seed ) >>> ( 32 - 2 * k ) ] ++;
			blocks ++; if ( ! seen.every( ( n ) => n === 1 ) ) fail ++;
		}
	}
	log( 'blocks tested', blocks, 'failures', fail );
	// low 26 bits of the rank are always zero
	let low = 0; for ( let i = 0; i < 1e5; i ++ ) low |= hsnRank( i % 977, ( i * 31 ) % 991, i ) & 0x03ffffff;
	log( 'rank low 26 bits OR-ed over 1e5 samples:', low );
}

log( '\n== (b,c) tile phase: values in a tile are 64 equally spaced values plus a per-tile offset' );
{
	let tiles = 0, bad = 0, badBins = 0, bad2 = 0, bad4 = 0;
	const phases = [];
	for ( const frame of [ 0, 1, 77, 4000000000 ] ) for ( let ty = 0; ty < 512; ty += 8 ) for ( let tx = 0; tx < 512; tx += 8 ) {
		const v = [];
		for ( let j = 0; j < 8; j ++ ) for ( let i = 0; i < 8; i ++ ) v.push( hsn( tx + i, ty + j, frame, 1 ) * 16777216 );
		v.sort( ( a, b ) => a - b );
		for ( let i = 1; i < 64; i ++ ) if ( v[ i ] - v[ i - 1 ] !== 262144 ) bad ++; // exactly 2^24/64 apart
		if ( v[ 0 ] >= 262144 ) bad ++;
		const bins = new Uint8Array( 64 ); v.forEach( ( x ) => bins[ Math.floor( x / 262144 ) ] ++ ); // fixed bins [k/64,(k+1)/64)
		if ( ! bins.every( ( n ) => n === 1 ) ) badBins ++;
		if ( frame === 0 ) phases.push( v[ 0 ] / 262144 );
		// 2x2 and 4x4 aligned sub-blocks are equally spaced too (1/4 and 1/16 apart)
		for ( const [ size, gap ] of [ [ 2, 4194304 ], [ 4, 1048576 ] ] ) for ( let by = 0; by < 8; by += size ) for ( let bx = 0; bx < 8; bx += size ) {
			const w = []; for ( let j = 0; j < size; j ++ ) for ( let i = 0; i < size; i ++ ) w.push( hsn( tx + bx + i, ty + by + j, frame, 1 ) * 16777216 );
			w.sort( ( a, b ) => a - b );
			for ( let i = 1; i < w.length; i ++ ) if ( w[ i ] - w[ i - 1 ] !== gap ) size === 2 ? bad2 ++ : bad4 ++;
		}
		tiles ++;
	}
	log( 'tiles x frames tested', tiles, '| spacing != 1/64 exactly:', bad, '| fixed 64-bin histogram not all-ones:', badBins, '| 2x2 spacing != 1/4:', bad2, '| 4x4 spacing != 1/16:', bad4 );
	const m = phases.reduce( ( a, b ) => a + b ) / phases.length;
	const hist = new Array( 8 ).fill( 0 ); phases.forEach( ( p ) => hist[ Math.floor( p * 8 ) ] ++ );
	log( 'sub-bin offset of tiles (fraction of 1/64): mean', m.toFixed( 3 ), 'hist8', hist.join( ',' ) );
	// tile mean varies only by the sub-bin offset
	const means = []; for ( let ty = 0; ty < 512; ty += 8 ) for ( let tx = 0; tx < 512; tx += 8 ) { let s = 0; for ( let j = 0; j < 8; j ++ ) for ( let i = 0; i < 8; i ++ ) s += hsn( tx + i, ty + j, 0, 1 ); means.push( s / 64 ); }
	log( 'tile mean min/max', Math.min( ...means ).toFixed( 5 ), Math.max( ...means ).toFixed( 5 ), '(63/128 =', ( 63 / 128 ).toFixed( 5 ), ', 65/128 =', ( 65 / 128 ).toFixed( 5 ) + ')' );
	// whole-image histogram
	const g = new Array( 64 ).fill( 0 ); for ( let y = 0; y < 512; y ++ ) for ( let x = 0; x < 512; x ++ ) g[ Math.floor( hsn( x, y, 5, 1 ) * 64 ) ] ++;
	log( '512x512 image, 64-bin histogram min/max count:', Math.min( ...g ), Math.max( ...g ), '(expected exactly', 512 * 512 / 64 + ')' );
}

log( '\n== (d) temporal behaviour' );
{
	// exact Weyl recurrence in u32
	let ok = true;
	for ( let i = 0; i < 2000; i ++ ) {
		const x = i * 13 % 500, y = i * 29 % 500, t = ( i * 2654435761 ) >>> 0;
		const d = ( hsnBits( x, y, ( t + 1 ) >>> 0, 3 ) - hsnBits( x, y, t, 3 ) ) >>> 0;
		if ( d !== GOLDEN_STEP ) ok = false;
	}
	log( 'bits(t+1) - bits(t) == step (mod 2^32) at random t up to 2^32:', ok );
	log( 'wrap: bits at index 2^32-1 plus step == bits at index 0:', ( ( hsnBits( 9, 9, 0xffffffff, 3 ) + GOLDEN_STEP ) >>> 0 ) === hsnBits( 9, 9, 0, 3 ) );
	// period: step odd => t*step mod 2^32 is a bijection of t. Check on a 2^16 analogue exhaustively and 2^k * step != 0 for k<32.
	let per = true; for ( const s of [ GOLDEN_STEP, ...R2_STEPS, ...R4_STEPS ] ) for ( let k = 0; k < 32; k ++ ) if ( Math.imul( s, 1 << k ) === 0 ) per = false;
	log( 'all steps: 2^k * step != 0 mod 2^32 for k<32 (order of step is exactly 2^32):', per );
	// 24-bit output period
	const seen = new Uint8Array( 1 << 24 ); let n = 0, t = 0;
	const b0 = hsnBits( 5, 6, 0, 1 );
	for ( ; t < ( 1 << 24 ); t ++ ) { const v = ( ( b0 + Math.imul( t, GOLDEN_STEP ) ) >>> 8 ); if ( ! seen[ v ] ) { seen[ v ] = 1; n ++; } }
	log( 'distinct 24-bit outputs of one pixel in the first 2^24 frames:', n, 'of', 1 << 24 );
	// three-gap theorem: gaps between the first N samples of one pixel take at most 3 distinct lengths
	for ( const N of [ 8, 16, 64, 256, 1000 ] ) {
		const v = []; for ( let i = 0; i < N; i ++ ) v.push( hsnBits( 5, 6, i, 1 ) ); v.sort( ( a, b ) => a - b );
		const gaps = new Set(); for ( let i = 0; i < N; i ++ ) gaps.add( ( v[ ( i + 1 ) % N ] - v[ i ] + ( i === N - 1 ? TWO32 : 0 ) ) );
		const g = [ ...gaps ].sort( ( a, b ) => a - b );
		// 1D star discrepancy
		const f = v.map( ( x ) => x / TWO32 ); let D = 0; f.forEach( ( x, i ) => { D = Math.max( D, Math.abs( x - i / N ), Math.abs( x - ( i + 1 ) / N ) ); } );
		const w = []; for ( let i = 0; i < N; i ++ ) w.push( rnd() ); w.sort( ( a, b ) => a - b ); let Dw = 0; w.forEach( ( x, i ) => { Dw = Math.max( Dw, Math.abs( x - i / N ), Math.abs( x - ( i + 1 ) / N ) ); } );
		log( 'N=' + N, 'distinct gap lengths', g.length, 'max/min gap ratio', ( g[ g.length - 1 ] / g[ 0 ] ).toFixed( 3 ), '| star discrepancy', D.toFixed( 4 ), 'white', Dw.toFixed( 4 ) );
	}
	// float IGN animation precision for comparison
	const f32 = Math.fround;
	for ( const frame of [ 100, 1e4, 1e6, 1e7 ] ) {
		const shift = f32( f32( frame ) * f32( 5.588238 ) ), coord = f32( f32( 1000.5 ) + shift );
		log( 'float32 IGN scroll at frame', frame, ': coordinate', coord, 'ulp', ( Math.fround( coord * ( 1 + 2 ** - 23 ) ) - coord ).toExponential( 2 ), 'pixels' );
	}
}

log( '\n== (e) unaligned windows and tile boundaries (seed 1, frame 0, 1024x1024; white baseline same size)' );
{
	const N = 1024, img = new Float64Array( N * N ), wht = new Float64Array( N * N );
	for ( let y = 0; y < N; y ++ ) for ( let x = 0; x < N; x ++ ) { img[ y * N + x ] = hsn( x, y, 0, 1 ); wht[ y * N + x ] = rnd(); }
	const windowStats = ( a, size, ox, oy ) => {
		const bins = size * size; let occ = 0, n = 0, minOcc = bins, m2 = 0;
		for ( let by = oy; by + size <= N; by += size ) for ( let bx = ox; bx + size <= N; bx += size ) {
			const seen = new Uint8Array( bins ); let k = 0, s = 0;
			for ( let j = 0; j < size; j ++ ) for ( let i = 0; i < size; i ++ ) { const v = a[ ( by + j ) * N + bx + i ]; s += v; const b = Math.floor( v * bins ); if ( ! seen[ b ] ) { seen[ b ] = 1; k ++; } }
			occ += k; minOcc = Math.min( minOcc, k ); m2 += ( s / bins - 0.5 ) ** 2; n ++;
		}
		return { bins, occupied: occ / n, minOccupied: minOcc, rms: Math.sqrt( m2 / n ) };
	};
	for ( const [ size, offs ] of [ [ 2, [ [ 0, 0 ], [ 1, 0 ], [ 1, 1 ] ] ], [ 4, [ [ 0, 0 ], [ 1, 1 ], [ 2, 2 ], [ 4, 4 ] ] ], [ 8, [ [ 0, 0 ], [ 1, 0 ], [ 1, 1 ], [ 2, 2 ], [ 4, 0 ], [ 4, 4 ] ] ] ] ) {
		const show = ( s ) => `occupied ${s.occupied.toFixed( 2 )}/${s.bins} (min ${s.minOccupied}), window-mean RMS error ${s.rms.toFixed( 5 )}`;
		const white = windowStats( wht, size, 0, 0 );
		for ( const [ ox, oy ] of offs ) { const s = windowStats( img, size, ox, oy ); json.windows.push( { size, offset: [ ox, oy ], ...s, whiteOccupied: white.occupied, whiteRms: white.rms } ); log( `${size}x${size} windows at offset (${ox},${oy}): ${SHORT} ${show( s )}` ); }
		log( `${size}x${size} windows: WHITE ${show( white )}` );
	}
	// neighbour differences (toroidal, in value) inside 2x2 blocks vs across block / tile boundaries
	const tor = ( d ) => { d = Math.abs( d ); return Math.min( d, 1 - d ); };
	const acc = {}; const add = ( k, v ) => { ( acc[ k ] = acc[ k ] || [ 0, 0, 1 ] ); acc[ k ][ 0 ] += v; acc[ k ][ 1 ] ++; acc[ k ][ 2 ] = Math.min( acc[ k ][ 2 ], v ); };
	for ( let y = 0; y < N; y ++ ) for ( let x = 0; x < N - 1; x ++ ) {
		const d = tor( img[ y * N + x ] - img[ y * N + x + 1 ] );
		add( ( x & 7 ) === 7 ? 'across 8x8 tile edge' : ( x & 3 ) === 3 ? 'across 4x4 edge (same tile)' : ( x & 1 ) === 1 ? 'across 2x2 edge (same 4x4)' : 'inside a 2x2 block', d );
		add( 'white', tor( wht[ y * N + x ] - wht[ y * N + x + 1 ] ) );
	}
	for ( const k in acc ) log( `horizontal neighbours ${k}: mean toroidal |dv| ${( acc[ k ][ 0 ] / acc[ k ][ 1 ] ).toFixed( 4 )}, min ${acc[ k ][ 2 ].toFixed( 4 )}` );
}

log( '\n== (g) relationship between two dimensions (seeds 117/118 = VXGI rotation/elevation), per aligned tile' );
{
	// 64 (u,v) pairs per tile: count occupied cells of a phase-aligned KxK grid; compare with a random pairing (Latin hypercube) and white
	const stats = { hsn: {}, lhs: {}, white: {} }; const tiles = 4096; json.dimensions = {};
	const put = ( o, k, v ) => { ( o[ k ] = o[ k ] || [] ).push( v ); };
	let corr = 0, n = 0;
	for ( let t = 0; t < tiles; t ++ ) {
		const tx = ( t % 64 ) * 8, ty = Math.floor( t / 64 ) * 8;
		const pu = hsnPhase( tx, ty, 117 ), pv = hsnPhase( tx, ty, 118 );
		const sets = { hsn: [], lhs: [], white: [] };
		const perm = [ ...Array( 64 ).keys() ]; for ( let i = 63; i > 0; i -- ) { const j = Math.floor( rnd() * ( i + 1 ) );[ perm[ i ], perm[ j ] ] = [ perm[ j ], perm[ i ] ]; }
		for ( let j = 0; j < 8; j ++ ) for ( let i = 0; i < 8; i ++ ) {
			const u = ( ( hsnBits( tx + i, ty + j, 0, 117 ) - pu ) >>> 0 ) / TWO32, v = ( ( hsnBits( tx + i, ty + j, 0, 118 ) - pv ) >>> 0 ) / TWO32;
			sets.hsn.push( [ u, v ] ); corr += ( u - 31.5 / 64 ) * ( v - 31.5 / 64 ); n ++;
			sets.lhs.push( [ ( j * 8 + i ) / 64, perm[ j * 8 + i ] / 64 ] ); sets.white.push( [ rnd(), rnd() ] );
		}
		for ( const name in sets ) for ( const K of [ 2, 4, 8 ] ) {
			const c = new Uint8Array( K * K ); sets[ name ].forEach( ( [ u, v ] ) => c[ Math.floor( u * K ) + K * Math.floor( v * K ) ] ++ );
			put( stats[ name ], 'occ' + K, c.filter( ( x ) => x > 0 ).length );
			put( stats[ name ], 'dev' + K, Math.sqrt( c.reduce( ( s, x ) => s + ( x - 64 / ( K * K ) ) ** 2, 0 ) / ( K * K ) ) );
		}
	}
	const mean = ( a ) => a.reduce( ( x, y ) => x + y ) / a.length;
	log( 'correlation coefficient of (u,v) ranks over', n, 'pixels:', ( corr / n / ( ( 64 * 64 - 1 ) / 12 / 4096 ) ).toFixed( 4 ) );
	for ( const name in stats ) json.dimensions[ name ] = Object.fromEntries( Object.entries( stats[ name ] ).map( ( [ k, v ] ) => [ k, mean( v ) ] ) );
	for ( const name in stats ) log( name.padEnd( 6 ), [ 2, 4, 8 ].map( ( K ) => `${K}x${K} grid: occupied ${mean( stats[ name ][ 'occ' + K ] ).toFixed( 2 )}/${K * K}, RMS count deviation ${mean( stats[ name ][ 'dev' + K ] ).toFixed( 2 )}` ).join( ' | ' ) );
	// inside one aligned 2x2 block: how many of the 4 (u,v) quadrants do the 4 pixels occupy?
	const q = [ 0, 0, 0, 0, 0 ];
	for ( let y = 0; y < 512; y += 2 ) for ( let x = 0; x < 512; x += 2 ) {
		const s = new Set(); for ( let j = 0; j < 2; j ++ ) for ( let i = 0; i < 2; i ++ ) s.add( ( hsnRank( x + i, y + j, 117 ) >>> 31 ) * 2 + ( hsnRank( x + i, y + j, 118 ) >>> 31 ) );
		q[ s.size ] ++;
	}
	log( '2x2 blocks by number of (u,v) quadrants occupied [0,1,2,3,4]:', q.join( ',' ) );
}

log( '\n== (h) per-pixel temporal 2D point sets: L2 star discrepancy of the first N (u,v) samples' );
{
	const l2star = ( p ) => { // Warnock
		const N = p.length; let a = 0, b = 0;
		for ( let i = 0; i < N; i ++ ) { a += ( 1 - p[ i ][ 0 ] ** 2 ) * ( 1 - p[ i ][ 1 ] ** 2 ); for ( let j = 0; j < N; j ++ ) b += ( 1 - Math.max( p[ i ][ 0 ], p[ j ][ 0 ] ) ) * ( 1 - Math.max( p[ i ][ 1 ], p[ j ][ 1 ] ) ); }
		return Math.sqrt( 1 / 9 - a / ( 2 * N ) + b / ( N * N ) );
	};
	const cases = { 'R2 steps': R2_STEPS, 'R4 steps [0],[1] (what VXGI uses)': [ R4_STEPS[ 0 ], R4_STEPS[ 1 ] ], 'R4 steps [2],[3]': [ R4_STEPS[ 2 ], R4_STEPS[ 3 ] ], 'R4 steps [0],[2] (SSR GGX x + march jitter)': [ R4_STEPS[ 0 ], R4_STEPS[ 2 ] ], 'shared golden step': [ GOLDEN_STEP, GOLDEN_STEP ] };
	for ( const N of [ 16, 64, 256, 1024 ] ) {
		const out = [], row = { N };
		for ( const name in cases ) {
			let s = 0; const P = 32;
			for ( let p = 0; p < P; p ++ ) { const pts = []; for ( let i = 0; i < N; i ++ ) pts.push( [ hsn( p * 3, p * 5, i, 117, cases[ name ][ 0 ] ), hsn( p * 3, p * 5, i, 118, cases[ name ][ 1 ] ) ] ); s += l2star( pts ); }
			out.push( `${name}: ${( s / P ).toFixed( 4 )}` ); row[ name ] = s / P;
		}
		let s = 0; for ( let p = 0; p < 32; p ++ ) { const pts = []; for ( let i = 0; i < N; i ++ ) pts.push( [ rnd(), rnd() ] ); s += l2star( pts ); }
		log( 'N=' + N, out.join( ' | ' ), '| white:', ( s / 32 ).toFixed( 4 ) ); row.white = s / 32; json.discrepancy.push( row );
	}
}

log( '\n== (f) output precision and range' );
{
	let mn = 1, mx = 0, bad = 0;
	for ( let i = 0; i < 2e6; i ++ ) { const v = hsn( i % 1920, ( i * 7 ) % 1080, i * 2654435761 >>> 0, i % 300 ); mn = Math.min( mn, v ); mx = Math.max( mx, v ); if ( Math.fround( v ) !== v || ! Number.isInteger( v * 16777216 ) ) bad ++; }
	log( 'min', mn, 'max', mx, '(largest representable output', ( 16777215 / 16777216 ), ') non-float32-exact or non-24-bit values:', bad );
	log( 'if all 32 bits were converted instead: fround(0xffffffff) / 2^32 =', Math.fround( 0xffffffff ) / TWO32, '(would reach 1.0)' );
}

mkdirSync( OUT, { recursive: true } );
writeFileSync( new URL( 'structure.txt', OUT ), lines.join( '\n' ) + '\n' );
writeFileSync( new URL( 'structure.json', OUT ), JSON.stringify( json, null, '\t' ) + '\n' );
