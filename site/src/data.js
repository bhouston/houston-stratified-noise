// Tables built from the committed results JSON, shared by the Overview and Results pages.
import { S, dataTable } from './common.js';
import rt from '../../results/gpu/realtime_metrics.json';
import bake from '../../results/gpu/bake_metrics.json';
import sensitivity from '../../results/gpu/bake_sensitivity.json';

export { rt };

// ---- temporal analysis (results/temporal/tables_*.json)

export const tables = import.meta.glob( '../../results/temporal/tables_*.json', { eager: true, import: 'default' } );
export const T = ( section, index, options ) => dataTable( T.raw( section, index ), options );
T.raw = ( section, index ) => tables[ `../../results/temporal/tables_${section}.json` ][ index ];
// Headline: EMA 0.1 + Gaussian sigma 1 by values per pixel, read out of the three generated tables.
const methods = [ [ S, `${S} (` ], [ 'FAST', 'FAST' ], [ 'STBN', 'STBN' ], [ 'V&C + R_d (shared golden for one value)', 'V&C' ], [ 'Animated IGN', 'Animated IGN (+' ], [ 'Hash + R_d (float time)', 'R_d Weyl + white' ], [ 'White', 'White' ] ];
const emaTables = [ 0, 2, 3 ].map( ( i ) => T.raw( 'D', i ) );
const column = ( t ) => t.head.indexOf( 'Gauss s=1' );
const pick = ( t, prefix ) => ( t.rows.filter( ( row ) => row[ 0 ].startsWith( prefix ) ).pop() || [] )[ column( t ) ] ?? '–'; // the last match is the R_d-step variant where both exist
export const headline = { title: '', head: [ 'Values per pixel', ...methods.map( ( m ) => m[ 0 ] ) ], rows: [ 1, 2, 4 ].map( ( D, i ) => [ String( D ), ...methods.map( ( m ) => pick( emaTables[ i ], m[ 1 ] ) ) ] ) };


// ---- in-engine measurements (results/gpu)

const NAMES = { base: 'Before', hhw: `${S} (pull request head)`, hash: 'A: Hash + R_d', ign: 'B: IGN + R_d', hhwr2: `C: ${S}, R2 steps`, vc: 'D: Void-and-cluster + R_d',
	e: 'E: single lattice, R4 constants', er2: 'E: single lattice, R2 constants', f: 'F: per-value lattices, R4 steps', fr2: 'F: per-value lattices, R2 steps', g: 'G: analytic R4, 32×32 tile (fork PR #42)' };
export const MAIN = [ 'base', 'hhw', 'hash', 'ign', 'hhwr2', 'vc' ], LATTICES = [ 'base', 'hhw', 'hash', 'e', 'er2', 'f', 'fr2', 'g' ];
const BEFORE = { vxgi: 'Before (IGN pair)', ssr: 'Before (analytic R2)', ssr_only: 'Before (analytic R2)' };
const pct = ( v, base ) => `${v >= base ? '+' : '−'}${Math.abs( ( v / base - 1 ) * 100 ).toFixed( 1 )}%`;

// mean ± SD over the runs, x 1e-3, with the change against "Before"
export function realtime( fx, digits, flickerDigits = digits, variants = MAIN ) {

	const d = rt[ fx ], base = d.variants.base, keys = [ 'rmse', 'bias', 'bias_corrected', 'noise', 'flicker' ];
	const control = d.fps_hhw_control_in_vc_session;

	const lattices = variants === LATTICES, relative = d.fps_relative_to_hsn_control || {};
	const rows = variants.filter( ( v ) => d.variants[ v ] ).map( ( v ) => {

		const s = d.variants[ v ];
		const cells = keys.map( ( k ) => {

			const n = k === 'flicker' ? flickerDigits : digits, value = ( s.mean[ k ] * 1e3 ).toFixed( n );
			const sd = k === 'bias_corrected' ? '' : ` ± ${( s.sd[ k ] * 1e3 ).toFixed( n )}`;
			return v === 'base' ? value + sd : `${value}${sd} (${pct( s.mean[ k ], base.mean[ k ] )})`;

		} );
		// D was measured in a later, busier session, so its fps is only comparable with the control measured alongside it
		// later sessions shared the GPU, so those variants are given only relative to the control measured in the same round
		const fps = lattices ? [ v === 'g' ? 'not resolved' : v === 'hhw' ? '1.00' : relative[ v ] ? relative[ v ].median_ratio.toFixed( 2 ) : v === 'hash' && relative.hashctl2 ? relative.hashctl2.median_ratio.toFixed( 2 ) : '—' ]
			: ! s.fps ? [] : [ v === 'vc' && control ? `${pct( s.fps.median, control.median )} against the ${S} control of its session (${s.fps.median.toFixed( 1 )} vs ${control.median.toFixed( 1 )})` : `${s.fps.median.toFixed( 1 )} (${s.fps.min.toFixed( 1 )}–${s.fps.max.toFixed( 1 )})` ];
		return [ v === 'base' ? BEFORE[ fx ] : NAMES[ v ], ...cells, ...fps ];

	} );

	const hasFps = !! base.fps;
	if ( ! lattices ) rows.push( [ 'White noise (for scale)', '—', '—', '—', ( d.white.noise * 1e3 ).toFixed( digits ), ( d.white.flicker * 1e3 ).toFixed( flickerDigits ), ...( hasFps ? [ '—' ] : [] ) ] );
	return dataTable( { head: [ 'Sampler', 'RMSE', 'Bias', 'Bias, corrected', 'Temporal noise', 'Flicker', ...( hasFps ? [ lattices ? `fps ÷ ${S} control of the same round` : 'fps at 1080p, median (range)' ] : [] ) ], rows } );

}

const B = bake.samplers, prev = B.prev.mean;
const bakeRow = ( name, key ) => [ name, ...[ 'rmse', 'grain', 'bias', 'grain_noref' ].map( ( k ) => key === 'prev' ? B[ key ].mean[ k ].toFixed( 4 ) : `${B[ key ].mean[ k ].toFixed( 4 )} (${( B[ key ].mean[ k ] / prev[ k ] ).toFixed( 2 )}×, ${pct( B[ key ].mean[ k ], prev[ k ] )})` ) ];
export const bakeTable = dataTable( { head: [ 'Sampler', 'RMSE', 'Grain (high-pass error)', 'Bias (low-pass error)', 'Grain, reference-free' ],
	rows: [ bakeRow( '(a) Previous, IGN pair', 'prev' ), bakeRow( `(b) ${S}, shared golden step`, 'shared' ), bakeRow( `(c) ${S}, R2 steps`, 'r2' ) ] } );

export const sensitivityTable = dataTable( { head: [ 'Grain definition', 'Shared golden step ÷ previous', 'R2 steps ÷ previous' ],
	rows: Object.entries( sensitivity ).map( ( [ name, v ] ) => [ name.replace( 'absolute', 'Absolute high-pass grain,' ).replace( 'relative', 'Relative, reference-free grain,' ).replace( 'sigma=', 'σ = ' ), v.shared_over_prev.toFixed( 2 ) + '×', v.r2_over_prev.toFixed( 2 ) + '×' ] ) } );

