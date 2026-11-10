// Temporal and step-constant sections of the Results page, rendered from results/temporal and results/steps.
import { S, command, dataTable, figure, list } from './common.js';
import { T } from './data.js';
import readings from './temporal-readings.json';
import stepReadings from './steps-readings.json';
import steps from '../../results/steps/tables_steps.json';

const fig = ( name, alt ) => figure( `temporal/figures/${name}.webp`, alt );
const reading = ( key ) => list( readings[ Object.keys( readings ).find( ( k ) => k.startsWith( key ) ) ] );
const TEMPORAL = command( 'pnpm analysis:temporal' );

const section = ( id, title, body ) => `<h3 id="${id}">${title}</h3>${body}`;

document.getElementById( 'temporal-body' ).innerHTML = `
	<p>Terms: <strong>1-value, 2-value and 4-value</strong> mean one, two or four values per pixel, each from its own seed and step; <strong>N</strong> is always the number of frames accumulated, with one sample of each value per pixel per frame.</p>
	<p>Per-pixel convergence over frames accumulated, the quality of each pixel's set of values over time, exponential moving averages and short windows with spatial filters, flicker, the temporal spectrum, long-run robustness, and the step constants. All errors are RMSE ×1000. Everything is a numpy model of the shader arithmetic; nothing in this section was rendered on a GPU.</p>
	${TEMPORAL}

	<h3>Headline numbers</h3>
	${list( readings[ 'Headline numbers' ] )}

	<h3>Most surprising findings, mostly unfavourable</h3>
	${list( readings[ 'Most surprising findings, mostly unfavourable' ], 'ol' )}

	<h3>Methods as implemented</h3>
	${list( readings[ 'Methods as implemented' ] )}
	<h3>Integrands</h3>
	${list( readings.Integrands )}

	${section( 'A', 'A. Per-pixel convergence, one value', fig( 'A_convergence_1d', 'Per-pixel temporal convergence, one dimension' ) + T( 'AB', 1 ) + reading( 'A.' ) )}

	${section( 'B', 'B. Per-pixel convergence, two and four values', fig( 'B_convergence_2d_4d', 'Per-pixel temporal convergence, two and four dimensions' ) + T( 'AB', 7 ) + T( 'AB', 11 ) + reading( 'B.' )
		+ fig( 'lockstep', 'One pixel\'s 256 samples of two dimensions with a shared step and with separate R2 steps' ) + fig( 'lockstep_four', 'One pixel\'s 256 two-dimensional samples for four samplers' ) )}

	${section( 'C', 'C. Sample-set quality', fig( 'C_scatter_2d', 'One pixel\'s first 16, 64 and 256 two-dimensional samples' ) + fig( 'C_discrepancy', 'Discrepancy of one pixel\'s sample set over time' ) + T( 'C', 0 ) + T( 'C', 1 ) + T( 'C', 2 ) + reading( 'C.' ) )}

	${section( 'D', 'D. EMA and N-frame windows with spatial filters', fig( 'D_ema_spatial', 'Error left after temporal accumulation and a spatial filter' ) + T( 'D', 0 ) + T( 'D', 2 ) + T( 'D', 3 )
		+ fig( 'D_box_windows', 'Short temporal windows: N-frame average, then a spatial filter' ) + T( 'D', 12 ) + T( 'D', 16 ) + reading( 'D.' ) )}

	${section( 'E', 'E. Temporal stability: flicker and the temporal spectrum', fig( 'E_flicker_vs_error', 'Flicker against error under EMA + Gaussian sigma 1' ) + T( 'D', 20 ) + T( 'D', 22 )
		+ fig( 'E_temporal_spectrum', 'Where each pixel\'s noise sits in temporal frequency' ) + T( 'E', 0 ) + reading( 'E.' ) )}

	${section( 'F', 'F. Spatial quality over time', fig( 'F_frames_and_residual', 'The pattern on consecutive frames and what is left after averaging' ) + T( 'F', 0 ) + T( 'F', 2 ) + reading( 'F.' ) )}

	${section( 'G', 'G. Long-run robustness', fig( 'G_long_run', 'Error of a 64-frame average started at frame n0' ) + T( 'G', 0 ) + T( 'G', 2 ) + reading( 'G.' ) )}

	${section( 'H', 'H. Pairwise independence of four values', fig( 'H_pairs_4d', 'Pairwise projections of one pixel\'s 256 four-dimensional samples' ) + T( 'C', 4 ) + T( 'C', 3 ) + reading( 'H.' ) )}

	${section( 'X1', 'Pairing two dimensions inside a tile by bit reversal', T( 'X1', 0 ) + T( 'X1', 1 ) + T( 'X1', 5 ) + reading( 'X1.' ) )}

	${section( 'X3', 'Step constants as Three.js uses them', fig( 'X3_steps_1d', 'Each temporal step as a one-dimensional sequence' ) + T( 'X3', 0 ) + fig( 'X3_step_pairs_scatter', 'One pixel\'s two-dimensional samples for each pair of steps' ) + T( 'X3', 1 ) + T( 'X3', 2 ) + reading( 'X3.' ) )}

	${section( 'X4', `Is the hierarchy needed? ${S} against hash + R_d (A) and IGN + R_d (B)`, T( 'X4', 5 ) + T( 'X4', 9 ) + T( 'X4', 11 ) + T( 'X4', 17 ) + reading( 'X4.' ) )}

	${section( 'X5', 'Step and hierarchy resonance', T( 'X5', 0 ) + reading( 'X5.' ) )}

	<h3>Plain-language conclusions</h3>
	${list( readings[ 'Plain-language conclusions' ] )}

	<h3>Caveats and gaps</h3>
	${list( readings[ 'Caveats and gaps' ] )}
`;

// ---- step search (analysis/steps)

const S4 = steps.filter( ( t ) => t.heading.startsWith( '4 value' ) );
const byTitle = ( list, start ) => list.find( ( t ) => t.title.includes( start ) );

document.getElementById( 'steps-body' ).innerHTML = `
	<p>A bounded search for better temporal step constants, with the selection rule fixed before any measurement and a validation on held-out integrands. It uses the same harness as the temporal analysis. Full tables, including every ranking, are in <code>results/steps/tables_steps.md</code>.</p>
	${command( 'pnpm analysis:steps' )}

	<h3>Verdict</h3>
	${dataTable( { head: [ 'Values per pixel', 'Verdict', 'Constants' ], rows: [
		[ '1', 'Keep the golden step', '<code>2654435769</code>' ],
		[ '2', 'Keep <code>R2_STEPS</code>', '<code>[3242174889, 2447445413]</code>' ],
		[ '4', 'Keep <code>R4_STEPS</code> by the stated bar; a real trade-off candidate exists', 'candidate <code>TRADEOFF_R4_STEPS = [3280154747, 2481977421, 1303403687, 2746543331]</code> in <code>src/noise/steps.js</code>, optional and not the default' ]
	] } )}
	${list( stepReadings.verdict )}

	<h3>What was done</h3>
	${list( stepReadings[ 'What was done' ] )}

	<h3>Findings</h3>
	${list( stepReadings.Findings, 'ol' )}

	<h3>Four values: the candidate against <code>R4_STEPS</code> on held-out integrands</h3>
	${figure( 'steps/figures/pairs_4d_current_vs_candidate.webp', 'Pairwise projections of one pixel\'s 256 four-dimensional samples, current and candidate steps' )}
	${dataTable( byTitle( S4, 'Held-out integrands' ) )}
	${dataTable( byTitle( S4, 'Pairwise temporal chi-square' ) )}

	<h3>The candidate's first two steps as a two-value pair</h3>
	${dataTable( steps.find( ( t ) => t.heading.startsWith( 'Supplementary' ) ) )}

	<h3>Not tested</h3>
	${list( stepReadings[ 'Not tested' ] )}
`;
