// "Analytic R4" and "What each part contributes" sections of the Results page (results/r4-ablation and results/gpu).
import { S, command, dataTable, figure, list, r } from './common.js';
import { realtime, LATTICES } from './data.js';
import g from './r4-readings.json';
import R4 from '../../results/r4-ablation/tables_R4.json';
import ABL from '../../results/r4-ablation/tables_ABL.json';

const fig = ( name, alt ) => figure( `r4-ablation/figures/${name}.webp`, alt );
const CPU = command( 'pnpm analysis:r4-ablation' );

document.getElementById( 'r4-body' ).innerHTML = `
	<p>Hash-free "analytic" samplers give every pixel a phase that is a linear function of its coordinates, then step it with the R4 (or R2) constants. The result has two halves, and both are shown. <strong>On the CPU flat-field test</strong> the per-value lattices have lower error than ${S}. <strong>But</strong> every hash-free version puts 6–18% of a threshold mask's spectral power in a single bin (${S}: about 0.09%), and <strong>in the engine</strong> the lattice variants are worse than ${S} and the plain hash on most measures, with structured error over time. The CPU row (ii) and the in-engine variant F use different direction pairs; rows E and F on the CPU use exactly the in-engine definitions, so compare those like for like.</p>

	<h3>CPU: definitions</h3>
	${CPU}
	${list( g.definitions )}
	<p>${r( g.spectrum_note )}</p>
	${list( g.addendum )}

	<h3>CPU: four values per pixel</h3>
	${fig( 'r4_ema_spatial', 'Error left after temporal accumulation and a spatial filter, analytic R4 comparison' )}
	${dataTable( R4[ 2 ] )}
	${dataTable( R4[ 0 ] )}
	${dataTable( R4[ 5 ] )}
	${fig( 'r4_swatches', 'Threshold masks and spectra of the analytic samplers' )}
	${fig( 'r4_convergence', 'Per-pixel convergence of the analytic samplers' )}

	<h3>CPU: two values per pixel</h3>
	${dataTable( R4[ 8 ] )}
	${dataTable( R4[ 11 ] )}
	<p class="caption">The 3×3 box and Gaussian σ = 2 tables and the ratios against ${S} are in <code>results/r4-ablation/tables_R4.md</code>.</p>

	<h3>CPU: reading</h3>
	${list( g.reading1 )}

	<h3>In-engine: variants E (single lattice), F (per-value lattices) and G (the 32×32-tile analytic R4 of three.js fork PR #42)</h3>
	${command( 'pnpm analysis:gpu' )}
	${list( g.engine_definitions )}
	<p><strong>G</strong> is the <code>RNoise.js</code> of bhouston/three.js#42 used verbatim (<code>analysis/gpu/harness/MeasureRNoiseR4.js</code>): an R2 tile shift of a 32×32 pattern, <code>t = c.x + 32·c.y + seed</code>, <code>fract( t / P^k + 0.5 )</code> with P = 1.1673039782614187, all in float.</p>
	<p class="caption">VXGI, real time: mean ± SD over three runs, ×10⁻³, change against "Before".</p>
	${realtime( 'vxgi', 2, 3, LATTICES )}
	<p>${r( g.engine_e_note )}</p>
	<p class="caption">SSR, denoised.</p>
	${realtime( 'ssr', 3, 3, LATTICES )}
	<p>${r( g.engine_fps_ef )} For G: ${r( g.engine_fps[ 0 ] )}</p>

	<h3>In-engine: structure in the crops</h3>
	<p>See the variants figure under <a href="#engine">In-engine</a>.</p>
	${list( [ ...g.engine_structure, ...g.engine_g_structure.map( ( x ) => x.replace( '**', '**G, ' ) ) ] )}

	<h3>In-engine: verdict for E and F</h3>
	${list( g.engine_ef_verdict )}

	<h3>In-engine: verdict for G</h3>
	${list( g.engine_verdict )}

	<h3>CPU against in-engine, like for like (E and F)</h3>
	${list( g.likeforlike )}

	<h3>Caveats</h3>
	${list( g.caveats )}
`;

document.getElementById( 'ablation-body' ).innerHTML = `
	<p>A single-factor ablation on the CPU harness: each part of ${S} is switched off in turn and the same metrics are measured. The ratio is without ÷ with: above 1 means the part helps on that metric, below 1 means it costs.</p>
	${CPU}
	${list( g.ablation_definitions )}

	<h3>Summary: component, purpose, metric, with and without</h3>
	${dataTable( ABL[ 0 ], { caption: false } )}
	${list( g.reading2 )}

	${fig( 'ablation_metrics', 'Ablation metrics by variant' )}
	${fig( 'ablation_swatches', 'Threshold masks and spectra of each ablation variant' )}
	<p class="caption">The tiled-Bayer spectrum is a few isolated peaks, so it renders black.</p>

	<h3>Per-variant tables</h3>
	${dataTable( ABL[ 1 ] )}${dataTable( ABL[ 2 ] )}${dataTable( ABL[ 3 ] )}${dataTable( ABL[ 4 ] )}
`;
