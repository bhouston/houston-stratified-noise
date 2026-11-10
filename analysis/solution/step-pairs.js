// 2D projections of the R2 / R4 steps: per-pixel L2 star discrepancy of the first N samples, and the
// strongest small-integer near-relation p*a_i + q*a_j ~ integer. Run: node analysis/solution/step-pairs.js
// Writes results/solution/step-pairs.json.
import { mkdirSync, writeFileSync } from 'node:fs';
import { hsn, R2_STEPS, R4_STEPS } from '../../src/noise/index.js';
const rows = [];
const l2 = ( p ) => { const N = p.length; let a = 0, b = 0; for ( let i = 0; i < N; i ++ ) { a += ( 1 - p[ i ][ 0 ] ** 2 ) * ( 1 - p[ i ][ 1 ] ** 2 ); for ( let j = 0; j < N; j ++ ) b += ( 1 - Math.max( p[ i ][ 0 ], p[ j ][ 0 ] ) ) * ( 1 - Math.max( p[ i ][ 1 ], p[ j ][ 1 ] ) ); } return Math.sqrt( 1 / 9 - a / ( 2 * N ) + b / ( N * N ) ); };
const run = ( name, s0, s1 ) => {
	const row = [ 64, 256, 1024 ].map( ( N ) => { let s = 0; for ( let p = 0; p < 16; p ++ ) { const pts = []; for ( let i = 0; i < N; i ++ ) pts.push( [ hsn( p * 3, p * 5, i, 117, s0 ), hsn( p * 3, p * 5, i, 118, s1 ) ] ); s += l2( pts ); } return ( s / 16 ).toFixed( 4 ); } );
	let best = [ 1 ]; const a = s0 / 2 ** 32, b = s1 / 2 ** 32;
	for ( let p = - 12; p <= 12; p ++ ) for ( let q = 0; q <= 12; q ++ ) { if ( ! p && ! q ) continue; const v = p * a + q * b, e = Math.abs( v - Math.round( v ) ) * Math.max( Math.abs( p ), 1 ) * Math.max( q, 1 ); if ( e < best[ 0 ] ) best = [ e, p, q, Math.abs( v - Math.round( v ) ) ]; }
	rows.push( { steps: name, l2star: { 64: + row[ 0 ], 256: + row[ 1 ], 1024: + row[ 2 ] }, resonance: { p: best[ 1 ], q: best[ 2 ], error: best[ 3 ] } } );
	console.log( name.padEnd( 10 ), 'L2* N=64/256/1024:', row.join( ' ' ), '| worst resonance p,q =', best[ 1 ], best[ 2 ], '|p a+q b - int| =', best[ 3 ].toExponential( 2 ) );
};
run( 'R2', ...R2_STEPS );
for ( let i = 0; i < 4; i ++ ) for ( let j = i + 1; j < 4; j ++ ) run( `R4[${i}],[${j}]`, R4_STEPS[ i ], R4_STEPS[ j ] );
const out = new URL( '../../results/solution/', import.meta.url );
mkdirSync( out, { recursive: true } );
writeFileSync( new URL( 'step-pairs.json', out ), JSON.stringify( rows, null, '\t' ) + '\n' );
