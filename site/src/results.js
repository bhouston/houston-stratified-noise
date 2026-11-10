import { S, command, figure, list, r, table } from './common.js';
import './results-temporal.js';
import './results-gpu.js';
import './results-r4.js';
import { T, headline, realtime, bakeTable } from './data.js';
import { dataTable } from './common.js';
import spatial from '../../results/spatial/tables.json';
import structure from '../../results/solution/structure.json';
import pairs from '../../results/solution/step-pairs.json';
import readings from './spatial-readings.json';


// ---- structure (analysis/solution)

const SOLUTION = command( 'pnpm analysis:solution' );
const f = ( v, d ) => v.toFixed( d );

const windows = {
	head: [ 'Offset', 'Distinct bins occupied', 'Window-mean RMS error', 'White: bins occupied', 'White: RMS error' ],
	rows: structure.windows.map( ( w ) => [ `${w.size}×${w.size}`, `(${w.offset})`, `${f( w.occupied, 2 )} / ${w.bins}`, f( w.rms, 4 ), `${f( w.whiteOccupied, 2 )} / ${w.bins}`, f( w.whiteRms, 4 ) ] )
};

const columns = Object.keys( structure.discrepancy[ 0 ] ).filter( ( k ) => k !== 'N' );
const discrepancy = {
	head: structure.discrepancy.map( ( d ) => `N=${d.N}` ),
	rows: columns.map( ( c ) => [ c === 'white' ? 'White noise' : c, ...structure.discrepancy.map( ( d ) => f( d[ c ], 4 ) ) ] )
};

const stepPairs = {
	head: [ 'N=64', 'N=256', 'N=1024', 'Strongest near-relation p·α₀ + q·α₁ ≈ integer (p, q)', 'Distance from integer' ],
	rows: pairs.map( ( p ) => [ p.steps, f( p.l2star[ 64 ], 4 ), f( p.l2star[ 256 ], 4 ), f( p.l2star[ 1024 ], 4 ), `${p.resonance.p}, ${p.resonance.q}`, p.resonance.error.toExponential( 2 ) ] )
};

const dims = structure.dimensions;
const dimensions = {
	head: [ 'Quadrant-count RMS deviation (ideal 16 each)', '4×4 grid deviation', '8×8 grid cells occupied (of 64)' ],
	rows: [ [ S, dims.hsn ], [ 'Random Latin-hypercube pairing', dims.lhs ], [ 'White noise', dims.white ] ].map( ( [ name, d ] ) => [ name, f( d.dev2, 2 ), f( d.dev4, 2 ), f( d.occ8, 2 ) ] )
};

document.getElementById( 'structure-body' ).innerHTML = `
	<p>Checks of what the construction guarantees, run on the plain-JavaScript reference. The full printed output is <code>results/solution/structure.txt</code>; the algorithm diagrams on the <a href="./">Overview</a> page come from the same command.</p>
	${SOLUTION}

	<h4>Aligned and unaligned windows</h4>
	${table( windows ).replace( '<th>Method</th>', '<th>Window</th>' )}
	<p>Guarantees hold only for windows aligned to the 2, 4 and 8 pixel grid. A 2×2 window shifted diagonally by one pixel is statistically white. Larger unaligned windows degrade gracefully because they still contain whole aligned sub-blocks: an 8×8 window at any offset tested has a mean 1.8 to 8 times more accurate than white noise. A 4×4 window at offset (4,4) is aligned again.</p>

	<h4>Two dimensions within a tile</h4>
	${table( dimensions ).replace( '<th>Method</th>', '<th>64 (u,v) pairs per aligned tile</th>' )}
	<p>Using two seeds over 4,096 tiles, each tile's 64 (u,v) pairs have perfect 1D marginals in both dimensions, but their joint 2D distribution is no better than white noise. Dimensions are independent, not jointly stratified; the joint quality of multi-dimensional samples comes from the temporal steps, not from space.</p>

	<h4>Per-pixel 2D point sets over time, by step pair</h4>
	<p>L2 star discrepancy of one pixel's first N two-dimensional samples (lower is better), mean over pixels.</p>
	${table( discrepancy ).replace( '<th>Method</th>', '<th>Steps</th>' )}
	${table( stepPairs ).replace( '<th>Method</th>', '<th>Steps</th>' )}
	<p>A step shared by both dimensions stalls at about 0.075 and never converges. <code>R4_STEPS[0]</code> and <code>[2]</code> nearly satisfy α₀ + 5·α₂ = 4.000208, so that pair sits close to a small family of lines and barely improves between 256 and 1,024 samples. Each step alone as a one-dimensional sequence, and what these differences do to integrand error, are in the <a href="#X3">temporal results</a>.</p>
`;

// ---- spatial (analysis/spatial)

const SPATIAL = command( 'pnpm analysis:spatial' );
const reading = ( start ) => readings.reading.flatMap( ( g ) => g.items ).find( ( i ) => i.startsWith( `**${start}` ) );

const figures = [
	[ 'swatches', 'One frame of each noise' ], [ 'swatches-threshold', 'The same crops thresholded at 50%' ], [ 'spectra-2d', 'Power spectra' ],
	[ 'radial-power', 'Radially averaged power spectrum' ], [ 'anisotropy', 'Radial anisotropy' ], [ 'filtered-error', 'Error left after a Gaussian blur' ],
	[ 'threshold-error-by-level', 'Filtered threshold error by threshold level' ], [ 'window-stratification', 'Local stratification: error of window means' ],
	[ 'window-offsets', `${S}: what happens off the 8×8 grid` ], [ 'autocorrelation', 'Autocorrelation at small lags' ], [ 'histograms', 'Value histograms' ]
];

// which bullets of "Reading the numbers" speak to which table
const tableReadings = {
	A: [ 'Uniform histogram' ], D1: [ 'Depth of the low-frequency hole', 'No blue-noise peak or plateau' ], D2: [ 'Isotropy', 'No spectral peaks' ],
	E1: [ 'Filtered value error' ], E2: [ 'Filtered threshold error' ], E4: [ 'Wide-filter threshold error' ],
	F1: [ 'Stratification is tied to the grid' ], F2: [ 'No 8-pixel spectral lines' ], G: [ 'Nearest neighbours are anti-correlated', 'Anti-correlation exists only inside 2×2 blocks' ]
};

document.getElementById( 'spatial-body' ).innerHTML = `
	<p>${r( readings.headline )}</p>
	<p>Scope: one frame (sample index 0), one scalar per pixel. Nothing in this section says anything about temporal convergence or multi-dimensional sampling.</p>
	${SPATIAL}

	<h4>Methods as implemented</h4>
	<p>${r( readings.protocol )}</p>
	${table( { head: [ 'Definition', 'Arithmetic', 'Realizations' ], rows: readings.methods.map( ( row ) => row.map( r ) ) } )}
	${list( readings.definitions )}

	${figures.map( ( [ name, title ] ) => `<h4 id="${name}">${title}</h4>${figure( `spatial/figures/${name}.webp`, title, readings.figures[ name ].replaceAll( '{S}', S ) )}` ).join( '' )}

	${spatial.tables.map( ( t ) => `<h4 id="table-${t.id}">${t.title}</h4>${table( t )}${( tableReadings[ t.id ] || [] ).map( ( start ) => `<p>${r( reading( start ) )}</p>` ).join( '' )}` ).join( '' )}

	<h4>${S} details</h4>
	${list( spatial.details )}

	${readings.reading.slice( 2 ).map( ( g ) => `<h4>${r( g.title )}</h4>${list( g.items )}` ).join( '' )}

	<h4>Surprises</h4>
	${list( readings.surprises, 'ol' )}

	<h4>Caveats and limits</h4>
	${list( readings.caveats )}

	<h4>Gaps worth follow-on work</h4>
	${list( readings.gaps )}
`;

// ---- headline: the temporally accumulated regime, first on the page

const windowCols = ( index ) => { const head = T.raw( 'D', index ).head; return [ 16, 32 ].map( ( n ) => head.indexOf( `N=${n}, gauss1` ) ); };

document.getElementById( 'accumulated-body' ).innerHTML = `
	<p>These samplers are used under temporal accumulation: TRAA or an exponential moving average over roughly 16 to 32 frames, usually with a small spatial filter. That regime comes first. An exponential moving average with α = 0.1 has about 19 effective frames. All errors are RMSE ×1000 on a static flat field; motion and disocclusion were not measured.</p>

	<h3>Exponential accumulation (EMA α = 0.1) with a Gaussian σ = 1 blur, by values per pixel</h3>
	<p class="caption">Steady-state error. One value per pixel: threshold tests; two and four: all test integrands. The animated IGN error for two and four values is bias from its correlated values, so no blur removes it.</p>
	${dataTable( headline )}
	<p>With one value per pixel ${S} matches or beats FAST and STBN on thresholded signals (on the smooth one-value test functions FAST is about 30% better and STBN about 14%), and IGN-based samplers are better still: animated IGN by about 1.5 times, and IGN as a spatial phase with a golden-ratio Weyl step at 6.24 against 7.57. With two values it trails FAST by 25% and void-and-cluster with R2 steps by 17%, and a plain per-pixel hash with the same steps ties it once about four frames are accumulated. With four values it is 7–12% better than the stacked FAST and STBN textures, behind void-and-cluster with R4 steps (17.1 against 15.4), and keeps a small lead over the plain hash (4–14% depending on the window; see <a href="#X4">is the hierarchy needed?</a>).</p>

	<h3>The same, every spatial filter</h3>
	${T( 'D', 0 )}${T( 'D', 2 )}${T( 'D', 3 )}

	<h3>16 and 32 frames accumulated (box average), then a Gaussian σ = 1 blur</h3>
	${T( 'D', 12, { cols: windowCols( 12 ) } )}${T( 'D', 16, { cols: windowCols( 16 ) } )}${T( 'D', 18, { cols: windowCols( 18 ) } )}

	<h3>In-engine, steady state after TRAA</h3>
	<p>In SSR and VXGI under TRAA, ${S} is level with the FAST blue-noise textures on frame RMSE (VXGI 9.99 against 10.18, within run-to-run variation; SSR 2.982 against 2.981), at zero bytes against a 3.0 MB atlas. The error is distributed differently: in VXGI FAST has 19% lower bias while ${S} has 7% less temporal noise and 4% less flicker; in SSR ${S} has 15% lower bias while FAST has about 1% less noise and flicker. The plain hash with per-value steps also matches or beats FAST on RMSE. The flat-field gaps against FAST did not carry over to the engine, likely because TRAA and the denoiser are not the filter the FAST atlas is optimised for (untested). Scope: two effects, a static camera, one GPU, and FAST call sites written for this measurement.</p>
	<h3>In-engine, steady state after TRAA: VXGI</h3>
	<p class="caption">Three.js on a hardware GPU, mean ± SD over three runs of 256 frames, ×10⁻³, change against the previous sampler. Bias is measured against white noise through the same TRAA.</p>
	${realtime( 'vxgi', 2, 3 )}
	<h3>In-engine, steady state after TRAA: SSR, denoised</h3>
	${realtime( 'ssr', 3 )}
	<h3>In-engine: light map bake, 64 frames accumulated per texel, no spatial filter</h3>
	${bakeTable}
	<p>The old SSR and VXGI samplers were biased because their values per pixel were not independent; every variant that gives each value its own integer Weyl step removes that. A plain per-pixel hash with the same steps matches ${S} on SSR within 2%. On VXGI, like for like (variant C, ${S} with R2 steps, against variant A, the hash with R2 steps), the hash is about 4% lower on RMSE (8.86 against 9.26) with about 24% more flicker (5.07 against 4.09). Against the shipped configuration, which uses the first two R4 steps, the hash is 11% lower on RMSE with 22% more flicker, but there the step sets differ. Frame rate: no measurable change. Details, the simpler fixes and the limits of the method are under <a href="#engine">In-engine</a>; everything else about accumulation is under <a href="#temporal">Temporal</a>.</p>
`;

// ---- short histories: 1 to 8 frames accumulated, then a Gaussian sigma = 1 blur

const shortCols = ( index ) => { const head = T.raw( 'D', index ).head; return [ 1, 4, 8 ].map( ( n ) => head.indexOf( `N=${n}, gauss1` ) ); };

document.getElementById( 'short-body' ).innerHTML = `
	<h3>1, 4 and 8 frames accumulated, then a Gaussian σ = 1 blur</h3>
	${T( 'D', 12, { cols: shortCols( 12 ) } )}${T( 'D', 16, { cols: shortCols( 16 ) } )}${T( 'D', 18, { cols: shortCols( 18 ) } )}
	<p>On a single frame ${S}'s error is 34% (one value per pixel) and 56% (two values) higher than FAST's. Against a plain hash with the same steps it leads only on a single frame for two and four values (13–21% and 11–18%); the full comparison at 1, 4, 8 and 16 frames is under <a href="#X4">is the hierarchy needed?</a>.</p>
`;
