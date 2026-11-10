// Self-check: `npm test` (node --test, no dependencies).
//
// hsn-vectors.json was generated from the verified reference (the operation-for-operation
// transliteration of three.js PR #35429, which also equals the CPU model that matched GPU output).
// python-vectors.json is written by `python analysis/spatial/noises.py vectors` so the JavaScript
// modules and the numpy implementations used by the spatial analysis are checked against each other.

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as N from './index.js';

const load = ( name ) => JSON.parse( readFileSync( new URL( name, import.meta.url ) ) );

test( 'HSN reference is bit-exact against the stored test vectors', () => {

	const { cases } = load( './hsn-vectors.json' );
	assert.equal( cases.length, 1024 );

	for ( const [ x, y, index, seed, step, bits ] of cases ) {

		assert.equal( N.hsnBits( x, y, index, seed, step ), bits, `hsnBits(${[ x, y, index, seed, step ]})` );
		assert.equal( N.hsn( x, y, index, seed, step ), ( bits >>> 8 ) / 16777216 );

	}

	assert.deepEqual( N.hsn4( 3, 5, 7, 47 ), [ 0.6187723875045776, 0.6986466646194458, 0.30214303731918335, 0.8490200638771057 ] );

} );

test( 'HSN: every aligned 2x2 / 4x4 / 8x8 block holds each leading rank exactly once, on every frame', () => {

	for ( const seed of [ 0, 1, 2, 117, 189, 240, 0xdeadbeef ] ) for ( const frame of [ 0, 1, 12345 ] ) for ( let k = 1; k <= 3; k ++ ) {

		const size = 1 << k;

		for ( let by = 0; by < 256; by += size ) for ( let bx = 0; bx < 256; bx += size ) {

			const seen = new Uint8Array( size * size );
			const phase = N.hsnPhase( bx, by, seed ), time = Math.imul( frame, N.GOLDEN_STEP ) >>> 0;

			for ( let j = 0; j < size; j ++ ) for ( let i = 0; i < size; i ++ ) {

				// remove the tile phase and the time offset, then read the top 2k bits
				const bits = ( N.hsnBits( bx + i, by + j, frame, seed ) - phase - time ) >>> 0;
				assert.equal( bits, N.hsnRank( bx + i, by + j, seed ) );
				seen[ bits >>> ( 32 - 2 * k ) ] ++;

			}

			assert.ok( seen.every( ( n ) => n === 1 ), `block ${size} at ${bx},${by} seed ${seed}` );

		}

	}

} );

test( 'HSN: an aligned 8x8 tile holds 64 values exactly 1/64 apart, one per fixed 1/64 bin', () => {

	for ( const frame of [ 0, 1, 77, 4000000000 ] ) for ( let ty = 0; ty < 256; ty += 8 ) for ( let tx = 0; tx < 256; tx += 8 ) {

		const v = [];
		for ( let j = 0; j < 8; j ++ ) for ( let i = 0; i < 8; i ++ ) v.push( N.hsn( tx + i, ty + j, frame, 1 ) * 16777216 );
		v.sort( ( a, b ) => a - b );
		assert.ok( v.every( ( x, i ) => Math.floor( x / 262144 ) === i && ( i === 0 || x - v[ i - 1 ] === 262144 ) ) );

	}

} );

test( 'HSN output is a 24-bit float in [0, 1)', () => {

	for ( let i = 0; i < 100000; i ++ ) {

		const v = N.hsn( i * 7919 % 4096, i * 104729 % 4096, i, i % 251 );
		assert.ok( v >= 0 && v < 1 && Number.isInteger( v * 16777216 ) && Math.fround( v ) === v );

	}

} );

test( 'Bayer 8x8 is the standard matrix', () => {

	const table = [ [ 0, 32, 8, 40, 2, 34, 10, 42 ], [ 48, 16, 56, 24, 50, 18, 58, 26 ], [ 12, 44, 4, 36, 14, 46, 6, 38 ], [ 60, 28, 52, 20, 62, 30, 54, 22 ],
		[ 3, 35, 11, 43, 1, 33, 9, 41 ], [ 51, 19, 59, 27, 49, 17, 57, 25 ], [ 15, 47, 7, 39, 13, 45, 5, 37 ], [ 63, 31, 55, 23, 61, 29, 53, 21 ] ];
	for ( let y = 0; y < 16; y ++ ) for ( let x = 0; x < 16; x ++ ) assert.equal( N.bayerIndex( x, y ), table[ y % 8 ][ x % 8 ] );

} );

test( 'other noises match the numpy implementations used by the spatial analysis', () => {

	const p = load( './python-vectors.json' );
	let sinMatches = 0;

	p.x.forEach( ( x, k ) => {

		const y = p.y[ k ];
		// integer and float32 arithmetic: exact
		assert.equal( N.whitePcg( x, y, 0, 3 ), p.whitePcg[ k ] );
		assert.equal( N.whiteHsnHash( x, y, 0, 3 ), p.whiteHsnHash[ k ] );
		assert.equal( N.hash12( x, y ), p.hash12[ k ] );
		assert.equal( N.ign( x, y ), p.ign[ k ] );
		assert.equal( N.bayer( x, y ), p.bayer[ k ] );
		[ 0, 1, 7 ].forEach( ( index, i ) => { for ( let ch = 0; ch < 4; ch ++ ) assert.equal( N.threejsAnalytic( x, y, index, 47, ch ), p.threejsAnalytic[ i ][ ch ][ k ], `threejsAnalytic index ${index} channel ${ch}` ); } );
		// float64: equal to rounding
		assert.ok( Math.abs( N.r2( x, y ) - p.r2[ k ] ) < 1e-9 );
		// fract(sin) amplifies the last bit of the platform's sin(), so it is only expected to agree mostly
		if ( N.sinHash( x, y ) === p.sinHash[ k ] ) sinMatches ++;

	} );

	assert.ok( sinMatches >= 32, `fract(sin) hash agrees with numpy on only ${sinMatches} of 64 points` );

} );

test( 'multi-value noises match the implementations measured by the temporal analysis', () => {

	// written by `pnpm py analysis/temporal/extras.py vectors`
	const p = load( './temporal-vectors.json' );

	for ( const D of [ 1, 2, 4 ] ) p.x.forEach( ( x, k ) => {

		const y = p.y[ k ], n = p.index[ k ], steps = N.stepsFor( D );

		for ( let d = 0; d < D; d ++ ) {

			const at = `D=${D} d=${d} x=${x} y=${y} index=${n}`;
			assert.equal( N.hsn( x, y, n, d + 1, steps[ d ] ), p.hsn[ D ][ d ][ k ], `hsn ${at}` );
			assert.equal( N.hashRd( x, y, n, d, steps[ d ] ), p.hashRd[ D ][ d ][ k ], `hashRd ${at}` );
			assert.equal( N.ignRd( x, y, n, d, steps[ d ] ), p.ignRd[ D ][ d ][ k ], `ignRd ${at}` );
			assert.equal( N.vcRd( x, y, n, d, N.RD_ALPHAS[ D ][ d ] ), p.vcRd[ D ][ d ][ k ], `vcRd ${at}` );
			assert.equal( N.animatedIgn( x, y, n, d ), p.animatedIgn[ D ][ d ][ k ], `animatedIgn ${at}` );
			assert.equal( N.white( x, y, n, d ), p.white[ D ][ d ][ k ], `white ${at}` );

		}

	} );

	assert.deepEqual( [ ...N.VC64 ].sort( ( a, b ) => a - b ), Array.from( { length: 4096 }, ( _, i ) => i ) );

} );

test( 'analytic lattice samplers match the implementations in analysis/r4-ablation', () => {

	// written by `pnpm py analysis/r4-ablation/run.py vectors`
	const p = load( './r4-vectors.json' );

	for ( const D of [ 2, 4 ] ) p.x.forEach( ( x, k ) => {

		const y = p.y[ k ], n = p.index[ k ];

		for ( let d = 0; d < D; d ++ ) {

			const at = `D=${D} d=${d} x=${x} y=${y} index=${n}`;
			assert.equal( N.analyticR4Tile( x, y, n, d ), p.pr42[ D ][ d ][ k ], `analyticR4Tile ${at}` );
			assert.equal( N.analyticSingleLattice( x, y, n, N.RD_ALPHAS[ D ][ d ] ), p.single[ D ][ d ][ k ], `analyticSingleLattice ${at}` );
			assert.equal( N.analyticPerDimensionLattices( x, y, n, d, N.stepsFor( D )[ d ] ), p.perDimension[ D ][ d ][ k ], `analyticPerDimensionLattices ${at}` );
			assert.equal( N.engineSingleLattice( x, y, n, N.RD_ALPHAS[ D ][ d ], D === 4 ? 47 : 29 ), p.engineE[ D ][ d ][ k ], `engineSingleLattice ${at}` );
			assert.equal( N.engineLattices( x, y, n, d, N.RD_ALPHAS[ D ][ d ] ), p.engineF[ D ][ d ][ k ], `engineLattices ${at}` );

		}

	} );

} );

test( 'accumulation ramps up as a running mean, then becomes an EMA', () => {

	const alpha = 0.1, values = Array.from( { length: 400 }, ( _, i ) => N.white( 3, 5, i ) );
	const run = ( count ) => values.slice( 0, count ).reduce( ( history, v, i ) => N.accumulate( history, v, i + 1, alpha ), 123 ); // the initial value must not matter

	// after 5 frames (and up to 1 / alpha): exactly the mean of the inputs
	for ( const count of [ 1, 5, 10 ] ) assert.ok( Math.abs( run( count ) - values.slice( 0, count ).reduce( ( a, b ) => a + b ) / count ) < 1e-12 );

	// after many frames: a plain EMA, whatever it was seeded with
	const ema = values.reduce( ( history, v ) => history + alpha * ( v - history ), values[ 0 ] );
	assert.ok( Math.abs( run( 400 ) - ema ) < 1e-9 );
	assert.equal( N.historyWeight( 1, alpha ), 1 );
	assert.equal( N.historyWeight( 50, alpha ), alpha );

} );

test( 'step constants', () => {

	const all = [ N.GOLDEN_STEP, ...N.R2_STEPS, ...N.R4_STEPS, ...N.TRADEOFF_R4_STEPS ];
	assert.ok( all.every( ( s ) => s % 2 === 1 && s > 0 && s < 2 ** 32 ) ); // odd, so the u32 state has period 2^32
	for ( const D of [ 1, 2, 4 ] ) N.stepsFor( D ).forEach( ( s, d ) => assert.ok( Math.abs( s - N.RD_ALPHAS[ D ][ d ] * 2 ** 32 ) <= 2 ) );
	assert.deepEqual( N.stepsFor( 4 ), N.R4_STEPS ); // the trade-off candidate is never the default

} );

test( 'every registered noise stays in [0, 1)', () => {

	for ( const { id, fn, multi } of N.NOISES ) for ( let i = 0; i < 20000; i ++ ) {

		const D = multi ? [ 1, 2, 4 ][ i % 3 ] : 1, d = i % D;
		const v = fn( i * 37 % 2300, i * 91 % 2300, i % 300, i % 8, d, N.stepsFor( D ) );
		assert.ok( v >= 0 && v < 1, `${id} returned ${v}` );

	}

} );
